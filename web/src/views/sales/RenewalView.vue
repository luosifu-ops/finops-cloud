<template>
  <div class="page" v-loading="loading" element-loading-text="续费预警加载中…" ref="reportRef">
    <div class="page-header">
      <h2 class="page-title">续费与流失预警</h2>
      <div style="display:flex;align-items:center;gap:8px">
        <el-radio-group v-model="winDays" size="small" @change="loadAll">
          <el-radio-button :value="30">30天</el-radio-button>
          <el-radio-button :value="60">60天</el-radio-button>
          <el-radio-button :value="90">90天</el-radio-button>
        </el-radio-group>
        <el-button :icon="Download" size="small" @click="exportPdf" :loading="exporting"
                   data-pdf-hide>导出 PDF</el-button>
      </div>
    </div>

    <!-- 概览 -->
    <el-row :gutter="14">
      <el-col :span="6" v-for="s in summary" :key="s.label">
        <el-card shadow="never" class="stat-card">
          <div class="label">{{ s.label }}</div>
          <div class="value" :style="{ color: s.color }">{{ s.value }}</div>
          <div class="sub">{{ s.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="14" style="margin-top: 14px">
      <!-- 到期清单 -->
      <el-col :span="15">
        <div class="card">
          <div class="card-title">到期客户清单
            <span class="card-tip">对标「客户流失 3 秒定位」· 按到期天数升序</span>
          </div>
          <div class="table-wrap">
            <el-table :data="list" size="small" stripe max-height="460" empty-text="窗口内无到期客户 🎉">
              <el-table-column label="类型" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.type==='sales'?'success':'warning'" effect="plain">
                    {{ row.type==='sales'?'合同':'代账' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="name" label="客户名称" min-width="160" show-overflow-tooltip />
              <el-table-column prop="owner" label="负责人" width="100" />
              <el-table-column label="到期日" width="120">
                <template #default="{ row }">{{ row.expire }}</template>
              </el-table-column>
              <el-table-column label="剩余" width="100" align="center">
                <template #default="{ row }">
                  <span class="days" :class="row.level">{{ row.days }} 天</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="90" align="center">
                <template #default="{ row }">
                  <el-button text type="primary" size="small" @click="go(row)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-col>

      <!-- 转化漏斗 -->
      <el-col :span="9">
        <div class="card">
          <div class="card-title">客户转化漏斗（全量线索）</div>
          <div ref="funnelRef" class="chart" style="height: 420px"></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import { salesApi, accApi } from '@/api'

const router = useRouter()
const winDays = ref(60)
const loading = ref(false)
const list = ref([])
const funnelRef = ref()
let chart = null

const asList = (r) => {
  if (!r) return []
  if (Array.isArray(r)) return r
  if (Array.isArray(r.results)) return r.results
  if (r.data) {
    if (Array.isArray(r.data)) return r.data
    if (Array.isArray(r.data.results)) return r.data.results
  }
  return []
}
const daysBetween = (d) => { const t = dayjs(d); return t.isValid() ? t.diff(dayjs().startOf('day'), 'day') : 999 }
const fmtDate = (d) => dayjs(d).format('YYYY-MM-DD')

const summary = computed(() => {
  const total = list.value.length
  const d30 = list.value.filter(x => x.days <= 30).length
  const d60 = list.value.filter(x => x.days <= 60).length
  const urgent = list.value.filter(x => x.days <= 15).length
  return [
    { label: '窗口内到期', value: total + ' 户', sub: `近 ${winDays.value} 天`, color: '#2f6fed' },
    { label: '15天内紧急', value: urgent + ' 户', sub: '需立即跟进', color: '#d93026' },
    { label: '30天内', value: d30 + ' 户', sub: '重点续费', color: '#d9822b' },
    { label: '60天内', value: d60 + ' 户', sub: '提前铺垫', color: '#0f9960' }
  ]
})

const loadAll = async () => {
  loading.value = true
  try {
    const [sc, ac, fn] = await Promise.all([
      salesApi.expiringCustomers({ days: winDays.value }),
      accApi.expiringClients({ days: winDays.value }),
      salesApi.leadFunnel()
    ])
    const sList = asList(sc).map(x => ({
      type: 'sales', name: x.name || x.customer_name || '合同客户', owner: x.owner_name || '—',
      expire: fmtDate(x.expire_at), days: daysBetween(x.expire_at)
    }))
    const aList = asList(ac).map(x => ({
      type: 'account', name: x.customer_name || x.name || '代账客户', owner: x.accountant_name || '—',
      expire: fmtDate(x.service_end), days: daysBetween(x.service_end)
    }))
    list.value = [...sList, ...aList]
      .map(x => ({ ...x, level: x.days <= 15 ? 'urgent' : x.days <= 30 ? 'warn' : 'normal' }))
      .sort((a, b) => a.days - b.days)
    renderFunnel(fn.data || fn || [])
  } finally {
    loading.value = false
  }
}

const renderFunnel = (data) => {
  if (!chart) chart = echarts.init(funnelRef.value)
  const items = (data || []).map(d => ({ name: d.name, value: d.count }))
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    color: ['#2f6fed', '#4a86ff', '#8ab4f8', '#d9822b', '#0f9960'],
    series: [{
      type: 'funnel', top: 20, bottom: 20, left: '8%', width: '84%',
      minSize: '20%', maxSize: '100%', sort: 'descending', gap: 2,
      label: { show: true, position: 'inside', formatter: '{b}\n{c}', color: '#fff', fontSize: 12 },
      data: items
    }]
  })
}

const go = (row) => router.push(row.type === 'sales' ? '/sales/customers' : '/accounting/clients')

const onResize = () => chart && chart.resize()
onMounted(async () => { await loadAll(); window.addEventListener('resize', onResize) })
onBeforeUnmount(() => { window.removeEventListener('resize', onResize); chart && chart.dispose() })
</script>

<style scoped>
.stat-card { border-radius: 10px; border: 1px solid var(--border); }
.stat-card .value { font-size: 24px; }
.card-tip { font-size: 12px; font-weight: 400; color: var(--text-sub); margin-left: 8px; }
.days { font-weight: 700; }
.days.urgent { color: #d93026; }
.days.warn { color: #d9822b; }
.days.normal { color: #0f9960; }
</style>
