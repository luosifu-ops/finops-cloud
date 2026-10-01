<template>
  <div class="growth-page">
    <!-- 日期筛选 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true">
        <el-form-item label="统计周期">
          <el-date-picker v-model="range" type="daterange" value-format="YYYY-MM-DD"
                          start-placeholder="开始日期" end-placeholder="结束日期" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadAll">查询</el-button>
          <el-button @click="quick(7)">近7天</el-button>
          <el-button @click="quick(30)">近30天</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 部门整体 -->
    <el-card shadow="never" class="block">
      <template #header><span class="block-title">部门整体数据</span></template>
      <el-row :gutter="16">
        <el-col :span="4" v-for="c in deptCards" :key="c.label">
          <div class="kpi">
            <div class="kpi-label">{{ c.label }}</div>
            <div class="kpi-value" :style="{ color: c.color }">{{ c.value }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 个人数据 -->
    <el-card shadow="never" class="block">
      <template #header><span class="block-title">我的个人数据</span></template>
      <el-row :gutter="16">
        <el-col :span="4" v-for="c in myCards" :key="c.label">
          <div class="kpi">
            <div class="kpi-label">{{ c.label }}</div>
            <div class="kpi-value" :style="{ color: c.color }">{{ c.value }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 平台产出对比 -->
    <el-card shadow="never" class="block">
      <template #header>
        <div class="card-header">
          <span class="block-title">平台产出对比</span>
          <div>
            <el-tag type="success" size="small">高产出 {{ summary.high }}</el-tag>
            <el-tag type="warning" size="small" style="margin-left:6px">低产出 {{ summary.low }}</el-tag>
            <el-tag type="info" size="small" style="margin-left:6px">零产出 {{ summary.zero }}</el-tag>
          </div>
        </div>
      </template>
      <div ref="chartRef" class="chart"></div>
    </el-card>

    <!-- 明细表 -->
    <el-card shadow="never" class="block">
      <template #header><span class="block-title">各平台明细</span></template>
      <el-table :data="rows" border stripe size="default">
        <el-table-column prop="name" label="平台" width="100" />
        <el-table-column prop="lead_count" label="线索数" width="90" />
        <el-table-column prop="deal_count" label="成交数" width="90" />
        <el-table-column label="转化率" width="100">
          <template #default="{ row }">{{ row.convert_rate }}%</template>
        </el-table-column>
        <el-table-column label="消耗" width="110">
          <template #default="{ row }">¥{{ row.cost }}</template>
        </el-table-column>
        <el-table-column label="单线索成本" width="110">
          <template #default="{ row }">¥{{ row.cost_per_lead }}</template>
        </el-table-column>
        <el-table-column label="产出分层" width="110">
          <template #default="{ row }">
            <el-tag :type="levelType(row.level)" size="small">{{ row.level_label }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { growthApi } from '@/api/growth'

const range = ref([])
const overview = ref({ dept: {}, my: {} })
const rows = ref([])
const summary = ref({ high: 0, low: 0, zero: 0 })
const chartRef = ref(null)
let chart = null

function money(v) { return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }

const deptCards = computed(() => {
  const d = overview.value.dept || {}
  return [
    { label: '线索总数', value: d.lead_count ?? '-', color: '#303133' },
    { label: '成交数', value: d.deal_count ?? '-', color: '#67c23a' },
    { label: '转化率', value: (d.convert_rate ?? 0) + '%', color: '#409eff' },
    { label: '投放消耗', value: '¥' + money(d.cost), color: '#e6a23c' },
    { label: '单线索成本', value: '¥' + money(d.cost_per_lead), color: '#f56c6c' },
    { label: '投产比', value: d.roi ?? '-', color: '#909399' }
  ]
})

const myCards = computed(() => {
  const m = overview.value.my || {}
  return [
    { label: '我的线索', value: m.lead_count ?? '-', color: '#303133' },
    { label: '我的成交', value: m.deal_count ?? '-', color: '#67c23a' },
    { label: '我的转化率', value: (m.convert_rate ?? 0) + '%', color: '#409eff' },
    { label: '我的消耗', value: '¥' + money(m.cost), color: '#e6a23c' },
    { label: '单线索成本', value: '¥' + money(m.cost_per_lead), color: '#f56c6c' },
    { label: '投产比', value: m.roi ?? '-', color: '#909399' }
  ]
})

function levelType(l) { return { HIGH: 'success', LOW: 'warning', ZERO: 'info' }[l] || 'info' }

function quick(days) {
  const end = new Date()
  const start = new Date(Date.now() - days * 86400000)
  const f = d => d.toISOString().slice(0, 10)
  range.value = [f(start), f(end)]
  loadAll()
}

function params() {
  const p = {}
  if (range.value && range.value.length === 2) {
    p.start = range.value[0]
    p.end = range.value[1]
  }
  return p
}

async function loadAll() {
  try {
    const p = params()
    const [ov, bp] = await Promise.all([
      growthApi.statsOverview(p),
      growthApi.statsByPlatform(p)
    ])
    overview.value = ov || { dept: {}, my: {} }
    rows.value = (bp && bp.rows) || []
    summary.value = (bp && bp.summary) || { high: 0, low: 0, zero: 0 }
    renderChart()
  } catch (e) {
    overview.value = { dept: {}, my: {} }
    rows.value = []
    summary.value = { high: 0, low: 0, zero: 0 }
  }
}

function renderChart() {
  nextTick(() => {
    if (!chartRef.value) return
    if (!chart) chart = echarts.init(chartRef.value)
    const data = rows.value
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['线索数', '成交数'], top: 0 },
      grid: { left: 40, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: data.map(r => r.name) },
      yAxis: { type: 'value' },
      series: [
        { name: '线索数', type: 'bar', data: data.map(r => r.lead_count), itemStyle: { color: '#409eff' } },
        { name: '成交数', type: 'bar', data: data.map(r => r.deal_count), itemStyle: { color: '#67c23a' } }
      ]
    }, true)
  })
}

function onResize() { chart && chart.resize() }

onMounted(() => {
  loadAll()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart && chart.dispose()
})
</script>

<style scoped>
.growth-page { padding: 4px; }
.filter-card { margin-bottom: 14px; }
.block { margin-bottom: 14px; }
.block-title { font-weight: 600; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.kpi { text-align: center; padding: 10px 0; }
.kpi-label { font-size: 13px; color: #909399; }
.kpi-value { font-size: 22px; font-weight: 600; margin-top: 6px; }
.chart { width: 100%; height: 320px; }
</style>
