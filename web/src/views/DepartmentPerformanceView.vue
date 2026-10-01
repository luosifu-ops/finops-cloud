<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">{{ title }}</h2>
      <el-date-picker v-model="month" type="month" value-format="YYYY-MM"
                      placeholder="选择月份" style="width: 150px" @change="load" />
    </div>

    <el-alert v-if="data.code === 'OPS'" type="info" :closable="false" show-icon
              title="运营部业绩以「投放产出」衡量" style="margin-bottom:14px" />

    <!-- 指标卡 -->
    <el-row :gutter="14">
      <el-col :span="8" v-for="c in statCards" :key="c.label">
        <el-card shadow="never" class="stat-card">
          <div class="label">{{ c.label }}</div>
          <div class="value" :style="{ color: c.color || '#1f2329' }">{{ c.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 运营部：各平台明细 -->
    <el-card shadow="never" class="plat-card" v-if="data.code === 'OPS' && platforms.length">
      <div class="card-title">各投放平台明细（本月）</div>
      <el-table :data="platforms" size="small" stripe max-height="360">
        <el-table-column prop="platform" label="平台" />
        <el-table-column prop="cost" label="消耗(元)" align="right"><template #default="{row}">¥{{ fmt(row.cost) }}</template></el-table-column>
        <el-table-column prop="leads" label="线索数" align="center" />
        <el-table-column prop="deals" label="成交数" align="center" />
        <el-table-column prop="amount" label="成交额(元)" align="right"><template #default="{row}">¥{{ fmt(row.amount) }}</template></el-table-column>
        <el-table-column prop="cpl" label="线索成本" align="right"><template #default="{row}">¥{{ fmt(row.cpl) }}</template></el-table-column>
        <el-table-column label="投资回报率" align="center">
          <template #default="{row}"><el-tag size="small" :type="row.roi >= 3 ? 'success' : 'warning'">{{ row.roi }}</el-tag></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-empty v-if="!loading && !hasData" description="本月暂无该部门数据" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { dashApi } from '@/api'
import dayjs from 'dayjs'

const props = defineProps({
  code: { type: String, required: true },
  title: { type: String, default: '部门业绩总览' }
})

const month = ref(dayjs().format('YYYY-MM'))
const loading = ref(false)
const data = ref({})
const platforms = computed(() => data.value.by_platform || [])

const fmt = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))
const wan = (n) => (n >= 10000 ? (n / 10000).toFixed(1) + '万' : fmt(n))

const statCards = computed(() => {
  const d = data.value || {}
  const code = d.code
  if (code === 'SALES') {
    return [
      { label: '业绩金额', value: '¥' + wan(d.amount || 0), color: '#d93026' },
      { label: '订单数', value: fmt(d.orders || 0) + ' 单' },
      { label: '线索总数', value: fmt(d.lead_total || 0) },
      { label: '成交线索', value: fmt(d.lead_dealt || 0) },
      { label: '通话数', value: fmt(d.calls || 0) },
      { label: '接通数', value: fmt(d.connected || 0) },
    ]
  }
  if (code === 'ACCOUNT') {
    return [
      { label: '做账任务总数', value: fmt(d.task_total || 0), color: '#2f6fed' },
      { label: '已完成', value: fmt(d.task_done || 0), color: '#0f9960' },
      { label: '逾期', value: fmt(d.overdue || 0), color: (d.overdue || 0) > 0 ? '#d93026' : '#1f2329' },
      { label: '代账客户数', value: fmt(d.client_total || 0) },
      { label: '活跃客户', value: fmt(d.client_active || 0), color: '#0f9960' },
    ]
  }
  if (code === 'OPS') {
    return [
      { label: '投放总消耗', value: '¥' + wan(d.cost || 0), color: '#d9822b' },
      { label: '线索数', value: fmt(d.leads || 0) },
      { label: '加微数', value: fmt(d.wechat || 0) },
      { label: '成交数', value: fmt(d.deals || 0) },
      { label: '成交额', value: '¥' + wan(d.amount || 0), color: '#d93026' },
      { label: '投资回报率', value: fmt(d.roi || 0), color: (d.roi || 0) >= 3 ? '#0f9960' : '#d9822b' },
      { label: '线索成本 CPL', value: '¥' + fmt(d.cpl || 0) },
      { label: '获客成本 CAC', value: '¥' + fmt(d.cac || 0) },
    ]
  }
  return []
})

const hasData = computed(() => Object.keys(data.value || {}).length > 1)

const load = async () => {
  loading.value = true
  try {
    const r = await dashApi.department(props.code, { month: month.value })
    data.value = { code: props.code, ...(r.data || {}) }
  } catch (e) {} finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.stat-card { border-radius: 10px; border: 1px solid var(--border); margin-bottom: 14px; }
.stat-card .label { font-size: 13px; color: var(--text-sub); }
.stat-card .value { font-size: 22px; font-weight: 700; margin-top: 6px; }
.plat-card { border-radius: 10px; border: 1px solid var(--border); margin-top: 4px; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
</style>
