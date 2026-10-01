<template>
  <div class="records-view">
    <div class="rv-head">
      <h2 class="rv-title">我的考试记录</h2>
      <div class="rv-tools">
        <el-select v-if="user.isLeader" v-model="rankExam" placeholder="查看排行榜" clearable filterable style="width:220px" @change="loadRank">
          <el-option v-for="e in examOptions" :key="e.exam" :label="e.exam_title" :value="e.exam" />
        </el-select>
        <el-button :icon="Refresh" @click="load">刷新</el-button>
      </div>
    </div>

    <el-table :data="records" v-loading="loading" stripe border style="width:100%">
      <el-table-column prop="exam_title" label="考试名称" min-width="180" />
      <el-table-column label="得分" width="100" align="center"><template #default="{row}">{{ row.score }}</template></el-table-column>
      <el-table-column label="是否通过" width="100" align="center">
        <template #default="{row}"><el-tag :type="row.passed ? 'success' : 'danger'" size="small">{{ row.passed ? '通过' : '未通过' }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="attempt" label="第几次" width="80" align="center" />
      <el-table-column label="开始时间" min-width="150"><template #default="{row}">{{ fmt(row.started_at) }}</template></el-table-column>
      <el-table-column label="提交时间" min-width="150"><template #default="{row}">{{ fmt(row.submitted_at) }}</template></el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{row}"><el-button link type="primary" @click="viewDetail(row)">查看详情</el-button></template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !records.length" description="暂无考试记录" />

    <!-- 答卷详情 -->
    <el-dialog v-model="detailVis" title="答卷详情" width="720px">
      <div v-if="detail" v-loading="detailLoading">
        <el-descriptions :column="3" border size="small" class="rv-desc">
          <el-descriptions-item label="考试">{{ detail.exam_title }}</el-descriptions-item>
          <el-descriptions-item label="得分">{{ detail.score }}</el-descriptions-item>
          <el-descriptions-item label="结果">
            <el-tag :type="detail.passed ? 'success' : 'danger'" size="small">{{ detail.passed ? '通过' : '未通过' }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="detail.detail && detail.detail.length" class="rv-detail">
          <div v-for="(d, i) in detail.detail" :key="i" class="rv-q" :class="{ wrong: !d.correct }">
            <div class="rv-q-stem">{{ i + 1 }}. {{ d.stem }} <el-tag size="small" effect="plain">{{ qtypeName(d.qtype) }}</el-tag></div>
            <div class="rv-line">我的答案：<b :class="d.correct ? 'ok' : 'bad'">{{ fmtAnswer(d.my_answer) }}</b></div>
            <div class="rv-line">正确答案：<b class="ok">{{ fmtAnswer(d.correct_answer) }}</b></div>
            <div v-if="d.analysis" class="rv-line rv-ana">解析：{{ d.analysis }}</div>
          </div>
        </div>
        <el-alert v-else type="info" :closable="false" class="rv-tip"
                  title="后端正在补充逐题明细（含题干/正确答案/解析），当前展示作答记录摘要" show-icon>
          <template #default>
            <div>本次答对/答错已计入成绩；待人工阅卷题目：{{ (detail.answers && detail.answers.pending ? detail.answers.pending.length : 0) }} 道。</div>
          </template>
        </el-alert>
      </div>
    </el-dialog>

    <!-- 排行榜 -->
    <el-dialog v-model="rankVis" title="考试成绩排行榜" width="640px">
      <el-table :data="rank" v-loading="rankLoading" stripe size="small" max-height="420" empty-text="暂无排行数据">
        <el-table-column label="排名" width="70" align="center">
          <template #default="{row,$index}">
            <el-tag v-if="$index === 0" type="danger" size="small">第1名</el-tag>
            <el-tag v-else-if="$index === 1" type="warning" size="small">第2名</el-tag>
            <el-tag v-else-if="$index === 2" type="success" size="small">第3名</el-tag>
            <span v-else>{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="user_name" label="姓名" width="120" />
        <el-table-column label="得分" width="100" align="center"><template #default="{row}">{{ row.score }}</template></el-table-column>
        <el-table-column label="是否通过" width="100" align="center">
          <template #default="{row}"><el-tag :type="row.passed ? 'success' : 'danger'" size="small">{{ row.passed ? '通过' : '未通过' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="attempt" label="第几次" width="80" align="center" />
        <el-table-column label="提交时间" min-width="150"><template #default="{row}">{{ fmt(row.submitted_at) }}</template></el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { onboardingApi } from '@/api'
import { useUserStore } from '@/store/user'

const user = useUserStore()
const loading = ref(false)
const records = ref([])
const examOptions = ref([])

const qtypeName = (t) => ({ SINGLE: '单选', MULTI: '多选', JUDGE: '判断', FILL: '填空', ESSAY: '简答' }[t] || t)
const fmtAnswer = (a) => { if (a == null || a === '') return '—'; if (Array.isArray(a)) return a.join(''); return a }
const fmt = (t) => t ? String(t).replace('T', ' ').slice(0, 16) : '—'

const unwrap = (r) => { const b = r || {}; return (b && typeof b === 'object' && !Array.isArray(b) && 'code' in b && 'data' in b) ? b.data : b }
const asList = (p) => { if (!p) return []; if (Array.isArray(p)) return p; if (p.results) return p.results; return [p] }

async function load() {
  loading.value = true
  try {
    const r = unwrap(await onboardingApi.myExamRecords())
    records.value = asList(r)
    examOptions.value = records.value.map(x => ({ exam: x.exam, exam_title: x.exam_title }))
  } catch (e) { /* 拦截器已提示 */ } finally { loading.value = false }
}

// 详情
const detailVis = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
async function viewDetail(row) {
  detailVis.value = true
  detailLoading.value = true
  detail.value = null
  try { detail.value = unwrap(await onboardingApi.examRecordDetail(row.id)) } catch (e) { ElMessage.error('获取详情失败') } finally { detailLoading.value = false }
}

// 排行榜
const rankVis = ref(false)
const rankLoading = ref(false)
const rank = ref([])
const rankExam = ref('')
async function loadRank(id) {
  if (!id) { rankVis.value = false; return }
  rankVis.value = true
  rankLoading.value = true
  try { rank.value = asList(unwrap(await onboardingApi.examRank(id))) } catch (e) { ElMessage.error('获取排行榜失败') } finally { rankLoading.value = false }
}

onMounted(load)
</script>

<style scoped>
.rv-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
.rv-title { font-size: 18px; margin: 0; }
.rv-desc { margin-bottom: 14px; }
.rv-detail { margin-top: 8px; }
.rv-q { padding: 12px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px; }
.rv-q.wrong { border-color: #f0a8a8; background: var(--el-color-danger-light-9); }
.rv-q-stem { font-weight: 600; margin-bottom: 8px; line-height: 1.5; }
.rv-line { font-size: 14px; margin: 4px 0; }
.rv-ana { color: var(--text-sub); }
.rv-tip { margin-top: 8px; }
.ok { color: var(--success); }
.bad { color: #d93026; }
</style>
