<template>
  <div class="wrong-view">
    <div class="wv-head">
      <h2 class="wv-title">我的错题本</h2>
      <div class="wv-tools">
        <el-select v-model="examFilter" placeholder="按考试筛选" clearable style="width:200px" @change="load">
          <el-option v-for="e in examOptions" :key="e.id" :label="e.exam_title || e.title" :value="e.exam" />
        </el-select>
        <el-button :icon="Refresh" @click="load">刷新</el-button>
      </div>
    </div>

    <el-table :data="wrongs" v-loading="loading" stripe border style="width:100%">
      <el-table-column label="题目" min-width="260">
        <template #default="{row}">
          <div class="wv-stem">{{ row.stem }}</div>
          <el-tag size="small" effect="plain" class="wv-tag">{{ row.qtype_name || qtypeName(row.qtype) }}</el-tag>
          <span class="wv-exam">{{ row.exam_title }}</span>
        </template>
      </el-table-column>
      <el-table-column label="我的答案" min-width="140">
        <template #default="{row}"><span class="wv-mine">{{ fmtAnswer(row.my_answer) }}</span></template>
      </el-table-column>
      <el-table-column label="正确答案" min-width="140">
        <template #default="{row}"><span class="wv-right">{{ fmtAnswer(row.correct_answer) }}</span></template>
      </el-table-column>
      <el-table-column label="解析" min-width="200" show-overflow-tooltip>
        <template #default="{row}">{{ row.analysis || '—' }}</template>
      </el-table-column>
      <el-table-column label="出错次数" width="90" align="center">
        <template #default="{row}"><el-tag size="small" type="danger">{{ row.error_count || 1 }}</el-tag></template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{row}">
          <el-button link type="primary" @click="redo(row)">重做</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !wrongs.length" description="太棒了，目前没有错题" />

    <!-- 重做 -->
    <el-dialog v-model="redoVis" title="重做错题" width="520px">
      <div v-if="active" class="redo">
        <div class="redo-stem">{{ active.stem }}</div>
        <el-radio-group v-if="active.qtype === 'SINGLE' || active.qtype === 'JUDGE'" v-model="redoAns">
          <template v-if="active.qtype === 'JUDGE'">
            <el-radio value="对">正确</el-radio><el-radio value="错">错误</el-radio>
          </template>
          <template v-else>
            <el-radio v-for="o in (active.options || [])" :key="o.key" :value="o.key">{{ o.key }}. {{ o.text }}</el-radio>
          </template>
        </el-radio-group>
        <el-checkbox-group v-else-if="active.qtype === 'MULTI'" v-model="redoAns">
          <el-checkbox v-for="o in (active.options || [])" :key="o.key" :value="o.key">{{ o.key }}. {{ o.text }}</el-checkbox>
        </el-checkbox-group>
        <el-input v-else v-model="redoAns" :type="active.qtype === 'ESSAY' ? 'textarea' : 'text'" :rows="3" />
      </div>
      <div v-if="redoResult" class="redo-result" :class="redoResult.ok ? 'ok' : 'bad'">
        {{ redoResult.ok ? '回答正确 ✓' : '回答错误，正确答案：' + fmtAnswer(active && active.correct_answer) }}
        <div v-if="active && active.analysis" class="redo-analysis">解析：{{ active.analysis }}</div>
      </div>
      <template #footer>
        <el-button @click="redoVis = false">关闭</el-button>
        <el-button type="primary" :disabled="!redoAns || (Array.isArray(redoAns) && !redoAns.length)" @click="checkRedo">提交校验</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { onboardingApi } from '@/api'

const loading = ref(false)
const wrongs = ref([])
const examFilter = ref('')
const examOptions = ref([])

const qtypeName = (t) => ({ SINGLE: '单选', MULTI: '多选', JUDGE: '判断', FILL: '填空', ESSAY: '简答' }[t] || t)
const fmtAnswer = (a) => { if (a == null || a === '') return '—'; if (Array.isArray(a)) return a.join(''); return a }

const unwrap = (r) => { const b = r || {}; return (b && typeof b === 'object' && !Array.isArray(b) && 'code' in b && 'data' in b) ? b.data : b }
const asList = (p) => { if (!p) return []; if (Array.isArray(p)) return p; if (p.results) return p.results; return [p] }

async function load() {
  loading.value = true
  try {
    const [w, r] = await Promise.all([
      examFilter.value ? onboardingApi.examWrongQuestions(examFilter.value) : onboardingApi.myWrongBook(),
      onboardingApi.myExamRecords()
    ])
    wrongs.value = asList(unwrap(w))
    examOptions.value = asList(unwrap(r))
  } catch (e) { /* 拦截器已提示 */ } finally { loading.value = false }
}

// 重做
const redoVis = ref(false)
const active = ref(null)
const redoAns = ref('')
const redoResult = ref(null)
function redo(row) {
  active.value = row
  redoAns.value = row.qtype === 'MULTI' ? [] : ''
  redoResult.value = null
  redoVis.value = true
}
function checkRedo() {
  if (!active.value) return
  const correct = Array.isArray(active.value.correct_answer) ? active.value.correct_answer.join('') : String(active.value.correct_answer || '')
  const mine = Array.isArray(redoAns.value) ? redoAns.value.join('') : String(redoAns.value || '')
  const ok = mine.toUpperCase().replace(/\s/g, '') === correct.toUpperCase().replace(/\s/g, '')
  redoResult.value = { ok }
  if (ok) ElMessage.success('回答正确')
}

onMounted(load)
</script>

<style scoped>
.wv-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 8px; }
.wv-title { font-size: 18px; margin: 0; }
.wv-stem { line-height: 1.5; }
.wv-tag { margin-right: 8px; }
.wv-exam { font-size: 12px; color: var(--text-sub); }
.wv-mine { color: #d93026; font-weight: 600; }
.wv-right { color: var(--success); font-weight: 600; }
.redo-stem { font-weight: 600; margin-bottom: 14px; line-height: 1.6; }
.redo-result { margin-top: 14px; padding: 10px 12px; border-radius: 8px; }
.redo-result.ok { background: var(--el-color-success-light-9); color: var(--success); }
.redo-result.bad { background: var(--el-color-danger-light-9); color: #d93026; }
.redo-analysis { margin-top: 6px; font-size: 13px; color: var(--text-sub); }
</style>
