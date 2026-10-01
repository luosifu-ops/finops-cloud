<template>
  <div class="page" v-loading="loading" element-loading-text="经营数据加载中…">
    <!-- 新手引导条 -->
    <div class="guide" v-if="showGuide">
      <div class="guide-icon">🧭</div>
      <div class="guide-body">
        <div class="guide-title">经营总览 · 使用引导</div>
        <div class="guide-text">① 顶部 6 张指标卡看全局；② <b>目标达成仪表盘</b>看月度进度；③ <b>智能预警中心</b>聚合待审批/逾期/到期，点击可跳转处理；④ 顶栏「消息」随时查看待办。</div>
      </div>
      <el-button text size="small" :icon="Close" @click="dismissGuide">不再提示</el-button>
    </div>

    <!-- 欢迎条 -->
    <div class="welcome">
      <div class="welcome-left">
        <div class="hi">{{ greet }}，{{ store.name || '老板' }} <span class="wave">👋</span></div>
        <div class="date">{{ todayText }}</div>
      </div>
      <div class="welcome-right">
        <el-tag type="primary" effect="dark" round>角色：{{ roleName }}</el-tag>
        <el-tag v-if="data.performance" effect="plain" round>
          本月完成率 {{ data.performance.completion || 0 }}%
        </el-tag>
        <el-tag v-if="expiringTotal" type="warning" effect="plain" round>
          {{ expiringTotal }} 个客户即将到期
        </el-tag>
      </div>
    </div>

    <div class="page-header">
      <h2 class="page-title">经营总览</h2>
      <div style="display:flex;align-items:center;gap:8px">
        <el-date-picker v-model="month" type="month" value-format="YYYY-MM"
                        placeholder="选择月份" style="width: 150px" @change="loadAll" />
        <el-button :icon="Edit" size="small" @click="openTarget" data-pdf-hide>设置目标</el-button>
        <el-button :icon="Download" size="small" @click="exportPdf" :loading="exporting"
                   data-pdf-hide>导出 PDF</el-button>
      </div>
    </div>

    <!-- 核心指标 -->
    <el-row :gutter="14">
      <el-col :span="4" v-for="c in cards" :key="c.label">
        <el-card shadow="never" class="stat-card">
          <div class="label">{{ c.label }}</div>
          <div class="value" :style="{ color: c.color }">{{ c.value }}</div>
          <div class="sub">{{ c.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="14" style="margin-top: 14px">
      <!-- 目标达成仪表盘 -->
      <el-col :span="6">
        <div class="card">
          <div class="card-title">目标达成率</div>
          <div ref="gaugeRef" class="chart" style="height: 230px"></div>
          <div class="gauge-foot">
            <span>目标 ¥{{ wan((data.performance||{}).target || 0) }}</span>
            <span>已签 ¥{{ wan((data.performance||{}).amount || 0) }}</span>
          </div>
        </div>
      </el-col>
      <!-- 智能预警中心 -->
      <el-col :span="18">
        <div class="card">
          <div class="card-title">智能预警中心
            <span class="card-tip">对标「客户流失 3 秒定位 · 财税风险预警」</span>
          </div>
          <el-row :gutter="12">
            <el-col :span="6" v-for="w in warnings" :key="w.key">
              <div class="warn-tile" :class="'warn-'+w.level" @click="go(w.path)">
                <div class="warn-icon">{{ w.icon }}</div>
                <div class="warn-num">{{ w.count }}</div>
                <div class="warn-label">{{ w.label }}</div>
              </div>
            </el-col>
          </el-row>
          <!-- 到期明细 -->
          <div class="exp-list" v-if="expiringList.length">
            <div class="exp-title">近期到期提醒（Top {{ expiringList.length }}）</div>
            <div class="exp-row" v-for="(e, i) in expiringList" :key="i">
              <el-tag size="small" :type="e.type==='sales' ? 'success' : 'warning'" effect="plain">
                {{ e.type==='sales' ? '合同' : '代账' }}
              </el-tag>
              <span class="exp-name">{{ e.name }}</span>
              <span class="exp-days" :class="{ urgent: e.days <= 15 }">{{ e.days }} 天后到期</span>
            </div>
          </div>
          <el-empty v-else description="暂无到期预警 🎉" :image-size="50" style="padding: 10px 0" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="14" style="margin-top: 0">
      <!-- 业绩趋势 -->
      <el-col :span="16">
        <div class="card">
          <div class="card-title">业绩趋势（近 6 个月）</div>
          <div ref="trendRef" class="chart"></div>
        </div>
      </el-col>
      <!-- 今日考勤 -->
      <el-col :span="8">
        <div class="card">
          <div class="card-title">今日考勤</div>
          <div ref="attRef" class="chart" style="height: 200px"></div>
          <el-descriptions :column="2" border size="small" style="margin-top: 12px">
            <el-descriptions-item label="应出勤">{{ data.attendance?.total_staff || 0 }} 人</el-descriptions-item>
            <el-descriptions-item label="已打卡">{{ data.attendance?.checked || 0 }} 人</el-descriptions-item>
            <el-descriptions-item label="迟到">{{ data.attendance?.late || 0 }} 人</el-descriptions-item>
            <el-descriptions-item label="请假">{{ data.attendance?.leave || 0 }} 人</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="14" style="margin-top: 0">
      <!-- 部门业绩 -->
      <el-col :span="12">
        <div class="card">
          <div class="card-title">部门业绩对比</div>
          <div ref="deptRef" class="chart" style="height: 300px"></div>
        </div>
      </el-col>
      <!-- 运营投放 -->
      <el-col :span="12">
        <div class="card">
          <div class="card-title">运营投放（本月）</div>
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="总消耗">¥{{ fmt(data.ops?.cost) }}</el-descriptions-item>
            <el-descriptions-item label="线索数">{{ data.ops?.leads || 0 }}</el-descriptions-item>
            <el-descriptions-item label="加微数">{{ data.ops?.wechat || 0 }}</el-descriptions-item>
            <el-descriptions-item label="成交数">{{ data.ops?.deals || 0 }}</el-descriptions-item>
            <el-descriptions-item label="线索成本">¥{{ data.ops?.cpl || 0 }}</el-descriptions-item>
            <el-descriptions-item label="获客成本">¥{{ data.ops?.cac || 0 }}</el-descriptions-item>
          </el-descriptions>
          <div ref="opsRef" class="chart" style="height: 210px; margin-top: 10px"></div>
        </div>
      </el-col>
    </el-row>

    <!-- 部门业绩汇总 -->
    <div class="card">
      <div class="card-title">部门业绩汇总（{{ month }}）</div>
      <el-row :gutter="14">
        <el-col :span="8" v-for="d in deptSummary" :key="d.code">
          <el-card shadow="never" class="dept-sum-card" @click="goDept(d.code)">
            <div class="ds-name">{{ d.name }}</div>
            <div class="ds-amount">¥{{ wan(d.amount || 0) }}</div>
            <div class="ds-sub">{{ d.orders || 0 }} 单 · 目标 ¥{{ wan(d.target || 0) }}</div>
            <el-progress :percentage="Math.min(d.completion || 0, 100)"
                         :status="d.completion >= 100 ? 'success' : (d.completion >= 60 ? '' : 'exception')"
                         :stroke-width="10" style="margin-top:10px" />
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 排行榜 -->
    <div class="card">
      <div class="card-title">
        业绩排行榜
        <el-radio-group v-model="rankScope" size="small" style="float: right" @change="loadRank">
          <el-radio-button value="person">个人</el-radio-button>
        </el-radio-group>
      </div>
      <el-table :data="rankList" size="small" stripe max-height="360">
        <el-table-column prop="rank" label="排名" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.rank === 1" type="danger" size="small">第1名</el-tag>
            <el-tag v-else-if="row.rank === 2" type="warning" size="small">第2名</el-tag>
            <el-tag v-else-if="row.rank === 3" type="success" size="small">第3名</el-tag>
            <span v-else>{{ row.rank }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="department" label="部门" width="100" />
        <el-table-column prop="team" label="小组" width="110" />
        <el-table-column prop="amount" label="业绩" width="130" align="right">
          <template #default="{ row }">¥{{ fmt(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="orders" label="订单数" width="90" align="center" />
        <el-table-column prop="calls" label="通话量" width="90" align="center" />
        <el-table-column prop="target" label="目标" width="120" align="right">
          <template #default="{ row }">¥{{ fmt(row.target) }}</template>
        </el-table-column>
        <el-table-column label="完成率" min-width="180">
          <template #default="{ row }">
            <el-progress :percentage="Math.min(row.completion, 100)"
                         :status="row.completion >= 100 ? 'success' : (row.completion >= 60 ? '' : 'exception')"
                         :text-inside="true" :stroke-width="16" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 部门快捷入口 -->
    <div class="card">
      <div class="card-title">部门看板快捷入口</div>
      <el-row :gutter="14">
        <el-col :span="8" v-for="d in deptCards" :key="d.code">
          <el-card shadow="hover" class="dept-card" @click="goDept(d.code)">
            <div class="dept-name">
              <el-icon :size="20"><component :is="d.icon" /></el-icon>
              {{ d.name }}
            </div>
            <div class="dept-stat">{{ d.stat }}</div>
            <div class="dept-sub">{{ d.sub }}</div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 公司月度目标设置（合并自「全公司业绩中心」） -->
    <el-dialog v-model="targetDialogVisible" title="设置公司月度目标" width="420px" align-center>
      <div style="font-size:13px;color:var(--text-sub);margin-bottom:14px">
        当前月份：<b>{{ month }}</b>　｜　现目标：¥{{ wan((data.performance || {}).target || 0) }}
      </div>
      <el-input v-model="targetAmount" type="number" placeholder="请输入公司月度目标金额（元）">
        <template #prepend>¥</template>
      </el-input>
      <template #footer>
        <el-button @click="targetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingTarget" @click="saveTarget">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Close, Download, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { dashApi, salesApi, accApi } from '@/api'
import { useUserStore } from '@/store/user'
import { exportElementToPdf } from '@/utils/exportPdf'
import dayjs from 'dayjs'

const router = useRouter()
const store = useUserStore()
const month = ref(dayjs().format('YYYY-MM'))
const rankScope = ref('person')
const data = reactive({})
const rankList = ref([])
const reportRef = ref()
const exporting = ref(false)

const exportPdf = async () => {
  if (!reportRef.value) return
  exporting.value = true
  try {
    await exportElementToPdf(reportRef.value, `经营总览报表-${month.value}.pdf`)
  } finally { exporting.value = false }
}
const loading = ref(false)

/* 新手引导（localStorage 记忆） */
const showGuide = ref(localStorage.getItem('finops_guide_dashboard') !== '1')
const dismissGuide = () => { showGuide.value = false; localStorage.setItem('finops_guide_dashboard', '1') }

const trendRef = ref()
const deptRef = ref()
const attRef = ref()
const opsRef = ref()
const gaugeRef = ref()
let charts = []

const fmt = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))
const wan = (n) => (n >= 10000 ? (n / 10000).toFixed(1) + '万' : fmt(n))

/* 欢迎语 */
const hour = new Date().getHours()
const greet = hour < 6 ? '凌晨好' : hour < 9 ? '早上好' : hour < 12 ? '上午好'
  : hour < 14 ? '中午好' : hour < 18 ? '下午好' : '晚上好'
const todayText = dayjs().format('YYYY年M月D日 dddd')
const roleName = computed(() => store.roleName)

/* 预警数据 */
const warnings = reactive([
  { key: 'approval', level: 'danger', icon: '✅', label: '待我审批', count: 0, path: '/hr/approval' },
  { key: 'overdue', level: 'warning', icon: '⏰', label: '逾期做账', count: 0, path: '/accounting/tasks' },
  { key: 'expireSales', level: 'warning', icon: '📝', label: '合同将到期', count: 0, path: '/sales/customers' },
  { key: 'expireAcc', level: 'warning', icon: '📒', label: '代账将到期', count: 0, path: '/accounting/clients' }
])
const expiringList = ref([])
const expiringTotal = computed(() => warnings[2].count + warnings[3].count)

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
const daysBetween = (d) => {
  const t = dayjs(d)
  return t.isValid() ? t.diff(dayjs().startOf('day'), 'day') : 999
}

const cards = computed(() => {
  const p = data.performance || {}
  const a = data.accounting || {}
  const o = data.ops || {}
  return [
    { label: '本月业绩', value: '¥' + wan(p.amount || 0), sub: `目标 ¥${wan(p.target || 0)}`, color: '#d93026' },
    { label: '目标完成率', value: (p.completion || 0) + '%', sub: `订单 ${p.orders || 0} 单`, color: p.completion >= 100 ? '#0f9960' : '#1f2329' },
    { label: '已回款', value: '¥' + wan(p.received || 0), sub: `待收 ¥${wan(p.receivable || 0)}`, color: '#0f9960' },
    { label: '线索总数', value: fmt(data.leads?.total || 0), sub: `成交 ${data.leads?.dealt || 0} / 跟进 ${data.leads?.following || 0}`, color: '#2f6fed' },
    { label: '做账完成率', value: (a.completion || 0) + '%', sub: `${a.done || 0}/${a.total || 0} 户 · 逾期 ${a.overdue || 0}`, color: a.completion >= 90 ? '#0f9960' : '#d9822b' },
    { label: '投放 ROI', value: (o.roi || 0), sub: `消耗 ¥${wan(o.cost || 0)} · 成交 ${o.deals || 0}`, color: (o.roi || 0) >= 3 ? '#0f9960' : '#d9822b' }
  ]
})

const deptCards = computed(() => {
  const find = (code) => (data.departments || []).find(d => d.code === code) || {}
  const s = find('SALES'), a = find('ACCOUNT'), o = data.ops || {}
  return [
    { code: 'SALES', name: '电销部', icon: 'Phone', stat: `¥${wan(s.amount || 0)}`, sub: `${s.orders || 0} 单 · 完成率 ${s.completion || 0}%` },
    { code: 'ACCOUNT', name: '会计部', icon: 'Tickets', stat: `${a.total || 0} 户`, sub: `完成 ${a.done || 0} · 逾期 ${a.overdue || 0}` },
    { code: 'OPS', name: '运营部', icon: 'DataBoard', stat: `${o.leads || 0} 线索`, sub: `ROI ${o.roi || 0} · CPL ¥${o.cpl || 0}` }
  ]
})

const goDept = (code) => router.push(`/department/${code}`)
const go = (path) => router.push(path)

/* 公司月度目标设置（合并自「全公司业绩中心」） */
const targetDialogVisible = ref(false)
const targetAmount = ref(0)
const savingTarget = ref(false)
const openTarget = () => {
  targetAmount.value = Math.round((data.performance || {}).target || 0)
  targetDialogVisible.value = true
}
const saveTarget = async () => {
  savingTarget.value = true
  try {
    await salesApi.batchSetTarget({
      month: month.value,
      scope: 'COMPANY',
      targets: [{ amount_target: Number(targetAmount.value) || 0 }]
    })
    ElMessage.success('公司月度目标已更新')
    targetDialogVisible.value = false
    await loadAll()
  } catch (e) {
    ElMessage.error('保存失败，请重试')
  } finally {
    savingTarget.value = false
  }
}

const deptSummary = computed(() => (data.departments || []).map(d => ({
  code: d.code, name: d.department_name, amount: d.amount,
  orders: d.orders, target: d.target, completion: d.completion
})))

const initCharts = () => {
  charts.forEach(c => c.dispose())
  charts = []
  if (trendRef.value) charts.push(echarts.init(trendRef.value))
  if (deptRef.value) charts.push(echarts.init(deptRef.value))
  if (attRef.value) charts.push(echarts.init(attRef.value))
  if (opsRef.value) charts.push(echarts.init(opsRef.value))
  if (gaugeRef.value) charts.push(echarts.init(gaugeRef.value))
}

const renderCharts = (trend, depts, att, ops) => {
  charts[0]?.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['业绩', '订单数', '投放消耗'], bottom: 0 },
    grid: { left: 60, right: 40, top: 30, bottom: 50 },
    xAxis: { type: 'category', data: (trend || []).map(t => t.month) },
    yAxis: [
      { type: 'value', name: '金额(元)', axisLabel: { formatter: v => v >= 10000 ? v / 10000 + '万' : v } },
      { type: 'value', name: '订单', splitLine: { show: false } }
    ],
    series: [
      { name: '业绩', type: 'bar', data: (trend || []).map(t => t.amount), itemStyle: { color: '#2f6fed', borderRadius: [4, 4, 0, 0] }, barWidth: '32%' },
      { name: '订单数', type: 'line', yAxisIndex: 1, data: (trend || []).map(t => t.orders), itemStyle: { color: '#d93026' }, smooth: true },
      { name: '投放消耗', type: 'line', data: (trend || []).map(t => t.ad_cost), itemStyle: { color: '#d9822b' }, smooth: true }
    ]
  })

  charts[1]?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 70, right: 30, top: 30, bottom: 40 },
    xAxis: { type: 'value', axisLabel: { formatter: v => v >= 10000 ? v / 10000 + '万' : v } },
    yAxis: { type: 'category', data: (depts || []).map(d => d.department_name) },
    series: [
      { name: '实际业绩', type: 'bar', data: (depts || []).map(d => d.amount), itemStyle: { color: '#2f6fed', borderRadius: [0, 4, 4, 0] } },
      { name: '目标', type: 'bar', data: (depts || []).map(d => d.target), itemStyle: { color: '#e6e8eb', borderRadius: [0, 4, 4, 0] }, barGap: '-60%' }
    ],
    legend: { data: ['实际业绩', '目标'], bottom: 0 }
  })

  charts[2]?.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['45%', '70%'],
      data: [
        { value: att?.checked || 0, name: '已打卡', itemStyle: { color: '#0f9960' } },
        { value: att?.late || 0, name: '迟到', itemStyle: { color: '#d9822b' } },
        { value: att?.leave || 0, name: '请假', itemStyle: { color: '#2f6fed' } },
        { value: Math.max((att?.total_staff || 0) - (att?.checked || 0) - (att?.leave || 0), 0), name: '未打卡', itemStyle: { color: '#e6e8eb' } }
      ],
      label: { fontSize: 11 },
      center: ['50%', '48%']
    }]
  })

  charts[3]?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 30, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: (ops?.by_platform || []).map(p => p.platform), axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { formatter: v => v >= 10000 ? v / 10000 + '万' : v } },
    series: [
      { name: '消耗', type: 'bar', data: (ops?.by_platform || []).map(p => p.cost), itemStyle: { color: '#8ab4f8', borderRadius: [4, 4, 0, 0] } },
      { name: '成交额', type: 'bar', data: (ops?.by_platform || []).map(p => p.amount), itemStyle: { color: '#2f6fed', borderRadius: [4, 4, 0, 0] } }
    ],
    legend: { data: ['消耗', '成交额'], bottom: 0 }
  })

  // 目标达成仪表盘
  const comp = (data.performance?.completion || 0)
  charts[4]?.setOption({
    series: [{
      type: 'gauge', startAngle: 210, endAngle: -30, radius: '92%', center: ['50%', '56%'],
      progress: { show: true, width: 14, itemStyle: { color: comp >= 100 ? '#0f9960' : (comp >= 60 ? '#2f6fed' : '#d93026') } },
      axisLine: { lineStyle: { width: 14, color: [[1, '#eef0f4']] } },
      pointer: { show: false },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
      anchor: { show: false },
      detail: { valueAnimation: true, fontSize: 30, fontWeight: 700, offsetCenter: [0, '-4%'],
        formatter: '{value}%', color: comp >= 100 ? '#0f9960' : '#1f2329' },
      title: { show: true, offsetCenter: [0, '26%'], fontSize: 12, color: '#8a919f' },
      data: [{ value: comp, name: '目标完成率' }]
    }]
  })
}

const loadOverview = async () => {
  const res = await dashApi.overview({ month: month.value })
  Object.assign(data, res.data || {})
}

const loadTrend = async () => {
  const res = await dashApi.trend({ months: 6 })
  return res.data || []
}

const loadRank = async () => {
  const res = await dashApi.rank({ month: month.value })
  rankList.value = (res.data || []).slice(0, 20)
}

const loadWarnings = async () => {
  try {
    const todo = await dashApi.todo()
    warnings[0].count = todo.pending_approvals || 0
    warnings[1].count = todo.overdue_accounting_tasks || 0
  } catch (e) {}
  try {
    const sc = await salesApi.expiringCustomers({ days: 30 })
    const list1 = asList(sc).map(x => ({ type: 'sales', name: x.name || x.customer_name || '合同', days: daysBetween(x.expire_at) }))
    warnings[2].count = list1.length
    const ac = await accApi.expiringClients({ days: 60 })
    const list2 = asList(ac).map(x => ({ type: 'account', name: x.name || '代账客户', days: daysBetween(x.service_end) }))
    warnings[3].count = list2.length
    expiringList.value = [...list1, ...list2].sort((a, b) => a.days - b.days).slice(0, 6)
  } catch (e) {}
}

const loadAll = async () => {
  loading.value = true
  try {
    await Promise.all([loadOverview(), loadRank(), loadWarnings()])
    const trend = await loadTrend()
    await nextTick()
    initCharts()
    renderCharts(trend, data.departments, data.attendance, data.ops)
  } finally {
    loading.value = false
  }
}

const onResize = () => charts.forEach(c => c?.resize())

onMounted(async () => {
  await loadAll()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  charts.forEach(c => c?.dispose())
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; overflow: hidden; }
.card-tip { font-size: 12px; font-weight: 400; color: var(--text-sub); margin-left: 8px; }
.stat-card { border-radius: 10px; border: 1px solid var(--border); }
.stat-card .value { font-size: 24px; }
.dept-card { cursor: pointer; border-radius: 10px; }
.dept-card:hover { border-color: var(--primary); }
.dept-name { font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.dept-stat { font-size: 22px; font-weight: 700; color: var(--primary); margin-top: 10px; }
.dept-sub { font-size: 12px; color: var(--text-sub); margin-top: 4px; }

/* 部门业绩汇总卡 */
.dept-sum-card { cursor: pointer; border-radius: 10px; border: 1px solid var(--border); transition: .15s; }
.dept-sum-card:hover { border-color: var(--primary); box-shadow: var(--shadow-hover); }
.ds-name { font-size: 14px; font-weight: 600; }
.ds-amount { font-size: 24px; font-weight: 800; color: var(--primary); margin: 8px 0 2px; }
.ds-sub { font-size: 12px; color: var(--text-sub); }

/* 新手引导条 */
.guide {
  display: flex; align-items: center; gap: 12px;
  background: linear-gradient(135deg, #eef3ff, #f6f9ff);
  border: 1px solid var(--primary-100); border-radius: var(--radius);
  padding: 12px 16px; margin-bottom: 14px;
}
.guide-icon { font-size: 22px; }
.guide-body { flex: 1; }
.guide-title { font-size: 14px; font-weight: 700; color: var(--primary); margin-bottom: 3px; }
.guide-text { font-size: 12.5px; color: var(--text-sub); line-height: 1.7; }
.guide-text b { color: var(--text-main); }

/* 欢迎条 */
.welcome {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--brand-gradient); color: #fff; border-radius: var(--radius);
  padding: 18px 22px; margin-bottom: 14px; box-shadow: var(--shadow-card);
}
.welcome .hi { font-size: 20px; font-weight: 700; }
.welcome .hi .wave { font-size: 18px; }
.welcome .date { font-size: 13px; opacity: .9; margin-top: 4px; }
.welcome-right { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.welcome-right :deep(.el-tag) { border: none; }

/* 仪表盘脚注 */
.gauge-foot { display: flex; justify-content: space-around; font-size: 12px; color: var(--text-sub); margin-top: 4px; }

/* 预警中心 */
.warn-tile {
  border-radius: var(--radius-sm); padding: 14px 12px; cursor: pointer;
  text-align: center; border: 1px solid var(--border-soft); transition: transform .15s, box-shadow .15s;
  background: #fafbfc;
}
.warn-tile:hover { transform: translateY(-2px); box-shadow: var(--shadow-hover); }
.warn-icon { font-size: 22px; }
.warn-num { font-size: 26px; font-weight: 800; margin: 4px 0 2px; }
.warn-label { font-size: 12px; color: var(--text-sub); }
.warn-danger .warn-num { color: var(--danger); }
.warn-warning .warn-num { color: var(--warning); }

/* 到期明细 */
.exp-list { margin-top: 14px; border-top: 1px dashed var(--border); padding-top: 10px; }
.exp-title { font-size: 12px; color: var(--text-sub); margin-bottom: 8px; }
.exp-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid var(--border-soft); }
.exp-name { flex: 1; font-weight: 500; }
.exp-days { color: var(--warning); font-size: 12px; }
.exp-days.urgent { color: var(--danger); font-weight: 600; }
</style>
