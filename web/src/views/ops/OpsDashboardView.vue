<template>
  <div class="ops-dashboard">
    <!-- 顶部操作栏：日期筛选 + 导出 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <div class="title-wrap">
          <h2>投放总览</h2>
          <span class="sub-title">按平台拆分 · 抖音素材 / 抖音直播 / 闲鱼</span>
        </div>
        <div class="actions">
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
            start-placeholder="开始日期" end-placeholder="结束日期" style="width:250px"
            :clearable="true" @change="loadData" />
          <el-button @click="loadData" :loading="loading">刷新</el-button>
          <el-button @click="exportCsv" :loading="exporting">导出</el-button>
        </div>
      </div>
    </el-card>

    <!-- 合计汇总条 -->
    <el-card shadow="never" class="total-card" v-loading="loading">
      <template #header>
        <div class="card-head">
          <span class="card-title">全部平台合计</span>
          <span class="card-sub" v-if="total.days >= 0">统计天数：{{ total.days || 0 }} 天</span>
        </div>
      </template>
      <div class="metric-grid">
        <div class="metric-item" v-for="m in metricDefs" :key="m.prop">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value" :class="m.valueClass">{{ fmtVal(total[m.prop], m.prop) }}</div>
        </div>
      </div>
    </el-card>

    <!-- 三平台卡片 -->
    <el-row :gutter="16" class="platform-row">
      <el-col :span="8" v-for="p in platforms" :key="p.key">
        <el-card shadow="hover" class="platform-card" v-loading="loading">
          <template #header>
            <div class="plat-head">
              <div class="plat-title">
                <span class="plat-dot" :style="{ background: platColor(p.key) }"></span>
                <span>{{ p.platform_name }}</span>
                <el-tag size="small" type="info" v-if="!p.has_platform">未配置</el-tag>
              </div>
              <el-button type="primary" size="small" @click="openInput(p)">录入数据</el-button>
            </div>
          </template>

          <div class="plat-metrics">
            <div class="pm-item">
              <div class="pm-label">花费</div>
              <div class="pm-value cost">¥{{ fmtVal(p.cost) }}</div>
            </div>
            <div class="pm-item">
              <div class="pm-label">线索数</div>
              <div class="pm-value">{{ p.lead_count }}</div>
            </div>
            <div class="pm-item">
              <div class="pm-label">有效线索</div>
              <div class="pm-value ok">{{ p.valid_lead }}</div>
            </div>
            <div class="pm-item">
              <div class="pm-label">单条线索成本</div>
              <div class="pm-value warn">¥{{ p.cpl }}</div>
            </div>
          </div>

          <div class="plat-mini-grid">
            <div><span>曝光量</span><b>{{ p.impression }}</b></div>
            <div><span>点击量</span><b>{{ p.click }}</b></div>
            <div><span>加微数</span><b>{{ p.wechat_added }}</b></div>
            <div><span>成交数</span><b>{{ p.deal_count }}</b></div>
            <div><span>成交金额</span><b>¥{{ p.deal_amount }}</b></div>
            <div><span>有效率</span><b>{{ p.lead_valid_rate }}%</b></div>
          </div>

          <div class="plat-footer">
            <el-button link type="primary" size="small" @click="openDetail(p)">
              查看明细（{{ detailCount[p.key] || 0 }}）→
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 录入弹窗 -->
    <el-dialog v-model="inputVisible" :title="`录入投放数据 · ${currentPlatform?.platform_name || ''}`" width="680px">
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px"
        :title="`平台：${currentPlatform?.platform_name || ''}　同一日期重复录入将更新当日数据`" />
      <el-form :model="inputForm" label-width="110px" size="default">
        <el-form-item label="投放日期" required>
          <el-date-picker v-model="inputForm.date" type="date" value-format="YYYY-MM-DD"
            placeholder="默认当天" style="width:220px" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="花费(元)"><el-input-number v-model="inputForm.cost" :min="0" :precision="2" :controls="false" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="曝光量"><el-input-number v-model="inputForm.impression" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="点击量"><el-input-number v-model="inputForm.click" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="线索数"><el-input-number v-model="inputForm.lead_count" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="有效线索"><el-input-number v-model="inputForm.valid_lead" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="加微数"><el-input-number v-model="inputForm.wechat_added" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="访问量"><el-input-number v-model="inputForm.visit_count" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="成交数"><el-input-number v-model="inputForm.deal_count" :min="0" :controls="false" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="成交金额(元)"><el-input-number v-model="inputForm.deal_amount" :min="0" :precision="2" :controls="false" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="成本(元)"><el-input-number v-model="inputForm.cost_input" :min="0" :precision="2" :controls="false" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="inputForm.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="inputVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitInput">保存并自动统计</el-button>
      </template>
    </el-dialog>

    <!-- 平台明细抽屉 -->
    <el-drawer v-model="detailVisible" :title="`${currentPlatform?.platform_name || ''} · 投放明细`" size="760px">
      <div class="detail-toolbar">
        <el-button type="primary" size="small" @click="openInput(currentPlatform)">+ 录入数据</el-button>
        <span class="detail-tip">共 {{ detailList.length }} 条记录</span>
      </div>
      <el-table :data="detailList" v-loading="detailLoading" border stripe size="small" max-height="640">
        <el-table-column prop="date" label="日期" width="110" />
        <el-table-column prop="cost" label="花费" width="90" />
        <el-table-column prop="impression" label="曝光" width="90" />
        <el-table-column prop="click" label="点击" width="80" />
        <el-table-column prop="lead_count" label="线索" width="70" />
        <el-table-column prop="valid_lead" label="有效" width="70" />
        <el-table-column prop="wechat_added" label="加微" width="70" />
        <el-table-column prop="deal_count" label="成交" width="70" />
        <el-table-column prop="deal_amount" label="成交额" width="100" />
        <el-table-column prop="cpl" label="CPL" width="80" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="editDetail(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteDetail(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http, { opsApi } from '@/api'

const loading = ref(false)
const exporting = ref(false)
const platforms = ref([])
const total = ref({})
const dateRange = ref([])

const metricDefs = [
  { prop: 'cost', label: '花费', valueClass: 'cost' },
  { prop: 'impression', label: '曝光量' },
  { prop: 'click', label: '点击量' },
  { prop: 'lead_count', label: '线索数' },
  { prop: 'valid_lead', label: '有效线索', valueClass: 'ok' },
  { prop: 'wechat_added', label: '加微数' },
  { prop: 'visit_count', label: '访问量' },
  { prop: 'deal_count', label: '成交数' },
  { prop: 'deal_amount', label: '成交金额', valueClass: 'ok' },
  { prop: 'cpl', label: '单条线索成本', valueClass: 'warn' },
]

function fmtVal(v, prop) {
  if (v == null) return '0'
  const n = Number(v)
  if (isNaN(n)) return v
  if (prop === 'cpl' || prop === 'deal_amount' || prop === 'cost') {
    return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

function platColor(key) {
  return { DOUYIN_MATERIAL: '#409eff', DOUYIN_LIVE: '#f56c6c', XIANYU: '#e6a23c' }[key] || '#909399'
}

function buildParams() {
  const p = {}
  if (dateRange.value && dateRange.value.length === 2) {
    p.start_date = dateRange.value[0]
    p.end_date = dateRange.value[1]
  }
  return p
}

async function loadData() {
  loading.value = true
  try {
    const r = await opsApi.overviewByPlatform(buildParams())
    const d = r?.data || {}
    platforms.value = d.platforms || []
    total.value = d.total || {}
    // 各平台明细条数
    for (const p of platforms.value) {
      const ids = p.platform_ids || []
      if (!ids.length) { detailCount.value[p.key] = 0; continue }
      try {
        const res = await opsApi.dailyStats({ platform: ids[0], ...buildParams(), page_size: 1 })
        detailCount.value[p.key] = Array.isArray(res) ? res.length : (res?.count || 0)
      } catch { detailCount.value[p.key] = 0 }
    }
  } catch (e) { /* 拦截器已提示 */ } finally { loading.value = false }
}

const detailCount = reactive({})
const inputVisible = ref(false)
const saving = ref(false)
const currentPlatform = ref(null)
const editingStatId = ref(null)
const inputForm = reactive({
  date: '', cost: 0, impression: 0, click: 0, lead_count: 0, valid_lead: 0,
  wechat_added: 0, visit_count: 0, deal_count: 0, deal_amount: 0, cost_input: 0, remark: ''
})

function todayStr() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function resetInputForm() {
  Object.assign(inputForm, {
    date: todayStr(), cost: 0, impression: 0, click: 0, lead_count: 0, valid_lead: 0,
    wechat_added: 0, visit_count: 0, deal_count: 0, deal_amount: 0, cost_input: 0, remark: ''
  })
  editingStatId.value = null
}

function openInput(p) {
  if (!p || !p.platform_ids || !p.platform_ids.length) {
    return ElMessage.warning(`平台「${p?.platform_name || ''}」尚未配置，请先在「数据录入 → 投放平台」中创建`)
  }
  currentPlatform.value = p
  resetInputForm()
  inputVisible.value = true
}

// 后端 click_rate=DecimalField(max_digits=6, decimal_places=2)，整数部分最多 4 位；
// 前端原样提交越界值会触发 400「请确保总计不超过 6 个数字」。这里做安全钳制，
// 避免异常投放数据（如点击>曝光）把整录入请求打挂。2026-11-24 修复。
function safeDecimal(v, maxAbs) {
  const n = Number(v)
  if (!isFinite(n)) return 0
  return Math.max(-maxAbs, Math.min(maxAbs, Number(n.toFixed(2))))
}

async function submitInput() {
  if (!inputForm.date) return ElMessage.warning('请选择投放日期')
  const platformId = currentPlatform.value.platform_ids[0]
  saving.value = true
  try {
    const payload = {
      platform: platformId, date: inputForm.date,
      cost: inputForm.cost || 0, impression: inputForm.impression || 0,
      click: inputForm.click || 0, lead_count: inputForm.lead_count || 0,
      valid_lead: inputForm.valid_lead || 0, wechat_added: inputForm.wechat_added || 0,
      visit_count: inputForm.visit_count || 0, deal_count: inputForm.deal_count || 0,
      deal_amount: inputForm.deal_amount || 0, cost_input: inputForm.cost_input || 0,
      remark: inputForm.remark || '',
    }
    // 自动计算点击率/平均点击成本（后端也会算，这里赋值保持一致）；钳制到字段上限防 400
    payload.click_rate = payload.impression
      ? safeDecimal(payload.click / payload.impression * 100, 9999.99) : 0
    payload.avg_click_cost = payload.click
      ? safeDecimal(payload.cost / payload.click, 99999999.99) : 0

    // 2026-11-24 修复：兑现「同一日期重复录入将更新当日数据」承诺。
    // 从卡片「录入数据」进入时 editingStatId 为空，若该平台该日已有记录则改为更新，
    // 避免插入重复行（重复行会让明细/汇总翻倍，且在部分场景下触发唯一约束 400）。
    let targetId = editingStatId.value
    if (!targetId) {
      try {
        const exist = await opsApi.dailyStats({ platform: platformId, start_date: inputForm.date, end_date: inputForm.date, page_size: 5 })
        const rows = Array.isArray(exist) ? exist : (exist?.results || [])
        if (rows.length) targetId = rows[0].id
      } catch (e) { /* 查重失败则退回新建，不阻断录入 */ }
    }
    if (targetId) {
      await opsApi.updateDailyStat(targetId, payload)
      ElMessage.success('已更新当日数据，统计已刷新')
    } else {
      await opsApi.createDailyStat(payload)
      ElMessage.success('录入成功，统计已刷新')
    }
    inputVisible.value = false
    await loadData()
    if (detailVisible.value && currentPlatform.value) await loadDetail(currentPlatform.value)
  } catch (e) { /* 拦截器已提示 */ } finally { saving.value = false }
}

// 明细抽屉
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailList = ref([])

async function loadDetail(p) {
  if (!p || !p.platform_ids || !p.platform_ids.length) return
  detailLoading.value = true
  try {
    const res = await opsApi.dailyStats({ platform: p.platform_ids[0], ...buildParams(), page_size: 200 })
    detailList.value = Array.isArray(res) ? res : (res?.results || [])
  } catch { detailList.value = [] } finally { detailLoading.value = false }
}

function openDetail(p) {
  currentPlatform.value = p
  detailVisible.value = true
  loadDetail(p)
}

function editDetail(row) {
  currentPlatform.value = platforms.value.find(p => (p.platform_ids || []).includes(row.platform)) || currentPlatform.value
  Object.assign(inputForm, {
    date: row.date, cost: Number(row.cost || 0), impression: row.impression || 0,
    click: row.click || 0, lead_count: row.lead_count || 0, valid_lead: row.valid_lead || 0,
    wechat_added: row.wechat_added || 0, visit_count: row.visit_count || 0,
    deal_count: row.deal_count || 0, deal_amount: Number(row.deal_amount || 0),
    cost_input: Number(row.cost_input || 0), remark: row.remark || ''
  })
  editingStatId.value = row.id
  inputVisible.value = true
}

async function deleteDetail(row) {
  try {
    await ElMessageBox.confirm('确认删除这条投放记录？删除后统计将自动更新。', '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await http.delete(`/ops/daily-stats/${row.id}/`)
    ElMessage.success('已删除')
    await loadData()
    if (currentPlatform.value) await loadDetail(currentPlatform.value)
  } catch (e) { /* 拦截器已提示 */ }
}

function exportCsv() {
  const header = ['平台', '花费', '曝光量', '点击量', '线索数', '有效线索', '加微数', '访问量', '成交数', '成交金额', '单条线索成本']
  const rows = platforms.value.concat([total.value]).map(p => [
    p.platform_name, p.cost, p.impression, p.click, p.lead_count, p.valid_lead,
    p.wechat_added, p.visit_count, p.deal_count, p.deal_amount, p.cpl,
  ])
  const csv = '\uFEFF' + [header, ...rows].map(r => r.map(v => `"${v ?? 0}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `投放总览_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
  ElMessage.success('已导出')
}

onMounted(loadData)
</script>

<style scoped>
.ops-dashboard { padding: 2px; }
.toolbar-card { margin-bottom: 14px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-wrap { display: flex; align-items: baseline; gap: 12px; }
.title-wrap h2 { margin: 0; font-size: 20px; }
.sub-title { color: #909399; font-size: 13px; }
.actions { display: flex; gap: 8px; }
.total-card { margin-bottom: 14px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-weight: 600; font-size: 15px; }
.card-sub { color: #909399; font-size: 13px; }
.metric-grid { display: grid; grid-template-columns: repeat(10, 1fr); gap: 8px; }
.metric-item { text-align: center; padding: 8px 2px; border-right: 1px solid #f0f0f0; }
.metric-item:last-child { border-right: none; }
.metric-label { font-size: 12px; color: #909399; }
.metric-value { font-size: 17px; font-weight: 600; margin-top: 5px; }
.metric-value.cost { color: #303133; }
.metric-value.ok { color: #67c23a; }
.metric-value.warn { color: #e6a23c; }
.platform-row { margin-bottom: 14px; }
.platform-card { min-height: 340px; }
.plat-head { display: flex; justify-content: space-between; align-items: center; }
.plat-title { display: flex; align-items: center; gap: 8px; font-weight: 600; }
.plat-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.plat-metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 14px; }
.pm-item { background: #f8f9fb; border-radius: 6px; padding: 10px 12px; }
.pm-label { font-size: 12px; color: #909399; }
.pm-value { font-size: 20px; font-weight: 600; margin-top: 4px; }
.pm-value.cost { color: #303133; }
.pm-value.ok { color: #67c23a; }
.pm-value.warn { color: #e6a23c; }
.plat-mini-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px 12px; font-size: 13px; }
.plat-mini-grid > div { display: flex; justify-content: space-between; border-bottom: 1px dashed #f0f0f0; padding: 4px 0; }
.plat-mini-grid span { color: #909399; }
.plat-mini-grid b { font-weight: 600; }
.plat-footer { margin-top: 12px; text-align: right; }
.detail-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.detail-tip { color: #909399; font-size: 13px; }
@media (max-width: 1200px) {
  .metric-grid { grid-template-columns: repeat(5, 1fr); }
  .platform-row .el-col { width: 100% !important; margin-bottom: 12px; }
}
</style>
