<template>
  <div class="reminder-page">
    <div class="page-head">
      <h2 class="page-title">到期提醒中心</h2>
      <div class="page-actions">
        <span class="head-tip">数据日期：{{ data.today || todayStr }} · 申报/做账按 7 天临期窗口，年报/客户服务按 30 天</span>
        <el-button type="primary" plain @click="load">刷新</el-button>
      </div>
    </div>

    <!-- 四类预警数字卡片 -->
    <el-row :gutter="14" class="r-kpis">
      <el-col :span="6" v-for="k in kpiCards" :key="k.label">
        <el-card shadow="hover" @click="scrollTo(k.anchor)" class="kpi-card">
          <div class="kpi">
            <div class="num" :class="{ danger: k.overdue > 0, warn: k.overdue === 0 && k.soon > 0 }">
              {{ k.overdue }}<span class="sub"> / {{ k.soon }}</span>
            </div>
            <div class="lab">{{ k.label }}（逾期 / 临期）</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 四大板块 -->
    <el-row :gutter="14">
      <el-col :span="12" v-for="b in blocks" :key="b.title">
        <el-card shadow="never" class="r-card" :id="b.anchor">
          <template #header>
            <div class="ch-head"><span class="ch-title">{{ b.title }}</span></div>
          </template>
          <el-table :data="b.rows" size="small" max-height="300">
            <el-table-column v-for="c in b.cols" :key="c.prop" :prop="c.prop" :label="c.label" :width="c.width" />
            <template #empty><el-empty description="暂无数据" :image-size="60" /></template>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import http from '@/api'
import { ElMessage } from 'element-plus'

const data = ref({})
const todayStr = new Date().toISOString().slice(0, 10)

const c = data.value.counts || {}
const kpiCards = computed(() => {
  const cc = data.value.counts || {}
  return [
    { label: '纳税申报', overdue: cc.decl_overdue || 0, soon: cc.decl_soon || 0, anchor: 'blk-decl' },
    { label: '做账任务', overdue: cc.task_overdue || 0, soon: cc.task_soon || 0, anchor: 'blk-task' },
    { label: '工商年报', overdue: cc.report_overdue || 0, soon: cc.report_soon || 0, anchor: 'blk-report' },
    { label: '客户服务到期', overdue: cc.client_expired || 0, soon: cc.client_soon || 0, anchor: 'blk-client' },
  ]
})

const blocks = computed(() => {
  const d = data.value
  return [
    {
      title: '① 纳税申报（截止日未申报）', anchor: 'blk-decl',
      rows: [
        ...asRows(d.decl_overdue, '逾期', 'danger'),
        ...asRows(d.decl_soon, '临期', 'warning'),
      ],
      cols: [
        { prop: 'client', label: '客户', minWidth: 140 },
        { prop: 'period', label: '期间', width: 100 },
        { prop: 'deadline', label: '申报截止', width: 110 },
        { prop: 'tag', label: '预警', width: 80 },
      ],
    },
    {
      title: '② 月度做账任务（未完成）', anchor: 'blk-task',
      rows: [
        ...asRows(d.task_overdue, '逾期', 'danger'),
        ...asRows(d.task_soon, '临期', 'warning'),
      ],
      cols: [
        { prop: 'client', label: '客户', minWidth: 140 },
        { prop: 'period', label: '期间', width: 100 },
        { prop: 'status_name', label: '任务状态', width: 100 },
        { prop: 'deadline', label: '截止', width: 100 },
        { prop: 'tag', label: '预警', width: 80 },
      ],
    },
    {
      title: '③ 工商年报（未提交）', anchor: 'blk-report',
      rows: [
        ...asRows(d.report_overdue, '逾期', 'danger'),
        ...asRows(d.report_soon, '临期', 'warning'),
      ],
      cols: [
        { prop: 'client', label: '客户', minWidth: 160 },
        { prop: 'year', label: '年度', width: 90 },
        { prop: 'deadline', label: '截止', width: 110 },
        { prop: 'tag', label: '预警', width: 80 },
      ],
    },
    {
      title: '④ 客户服务到期（续费跟进）', anchor: 'blk-client',
      rows: [
        ...asRows(d.client_expired, '已到期', 'danger'),
        ...asRows(d.client_soon, '即将到期', 'warning'),
      ],
      cols: [
        { prop: 'client', label: '客户', minWidth: 140 },
        { prop: 'monthly_fee', label: '月费(元)', width: 100 },
        { prop: 'service_end', label: '到期日', width: 110 },
        { prop: 'tag', label: '预警', width: 90 },
      ],
    },
  ]
})

// 行数据带中文标签（MonthlyTask 的 status 数字码转中文在此按 dict 处理）
function asRows(list, tag, tagType) {
  return (list || []).map((r, i) => ({
    ...r,
    key: `${tag}-${i}-${r.id ?? ''}`,
    tag, tagType,
    status_name: ({ WAIT_DOC: '待收资料', DOING: '做账中', WAIT_CONFIRM: '待客户确认', DECLARED: '已申报', DELAYED: '逾期', SUSPENDED: '暂停' })[r.status] || r.status || '-',
  }))
}

async function load() {
  try {
    const r = await http.get('/accounting/reminders/')
    data.value = r?.data?.data || r?.data || {}
  } catch (e) { ElMessage.error('提醒数据加载失败，请重试') }
}
function scrollTo(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
onMounted(load)
</script>

<style scoped>
.head-tip { color: var(--text-sub); font-size: 12px; margin-right: 10px; }
.r-kpis { margin-bottom: 14px; }
.kpi-card { cursor: pointer; }
.kpi { text-align: center; padding: 4px 0; }
.kpi .num { font-size: 24px; font-weight: 700; color: var(--primary); }
.kpi .num .sub { font-size: 14px; color: var(--text-sub); font-weight: 400; }
.kpi .num.danger { color: var(--el-color-danger, #f56c6c); }
.kpi .num.warn { color: var(--el-color-warning, #e6a23c); }
.kpi .lab { color: var(--text-sub); font-size: 12px; margin-top: 4px; }
.r-card { margin-bottom: 14px; }
.ch-head { display: flex; justify-content: space-between; align-items: center; }
.ch-title { font-weight: 700; font-size: 15px; }
</style>
