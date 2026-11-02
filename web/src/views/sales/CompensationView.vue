<template>
  <div class="page" v-loading="loading" element-loading-text="绩效数据加载中…" ref="reportRef">
    <div class="page-header">
      <h2 class="page-title">绩效薪酬看板</h2>
      <div style="display:flex;gap:10px;align-items:center">
        <el-date-picker v-model="month" type="month" value-format="YYYY-MM"
                        placeholder="选择月份" style="width: 150px" @change="loadAll" />
        <el-button :icon="Download" size="small" @click="exportPdf" :loading="exporting"
                   data-pdf-hide>导出 PDF</el-button>
      </div>
    </div>

    <!-- 公司目标达成 -->
    <el-row :gutter="14">
      <el-col :span="6" v-for="c in companyCards" :key="c.label">
        <el-card shadow="never" class="stat-card">
          <div class="label">{{ c.label }}</div>
          <div class="value" :style="{ color: c.color }">{{ c.value }}</div>
          <div class="sub">{{ c.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 个人业绩与预估提成 -->
    <div class="card">
      <div class="card-title">个人业绩与预估提成
        <span class="card-tip">提成按「{{ ruleName }}」规则前端测算，仅供参考</span>
      </div>
      <div class="table-wrap">
        <el-table :data="perfItems" size="small" stripe max-height="420" empty-text="本月暂无业绩数据">
          <el-table-column prop="name" label="姓名" width="110" />
          <el-table-column prop="amount" label="业绩" width="130" align="right">
            <template #default="{ row }">¥{{ fmt(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="target" label="目标" width="130" align="right">
            <template #default="{ row }">¥{{ fmt(row.target) }}</template>
          </el-table-column>
          <el-table-column label="完成率" min-width="170">
            <template #default="{ row }">
              <el-progress :percentage="Math.min(row.rate || 0, 100)"
                           :status="row.rate >= 100 ? 'success' : (row.rate >= 60 ? '' : 'exception')"
                           :text-inside="true" :stroke-width="16" />
            </template>
          </el-table-column>
          <el-table-column prop="order_count" label="订单数" width="90" align="center" />
          <el-table-column label="预估提成" width="130" align="right">
            <template #default="{ row }">
              <span class="comm">¥{{ fmt(estComm(row.amount)) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 提成规则 -->
    <div class="card">
      <div class="card-title">提成规则</div>
      <div class="table-wrap">
        <el-table :data="rules" size="small" stripe empty-text="暂无提成规则">
          <el-table-column prop="name" label="规则名称" width="160" />
          <el-table-column prop="rule_type_name" label="类型" width="110">
            <template #default="{ row }">
              <el-tag size="small" :type="row.rule_type==='LADDER'?'warning':(row.rule_type==='RATE'?'success':'info')">{{ row.rule_type_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="department_name" label="适用部门" width="110" />
          <el-table-column label="比例 / 固定" width="130">
            <template #default="{ row }">
              <span v-if="row.rule_type==='FIXED'">¥{{ fmt(row.fixed_amount) }}/单</span>
              <span v-else>{{ row.rate }}%</span>
            </template>
          </el-table-column>
          <el-table-column label="阶梯配置" min-width="280">
            <template #default="{ row }">
              <span v-if="row.rule_type==='LADDER' && row.ladder && row.ladder.length">
                <el-tag v-for="(t,i) in row.ladder" :key="i" size="small" effect="plain" class="ladder-tag">
                  {{ fmt(t.min) }}~{{ t.max>=1000000?'∞':fmt(t.max) }}：{{ t.rate }}%
                </el-tag>
              </span>
              <span v-else class="text-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="effective_month" label="生效月" width="110" />
        </el-table>
      </div>
    </div>

    <!-- 完成率排行 -->
    <div class="card">
      <div class="card-title">完成率排行</div>
      <div class="table-wrap">
        <el-table :data="rankItems" size="small" stripe max-height="420" empty-text="暂无排行数据">
          <el-table-column label="排名" width="70" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.rank === 1" type="danger" size="small">第1名</el-tag>
              <el-tag v-else-if="row.rank === 2" type="warning" size="small">第2名</el-tag>
              <el-tag v-else-if="row.rank === 3" type="success" size="small">第3名</el-tag>
              <span v-else>{{ row.rank }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="department_name" label="部门" width="100" />
          <el-table-column prop="team_name" label="小组" width="110" />
          <el-table-column prop="amount" label="业绩" width="120" align="right">
            <template #default="{ row }">¥{{ fmt(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="target" label="目标" width="120" align="right">
            <template #default="{ row }">¥{{ fmt(row.target) }}</template>
          </el-table-column>
          <el-table-column label="完成率" min-width="160">
            <template #default="{ row }">
              <el-progress :percentage="Math.min(row.rate || 0, 100)"
                           :status="row.rate >= 100 ? 'success' : (row.rate >= 60 ? '' : 'exception')"
                           :text-inside="true" :stroke-width="16" />
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { salesApi } from '@/api'
import { exportElementToPdf } from '@/utils/exportPdf'

const month = ref(dayjs().format('YYYY-MM'))
const loading = ref(false)
const reportRef = ref()
const exporting = ref(false)

const exportPdf = async () => {
  if (!reportRef.value) return
  exporting.value = true
  try {
    await exportElementToPdf(reportRef.value, `绩效薪酬报表-${month.value}.pdf`)
  } finally { exporting.value = false }
}
const perf = reactive({ total: {}, items: [] })
const rankItems = ref([])
const rules = ref([])

const fmt = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 0 }))

const ruleName = computed(() => rules.value[0]?.name || '未配置')
const perfItems = computed(() => perf.items || [])
const companyCards = computed(() => {
  const t = perf.total || {}
  return [
    { label: '本月业绩', value: '¥' + fmt(t.amount), sub: `订单 ${t.order_count || 0} 单`, color: '#c3372c' },
    { label: '业绩目标', value: '¥' + fmt(t.target), sub: '公司月度目标', color: '#1f2329' },
    { label: '目标完成率', value: (t.rate || 0) + '%', sub: t.rate >= 100 ? '已达标 🎉' : '继续努力', color: t.rate >= 100 ? '#12865a' : '#c07a12' },
    { label: '已回款', value: '¥' + fmt(t.received), sub: '实收金额', color: '#12865a' }
  ]
})

/* 预估提成测算 */
const estComm = (amount) => {
  const rule = rules.value[0]
  if (!rule) return 0
  amount = Number(amount) || 0
  if (rule.rule_type === 'RATE') return amount * (Number(rule.rate) || 0) / 100
  if (rule.rule_type === 'FIXED') return Number(rule.fixed_amount) || 0
  if (rule.rule_type === 'LADDER') {
    let comm = 0
    for (const t of (rule.ladder || [])) {
      const min = Number(t.min) || 0, max = Number(t.max) || 0, rate = Number(t.rate) || 0
      const overlap = Math.min(amount, max) - min
      if (overlap > 0) comm += overlap * rate / 100
    }
    return Math.max(Math.round(comm), 0)
  }
  return 0
}

const loadAll = async () => {
  loading.value = true
  try {
    const [p, r, c] = await Promise.all([
      salesApi.performance({ month: month.value }),
      salesApi.rank({ month: month.value }),
      salesApi.commissionRules()
    ])
    perf.total = p.total || {}
    perf.items = p.items || []
    rankItems.value = r.items || []
    rules.value = c.results || c.data || []
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.stat-card { border-radius: 10px; border: 1px solid var(--border); }
.stat-card .value { font-size: 24px; }
.card-tip { font-size: 12px; font-weight: 400; color: var(--text-sub); margin-left: 8px; }
.comm { color: var(--success); font-weight: 700; }
.ladder-tag { margin: 0 6px 4px 0; }
</style>
