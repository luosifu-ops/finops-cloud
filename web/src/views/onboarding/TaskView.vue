<template>
  <div class="task-view">
    <el-tabs v-model="tab">
      <el-tab-pane label="我的入职任务" name="mine" />
      <el-tab-pane v-if="user.isHR || user.isBoss" label="全员完成统计" name="stat" />
    </el-tabs>

    <template v-if="tab === 'mine'">
      <!-- 进度统计 -->
      <el-row :gutter="16" v-loading="loading">
        <el-col :span="6"><el-card shadow="never" class="stat-card"><div class="stat-num">{{ stat.total }}</div><div class="stat-label">任务总数</div></el-card></el-col>
        <el-col :span="6"><el-card shadow="never" class="stat-card"><div class="stat-num done">{{ stat.finished_count }}</div><div class="stat-label">已完成</div></el-card></el-col>
        <el-col :span="6"><el-card shadow="never" class="stat-card">
          <el-progress type="dashboard" :percentage="stat.completion_rate" :width="90" :status="stat.completion_rate >= 100 ? 'success' : ''" />
          <div class="stat-label">完成率</div>
        </el-card></el-col>
        <el-col :span="6"><el-card shadow="never" class="stat-card"><div class="stat-num warn">{{ minDue }}</div><div class="stat-label">最近截止(天)</div></el-card></el-col>
      </el-row>

      <!-- 按类型分组 -->
      <div v-for="g in groups" :key="g.type" class="task-group">
        <div class="tg-head"><span class="tg-dot" :style="{background: g.color}" />{{ g.label }}
          <span class="tg-count">{{ g.list.filter(t => t.finished).length }}/{{ g.list.length }}</span>
        </div>
        <el-card v-for="t in g.list" :key="t.id" shadow="hover" class="task-item" :class="{ finished: t.finished }">
          <div class="ti-main">
            <div class="ti-title">{{ t.title }} <el-tag v-if="t.required" size="small" type="danger" effect="plain">必修</el-tag></div>
            <div class="ti-desc">{{ t.description || '—' }}</div>
            <div class="ti-meta">需 {{ t.due_days }} 天内完成<template v-if="t.finished_at"> · 完成于 {{ fmt(t.finished_at) }}</template></div>
          </div>
          <div class="ti-action">
            <el-tag v-if="t.finished" type="success" effect="dark">已完成</el-tag>
            <template v-else>
              <el-button v-if="g.type === 'REGULATION'" type="primary" size="small" @click="go(regulationPath(t))">去学习</el-button>
              <el-button v-else-if="g.type === 'COURSE'" type="primary" size="small" @click="go(coursePath(t))">去学习</el-button>
              <el-button v-else-if="g.type === 'EXAM'" type="primary" size="small" @click="go('/onboarding/exam')">去考试</el-button>
              <el-button v-else-if="g.type === 'MATERIAL'" type="primary" size="small" @click="go('/onboarding/profile')">去填写</el-button>
              <el-button v-else type="success" size="small" @click="complete(t)">标记完成</el-button>
            </template>
          </div>
        </el-card>
        <el-empty v-if="!g.list.length" :description="`暂无${g.label}任务`" :image-size="50" />
      </div>
      <el-empty v-if="!loading && !allTasks.length" description="暂未分配入职任务" />
    </template>

    <!-- 全员统计 -->
    <template v-else>
      <el-table :data="stats" v-loading="statLoading" stripe border style="width:100%">
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="department_name" label="部门" width="140" />
        <el-table-column prop="total" label="总任务" width="90" align="center" />
        <el-table-column prop="finished_count" label="已完成" width="90" align="center" />
        <el-table-column label="完成率" min-width="220">
          <template #default="{row}">
            <el-progress :percentage="Math.min(row.completion_rate || 0, 100)" :status="row.completion_rate >= 100 ? 'success' : ''" :text-inside="true" :stroke-width="16" />
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!statLoading && !stats.length" description="暂无统计数据" />
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { onboardingApi } from '@/api'
import { useUserStore } from '@/store/user'

const user = useUserStore()
const router = useRouter()
const tab = ref('mine')
const loading = ref(false)
const statLoading = ref(false)
const allTasks = ref([])
const stat = reactive({ total: 0, finished_count: 0, completion_rate: 0 })
const stats = ref([])

const groupDefs = [
  { type: 'REGULATION', label: '学习阅读 · 制度', color: '#409eff' },
  { type: 'COURSE', label: '学习阅读 · 课程', color: '#67c23a' },
  { type: 'EXAM', label: '考试任务', color: '#e6a23c' },
  { type: 'MATERIAL', label: '资料提交', color: '#9254de' },
  { type: 'OTHER', label: '其他事项', color: '#909399' }
]
const groups = computed(() => groupDefs.map(g => ({ ...g, list: allTasks.value.filter(t => t.task_type === g.type) })))
const minDue = computed(() => {
  const un = allTasks.value.filter(t => !t.finished && t.due_days)
  return un.length ? Math.min(...un.map(t => t.due_days)) : '—'
})
const fmt = (t) => t ? String(t).replace('T', ' ').slice(0, 16) : ''

const unwrap = (r) => { const b = r || {}; return (b && typeof b === 'object' && !Array.isArray(b) && 'code' in b && 'data' in b) ? b.data : b }

async function load() {
  loading.value = true
  try {
    const r = unwrap(await onboardingApi.myTasks())
    allTasks.value = r.tasks || []
    stat.total = r.total || 0; stat.finished_count = r.finished_count || 0; stat.completion_rate = r.completion_rate || 0
  } catch (e) {} finally { loading.value = false }
}
const go = (path) => router.push(path)
// 按任务标题关键词解析对应制度/课程分类（纯前端映射，跳转到真实存在的阅读页，避免跳经营总览）
function regSlug(title) {
  if (/薪酬|绩效/.test(title)) return 'salary'
  if (/保密|合规/.test(title)) return 'secret'
  if (/考勤/.test(title)) return 'attendance'
  if (/奖惩/.test(title)) return 'reward'
  if (/报销/.test(title)) return 'expense'
  if (/行为|规范/.test(title)) return 'behavior'
  return 'attendance'
}
function courseSlug(title) {
  if (/代理记账/.test(title)) return 'agency'
  if (/税务/.test(title)) return 'tax'
  if (/发票/.test(title)) return 'invoice'
  if (/工商/.test(title)) return 'business'
  if (/社保/.test(title)) return 'social'
  if (/法规/.test(title)) return 'law'
  if (/软件|做账/.test(title)) return 'software'
  if (/销售|话术/.test(title)) return 'sale'
  if (/投放|运营/.test(title)) return 'ops'
  return 'agency'
}
const regulationPath = (t) => `/onboarding/regulation/${regSlug(t.title || '')}`
const coursePath = (t) => `/onboarding/knowledge/${courseSlug(t.title || '')}`
async function complete(t) {
  try { await onboardingApi.completeTask(t.id); ElMessage.success('已标记完成'); load() } catch (e) { ElMessage.error('操作失败') }
}
async function loadStat() {
  if (!(user.isHR || user.isBoss)) return
  statLoading.value = true
  try { stats.value = unwrap(await onboardingApi.taskStat()) || [] } catch (e) {} finally { statLoading.value = false }
}

onMounted(() => { load(); loadStat() })
</script>

<style scoped>
.stat-card { text-align: center; border-radius: 10px; }
.stat-num { font-size: 30px; font-weight: 800; color: var(--el-color-primary); }
.stat-num.done { color: var(--success); }
.stat-num.warn { color: #e6a23c; }
.stat-label { font-size: 12px; color: var(--text-sub); margin-top: 4px; }
.task-group { margin-top: 18px; }
.tg-head { font-weight: 700; margin-bottom: 10px; display: flex; align-items: center; }
.tg-dot { width: 10px; height: 10px; border-radius: 3px; margin-right: 8px; }
.tg-count { font-size: 12px; color: var(--text-sub); font-weight: 400; margin-left: 8px; }
.task-item { margin-bottom: 10px; border-radius: 10px; display: flex; align-items: center; justify-content: space-between; }
.task-item.finished { opacity: 0.75; }
.ti-title { font-weight: 600; margin-bottom: 4px; }
.ti-desc { font-size: 13px; color: var(--text-sub); margin-bottom: 4px; }
.ti-meta { font-size: 12px; color: var(--text-sub); }
.ti-action { flex-shrink: 0; margin-left: 16px; }
</style>
