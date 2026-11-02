<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">业绩统计</h2>
      <div class="header-tools">
        <el-radio-group v-model="period" @change="onPeriodChange">
          <el-radio-button value="month">本月</el-radio-button>
          <el-radio-button value="quarter">本季度</el-radio-button>
          <el-radio-button value="year">本年</el-radio-button>
          <el-radio-button value="custom">自定义</el-radio-button>
        </el-radio-group>
        <el-date-picker v-if="period==='custom'" v-model="customMonth" type="month" value-format="YYYY-MM" style="width:150px" @change="reload" />
      </div>
    </div>

    <!-- 筛选 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="统计维度">
          <el-radio-group v-model="scope" @change="reload">
            <el-radio value="PERSON">个人</el-radio>
            <el-radio value="DEPT">部门</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="department" placeholder="全部部门" clearable style="width:160px" @change="reload">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="员工" v-if="scope==='PERSON'">
          <el-input v-model="keyword" placeholder="姓名/工号" clearable style="width:150px" @keyup.enter="reload" @clear="reload" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="reload">查询</el-button>
          <el-button :icon="Download" @click="exportCsv">导出 CSV</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-alert v-if="error" type="error" :closable="false" show-icon :title="error" class="err-alert" />

    <!-- 汇总卡片 -->
    <div class="stat-grid" v-if="summary">
      <el-card shadow="never" class="stat-card" v-for="c in summaryCards" :key="c.label">
        <div class="label">{{ c.label }}</div>
        <div class="value" :style="{ color: c.color }">{{ c.value }}</div>
        <div class="sub">{{ c.sub }}</div>
      </el-card>
    </div>

    <!-- 目标对比 -->
    <el-card shadow="never" class="block-card" v-if="summary && summary.total_target">
      <div class="card-title">目标对比（{{ statMonth }}）</div>
      <el-progress :percentage="Math.min(Number(summary.achieve_rate) || 0, 100)"
                   :status="(Number(summary.achieve_rate) || 0) >= 100 ? 'success' : ''"
                   :stroke-width="18" :text-inside="true" />
      <div class="target-line">
        <span>实际业绩：<b>{{ fmtMoney(summary.total_amount) }}</b></span>
        <span>目标业绩：<b>{{ fmtMoney(summary.total_target) }}</b></span>
        <span>完成率：<b :class="rateClass(summary.achieve_rate)">{{ summary.achieve_rate }}%</b></span>
      </div>
    </el-card>

    <!-- 明细表 -->
    <el-card shadow="never" class="block-card">
      <div class="card-title">{{ scope==='PERSON' ? '个人业绩明细' : '部门业绩明细' }}</div>
      <el-table :data="rows" size="small" stripe max-height="420" empty-text="暂无业绩数据">
        <el-table-column v-if="scope==='PERSON'" prop="user_name" label="姓名" width="120" />
        <el-table-column :prop="scope==='PERSON' ? 'department_name' : 'department_name'" label="部门" width="140" />
        <el-table-column label="合同金额" align="right" min-width="130"><template #default="{row}">{{ fmtMoney(row.contract_amount) }}</template></el-table-column>
        <el-table-column prop="deal_count" label="成交数" width="90" align="center" />
        <el-table-column prop="new_customer_count" label="新增客户" width="100" align="center" />
        <el-table-column prop="call_count" label="通话量" width="90" align="center" />
        <el-table-column label="目标" align="right" min-width="120"><template #default="{row}">{{ fmtMoney(row.target) }}</template></el-table-column>
        <el-table-column label="完成率" width="120" align="center">
          <template #default="{row}"><span :class="rateClass(row.achieve_rate)">{{ row.achieve_rate }}%</span></template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 排行 -->
    <el-card shadow="never" class="block-card">
      <div class="card-title">合同金额 Top10</div>
      <div v-if="top10.length" class="rank">
        <div class="rank-item" v-for="(r,i) in top10" :key="i">
          <span class="rank-no" :class="'no'+(i+1)">{{ i+1 }}</span>
          <span class="rank-name">{{ scope==='PERSON' ? (r.user_name||'—') : (r.department_name||'—') }}</span>
          <div class="rank-bar"><div class="rank-fill" :style="{ width: barWidth(r.contract_amount) }"></div></div>
          <span class="rank-val">{{ fmtMoney(r.contract_amount) }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无排行数据" :image-size="80" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { hrApi, orgApi } from '@/api'

const loading = ref(false)
const error = ref('')
const period = ref('month')
const customMonth = ref(dayjs().format('YYYY-MM'))
const scope = ref('PERSON')
const department = ref('')
const keyword = ref('')
const departments = ref([])
const rows = ref([])
const summary = ref(null)

const statMonth = computed(() => {
  if (period.value === 'custom') return customMonth.value
  if (period.value === 'quarter') return quarterStart().format('YYYY-MM')
  if (period.value === 'year') return dayjs().format('YYYY') + '-01'
  return dayjs().format('YYYY-MM')
})
const quarterStart = () => {
  const m = dayjs()
  const q = Math.floor(m.month() / 3) * 3
  return m.month(q).date(1)
}
const onPeriodChange = () => { if (period.value !== 'custom') reload() }

const sumField = (f) => rows.value.reduce((a, r) => a + (Number(r[f]) || 0), 0)
const summaryCards = computed(() => {
  const s = summary.value || {}
  return [
    { label: '总业绩', value: fmtMoney(s.total_amount != null ? s.total_amount : sumField('contract_amount')), sub: statMonth.value, color: '#c3372c' },
    { label: '成交单数', value: s.total_deal != null ? s.total_deal : sumField('deal_count'), sub: '合同成交总数', color: '#1f2329' },
    { label: '新增客户', value: s.total_new_customer != null ? s.total_new_customer : sumField('new_customer_count'), sub: '本期新增', color: '#2a4fd4' },
    { label: '通话量', value: s.total_call != null ? s.total_call : sumField('call_count'), sub: '电话外呼量', color: '#12865a' },
    { label: '目标完成率', value: (s.achieve_rate != null ? s.achieve_rate : '—') + (s.achieve_rate != null ? '%' : ''), sub: Number(s.achieve_rate) >= 100 ? '已达标' : '未达标', color: Number(s.achieve_rate) >= 100 ? '#c3372c' : '#909399' }
  ]
})
const top10 = computed(() => [...rows.value].sort((a, b) => (b.contract_amount || 0) - (a.contract_amount || 0)).slice(0, 10))
const maxAmount = computed(() => Math.max(1, ...top10.value.map(r => Number(r.contract_amount) || 0)))
const barWidth = (v) => Math.round((Number(v) || 0) / maxAmount.value * 100) + '%'
const rateClass = (r) => (Number(r) || 0) >= 100 ? 'rate-ok' : 'rate-no'

const fmtMoney = (n) => (n === undefined || n === null ? '¥0.00' : '¥' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))

function parseObj(resp) {
  if (!resp) return null
  if (resp && typeof resp === 'object' && 'code' in resp && 'data' in resp) return resp.data
  return resp
}
function parseList(resp) {
  if (!resp) return []
  let b = resp
  if (b && typeof b === 'object' && 'code' in b && 'data' in b) b = b.data
  if (b && b.results) return b.results
  if (Array.isArray(b)) return b
  if (b && typeof b === 'object') return [b]
  return []
}

const reload = async () => {
  loading.value = true
  error.value = ''
  try {
    const p = { month: statMonth.value, scope: scope.value }
    if (department.value) p.department = department.value
    if (scope.value === 'PERSON' && keyword.value) p.user = keyword.value
    const r = await hrApi.performanceStat(p)
    const d = parseObj(r) || {}
    summary.value = d.summary || null
    rows.value = d.list || []
  } catch (e) {
    error.value = '业绩统计数据加载失败，请稍后重试'
    summary.value = null; rows.value = []
  } finally { loading.value = false }
}

const exportCsv = () => {
  const headers = scope.value === 'PERSON' ? ['姓名', '部门', '合同金额', '成交数', '新增客户', '通话量', '目标', '完成率'] : ['部门', '合同金额', '成交数', '新增客户', '通话量', '目标', '完成率']
  const rowsData = rows.value.map(r => scope.value === 'PERSON'
    ? [r.user_name, r.department_name, r.contract_amount, r.deal_count, r.new_customer_count, r.call_count, r.target, r.achieve_rate + '%']
    : [r.department_name, r.contract_amount, r.deal_count, r.new_customer_count, r.call_count, r.target, r.achieve_rate + '%'])
  const csv = [headers, ...rowsData].map(row => row.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `业绩统计-${statMonth.value}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

const loadDepartments = async () => {
  try { const r = await orgApi.departments({ page_size: 200 }); departments.value = parseList(r) } catch (e) {}
}

onMounted(async () => { await loadDepartments(); await reload() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 10px; }
.header-tools { display: flex; gap: 8px; align-items: center; }
.filter-card, .block-card, .stat-card { border-radius: 10px; border: 1px solid var(--border); margin-bottom: 14px; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
.err-alert { margin-bottom: 14px; }
.stat-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 14px; }
@media (max-width: 1100px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }
.stat-card .label { font-size: 13px; color: var(--text-sub); }
.stat-card .value { font-size: 22px; font-weight: 800; margin: 6px 0; }
.stat-card .sub { font-size: 12px; color: #909399; }
.target-line { display: flex; gap: 24px; margin-top: 12px; flex-wrap: wrap; font-size: 14px; color: var(--text-sub); }
.rate-ok { color: #c3372c; font-weight: 800; }
.rate-no { color: #909399; }
.rank { display: flex; flex-direction: column; gap: 10px; }
.rank-item { display: flex; align-items: center; gap: 10px; }
.rank-no { width: 24px; height: 24px; line-height: 24px; text-align: center; border-radius: 6px; background: #f0f2f5; font-size: 12px; font-weight: 700; color: #606266; }
.rank-no.no1 { background: #fde2e2; color: #c3372c; }
.rank-no.no2 { background: #fdf0e0; color: #c07a12; }
.rank-no.no3 { background: #e6f4ea; color: #12865a; }
.rank-name { width: 120px; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-bar { flex: 1; background: #f0f2f5; border-radius: 6px; height: 18px; overflow: hidden; }
.rank-fill { height: 100%; background: linear-gradient(90deg, #2a4fd4, #5b8def); border-radius: 6px; transition: width .4s; }
.rank-val { width: 120px; text-align: right; font-size: 13px; font-weight: 600; }
</style>
