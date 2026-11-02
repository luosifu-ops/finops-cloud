<template>
  <div class="page" v-loading="loading" element-loading-text="经营数据加载中…">
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

    <!-- 新手引导条 -->
    <div class="guide" v-if="showGuide">
      <div class="guide-icon">🧭</div>
      <div class="guide-body">
        <div class="guide-title">经营总览 · 使用引导</div>
        <div class="guide-text">① 顶部 6 张指标卡看全局；② <b>目标达成仪表盘</b>看月度进度；③ <b>智能预警中心</b>聚合待审批/逾期/到期，点击可跳转处理；④ 顶栏「消息」随时查看待办。</div>
      </div>
      <el-button text size="small" :icon="Close" @click="dismissGuide">不再提示</el-button>
    </div>

    <!-- 核心指标 -->
    <el-row :gutter="14">
      <el-col :span="4" v-for="(c, i) in cards" :key="c.label">
        <el-card shadow="never" class="stat-card" :class="{ 'hero-card': i === 0 }">
          <div class="label">{{ c.label }}</div>
          <div class="value" :style="i === 0 ? null : { color: c.color }">{{ c.value }}</div>
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
                <div class="warn-top">
                  <span class="warn-icon"><el-icon><component :is="w.iconComp" /></el-icon></span>
                  <span class="warn-num">{{ w.count }}</span>
                </div>
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
  { key: 'approval', level: 'danger', icon: '✅', iconComp: 'CircleCheck', label: '待我审批', count: 0, path: '/hr/approval' },
  { key: 'overdue', level: 'warning', icon: '⏰', iconComp: 'AlarmClock', label: '逾期做账', count: 0, path: '/accounting/tasks' },
  { key: 'expireSales', level: 'warning', icon: '📝', iconComp: 'Document', label: '合同将到期', count: 0, path: '/sales/customers' },
  { key: 'expireAcc', level: 'warning', icon: '📒', iconComp: 'Notebook', label: '代账将到期', count: 0, path: '/accounting/clients' }
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
    { label: '本月业绩', value: '¥' + wan(p.amount || 0), sub: `目标 ¥${wan(p.target || 0)}`, color: '#c3372c' },
    { label: '目标完成率', value: (p.completion || 0) + '%', sub: `订单 ${p.orders || 0} 单`, color: p.completion >= 100 ? '#12865a' : '#1f2329' },
    { label: '已回款', value: '¥' + wan(p.received || 0), sub: `待收 ¥${wan(p.receivable || 0)}`, color: '#12865a' },
    { label: '线索总数', value: fmt(data.leads?.total || 0), sub: `成交 ${data.leads?.dealt || 0} / 跟进 ${data.leads?.following || 0}`, color: '#4a6fa5' },
    { label: '做账完成率', value: (a.completion || 0) + '%', sub: `${a.done || 0}/${a.total || 0} 户 · 逾期 ${a.overdue || 0}`, color: a.completion >= 90 ? '#12865a' : '#c0392f' },
    { label: '投放 ROI', value: (o.roi || 0), sub: `消耗 ¥${wan(o.cost || 0)} · 成交 ${o.deals || 0}`, color: (o.roi || 0) >= 3 ? '#12865a' : '#c0392f' }
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
      { name: '业绩', type: 'bar', data: (trend || []).map(t => t.amount), itemStyle: { color: '#4a6fa5', borderRadius: [4, 4, 0, 0] }, barWidth: '32%' },
      { name: '订单数', type: 'line', yAxisIndex: 1, data: (trend || []).map(t => t.orders), itemStyle: { color: '#c3372c' }, smooth: true },
      { name: '投放消耗', type: 'line', data: (trend || []).map(t => t.ad_cost), itemStyle: { color: '#c0392f' }, smooth: true }
    ]
  })

  charts[1]?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 70, right: 30, top: 30, bottom: 40 },
    xAxis: { type: 'value', axisLabel: { formatter: v => v >= 10000 ? v / 10000 + '万' : v } },
    yAxis: { type: 'category', data: (depts || []).map(d => d.department_name) },
    series: [
      { name: '实际业绩', type: 'bar', data: (depts || []).map(d => d.amount), itemStyle: { color: '#4a6fa5', borderRadius: [0, 4, 4, 0] } },
      { name: '目标', type: 'bar', data: (depts || []).map(d => d.target), itemStyle: { color: '#e6e8eb', borderRadius: [0, 4, 4, 0] }, barGap: '-60%' }
    ],
    legend: { data: ['实际业绩', '目标'], bottom: 0 }
  })

  charts[2]?.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: ['45%', '70%'],
      data: [
        { value: att?.checked || 0, name: '已打卡', itemStyle: { color: '#12865a' } },
        { value: att?.late || 0, name: '迟到', itemStyle: { color: '#c0392f' } },
        { value: att?.leave || 0, name: '请假', itemStyle: { color: '#4a6fa5' } },
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
      { name: '成交额', type: 'bar', data: (ops?.by_platform || []).map(p => p.amount), itemStyle: { color: '#4a6fa5', borderRadius: [4, 4, 0, 0] } }
    ],
    legend: { data: ['消耗', '成交额'], bottom: 0 }
  })

  // 目标达成仪表盘
  const comp = (data.performance?.completion || 0)
  charts[4]?.setOption({
    series: [{
      type: 'gauge', startAngle: 210, endAngle: -30, radius: '92%', center: ['50%', '56%'],
      progress: { show: true, width: 14, itemStyle: { color: comp >= 100 ? '#12865a' : (comp >= 60 ? '#4a6fa5' : '#c3372c') } },
      axisLine: { lineStyle: { width: 14, color: [[1, '#eef0f4']] } },
      pointer: { show: false },
      axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
      anchor: { show: false },
      detail: { valueAnimation: true, fontSize: 30, fontWeight: 700, offsetCenter: [0, '-4%'],
        formatter: '{value}%', color: comp >= 100 ? '#12865a' : '#1f2329' },
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
/* ============================================================================
   经营总览 —— 全站视觉标杆页
   ========================================================================== */
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  gap: 18px; margin-bottom: 20px; padding-bottom: 16px;
  border-bottom: 1px solid var(--border-soft); position: relative;
}
.page-header::after {
  content: ''; position: absolute; left: 0; bottom: -1px; width: 132px; height: 1px;
  background: linear-gradient(90deg, var(--primary), rgba(74, 111, 165, 0));
}
.page-header .page-title { font-size: 23px; font-weight: 700; letter-spacing: -0.4px; margin: 0; }

.card-title {
  font-size: 15px; font-weight: 650; margin-bottom: 16px;
  overflow: hidden; letter-spacing: -0.15px;
}
.card-tip { font-size: 11.5px; font-weight: 400; color: var(--text-faint); margin-left: 10px; }

/* ---------- KPI 卡 ---------- */
.stat-card { border-radius: var(--radius); }
.stat-card .value { font-size: 26px; }
/* 首张「旗舰卡」：深墨蓝底 + 金色顶线，全场唯一的重色块，作为视觉锚点 */
.stat-card.hero-card {
  background:
    radial-gradient(300px 180px at 92% -20%, rgba(108, 147, 200, 0.45) 0%, rgba(13, 17, 23, 0) 68%),
    linear-gradient(150deg, #1a2230 0%, #141b26 58%, #0f141c 100%);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow:
    0 2px 4px rgba(13, 17, 23, 0.10),
    0 18px 40px -20px rgba(13, 17, 23, 0.50);
  overflow: hidden;
}
.stat-card.hero-card::before {
  content: ''; position: absolute; left: 0; right: 0; top: 0; height: 2px;
  background: linear-gradient(90deg, #9fbad9, rgba(155, 184, 217, 0.15));
}
.stat-card.hero-card::after {
  background: radial-gradient(circle, rgba(155, 184, 217, 0.14) 0%, transparent 70%);
}
.stat-card.hero-card .label { color: rgba(230, 236, 245, 0.66); }
.stat-card.hero-card .value { color: #fff !important; text-shadow: 0 2px 18px rgba(108, 147, 200, 0.45); }
.stat-card.hero-card .sub { color: rgba(188, 208, 232, 0.82); }

.dept-card { cursor: pointer; border-radius: var(--radius); }
.dept-card:hover { border-color: var(--primary-200); }
.dept-name {
  font-size: 15px; font-weight: 650;
  display: flex; align-items: center; gap: 9px; color: var(--text-main);
}
.dept-name :deep(.el-icon) { color: var(--primary); }
.dept-stat {
  font-size: 23px; font-weight: 700; color: var(--primary-700);
  margin-top: 12px; letter-spacing: -0.6px;
}
.dept-sub { font-size: 11.5px; color: var(--text-weak); margin-top: 5px; }

/* 部门业绩汇总卡 */
.dept-sum-card {
  cursor: pointer; border-radius: var(--radius);
  border: 1px solid var(--border-soft); transition: all 240ms var(--ease-spring);
}
.dept-sum-card:hover {
  border-color: var(--primary-200);
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}
.ds-name { font-size: 13.5px; font-weight: 600; color: var(--text-sub); }
.ds-amount {
  font-size: 25px; font-weight: 700; color: var(--text-main);
  margin: 10px 0 3px; letter-spacing: -0.8px;
}
.ds-sub { font-size: 11.5px; color: var(--text-weak); }

/* ---------- 新手引导：弱化为「便签」而非「广告横幅」 ---------- */
.guide {
  display: flex; align-items: center; gap: 14px;
  background: #fff;
  border: 1px solid var(--border-soft);
  border-left: 2px solid var(--primary);
  border-radius: var(--radius-sm);
  padding: 13px 18px; margin-bottom: 16px;
  box-shadow: var(--shadow-xs);
}
.guide-icon { font-size: 17px; opacity: 0.85; }
.guide-body { flex: 1; }
.guide-title {
  font-size: 12.5px; font-weight: 650; color: var(--text-main);
  margin-bottom: 3px; letter-spacing: 0.01em;
}
.guide-text { font-size: 12px; color: var(--text-sub); line-height: 1.65; }
.guide-text b { color: var(--text-main); font-weight: 650; }

/* ---------- 欢迎条 ---------- */
.welcome {
  position: relative; overflow: hidden;
  display: flex; justify-content: space-between; align-items: center;
  background:
    radial-gradient(520px 240px at 88% -34%, rgba(108, 147, 200, 0.42) 0%, rgba(13, 17, 23, 0) 70%),
    linear-gradient(118deg, #1a2230 0%, #141b26 56%, #0f141c 100%);
  color: #fff; border-radius: var(--radius);
  padding: 22px 26px; margin-bottom: 18px;
  box-shadow:
    0 2px 4px rgba(11, 26, 46, 0.08),
    0 20px 46px -22px rgba(11, 26, 46, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.07);
}
/* 底部一道金蓝渐变线：全站统一的「贵感签名」 */
.welcome::after {
  content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 2px;
  background: linear-gradient(90deg,
    rgba(108, 147, 200, 0.9) 0%,
    rgba(155, 184, 217, 0.5) 42%,
    rgba(155, 184, 217, 0) 100%);
}
/* 右上角极淡网格，避免大面积纯色显廉价 */
.welcome::before {
  content: ''; position: absolute; inset: 0; pointer-events: none; opacity: 0.4;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 38px 38px;
  mask-image: linear-gradient(90deg, transparent 30%, #000 100%);
  -webkit-mask-image: linear-gradient(90deg, transparent 30%, #000 100%);
}
.welcome-left { position: relative; z-index: 1; }
.welcome .hi {
  font-size: 21px; font-weight: 700; letter-spacing: -0.3px;
  display: flex; align-items: center; gap: 8px;
}
.welcome .hi .wave { font-size: 17px; }
.welcome .date {
  font-size: 12.5px; color: rgba(226, 236, 248, 0.68); margin-top: 6px;
  letter-spacing: 0.02em;
}
.welcome-right {
  display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end;
  position: relative; z-index: 1;
}
.welcome-right :deep(.el-tag) {
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(6px);
  font-weight: 550;
}
.welcome-right :deep(.el-tag--primary) {
  background: linear-gradient(135deg, rgba(74, 111, 240, 0.9), rgba(42, 79, 212, 0.9));
  border-color: rgba(122, 152, 255, 0.4);
  color: #fff;
}
.welcome-right :deep(.el-tag--warning) {
  background: rgba(214, 186, 134, 0.16);
  border-color: rgba(214, 186, 134, 0.40);
  color: #e8d5ae;
}

.gauge-foot {
  display: flex; justify-content: space-around;
  font-size: 11.5px; color: var(--text-weak); margin-top: 6px;
  padding-top: 12px; border-top: 1px solid var(--border-soft);
}

/* ---------- 预警卡 ---------- */
.warn-tile {
  border-radius: var(--radius-sm); padding: 16px 17px; cursor: pointer;
  border: 1px solid var(--border-soft); background: var(--card-bg);
  transition: all 240ms var(--ease-spring);
  position: relative; overflow: hidden;
}
.warn-tile::after {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 2px;
  opacity: 0.9;
}
.warn-tile:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
  border-color: var(--primary-200);
}
.warn-top {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
}
.warn-icon {
  width: 34px; height: 34px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 17px; flex: none;
}
.warn-num {
  font-size: 27px; font-weight: 750; line-height: 1;
  letter-spacing: -1px; font-variant-numeric: tabular-nums;
}
.warn-label {
  font-size: 12px; color: var(--text-sub); margin-top: 11px;
  font-weight: 500; letter-spacing: 0.02em;
}
.warn-danger .warn-icon { background: var(--danger-50); color: var(--danger); }
.warn-danger .warn-num { color: var(--danger); }
.warn-danger::after { background: linear-gradient(180deg, var(--danger-500), var(--danger)); }
.warn-warning .warn-icon { background: var(--warning-50); color: var(--warning); }
.warn-warning .warn-num { color: var(--warning); }
.warn-warning::after { background: linear-gradient(180deg, var(--warning-500), var(--warning)); }
.warn-success .warn-icon { background: var(--success-50); color: var(--success); }
.warn-success .warn-num { color: var(--success); }

/* ---------- 到期明细 ---------- */
.exp-list {
  margin-top: 16px; border-top: 1px solid var(--border-soft); padding-top: 14px;
}
.exp-title {
  font-size: 11px; color: var(--text-weak); margin-bottom: 10px;
  letter-spacing: 0.10em; font-weight: 650; text-transform: uppercase;
}
.exp-row {
  display: flex; align-items: center; gap: 11px; padding: 9px 0;
  font-size: 13px; border-bottom: 1px solid var(--border-soft);
  transition: background var(--dur-fast);
}
.exp-row:last-child { border-bottom: none; }
.exp-row:hover { background: var(--surface-2); }
.exp-name { flex: 1; font-weight: 550; color: var(--text-main); }
.exp-days {
  color: var(--warning); font-size: 11.5px; font-weight: 550;
  font-variant-numeric: tabular-nums;
}
.exp-days.urgent { color: var(--danger); font-weight: 700; }
</style>
