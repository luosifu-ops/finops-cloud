<template>
  <div class="lead-entry">
    <el-tabs v-model="tab">
      <!-- ============ 线索录入中心 ============ -->
      <el-tab-pane label="线索录入中心" name="list">
        <!-- 顶部指标条 -->
        <el-row :gutter="16" class="stat-row">
          <el-col :span="6">
            <el-card shadow="never" class="mini-card">
              <div class="mini-label">线索总数</div>
              <div class="mini-value">{{ boardTotal }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never" class="mini-card">
              <div class="mini-label">成交数</div>
              <div class="mini-value ok">{{ boardDeal }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never" class="mini-card">
              <div class="mini-label">整体转化率</div>
              <div class="mini-value">{{ boardRate }}%</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never" class="mini-card">
              <div class="mini-label">签单总额(元)</div>
              <div class="mini-value">{{ boardAmount.toLocaleString() }}</div>
            </el-card>
          </el-col>
        </el-row>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>线索转化分析与跟进明细</span>
              <div>
                <el-button @click="loadData">刷新</el-button>
              </div>
            </div>
          </template>

          <el-form :inline="true" class="filter-bar">
            <el-form-item label="平台">
              <el-select v-model="filters.channel" placeholder="全部平台" clearable style="width:140px">
                <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="账号">
              <el-input v-model="filters.account" placeholder="来源账号编号" clearable style="width:160px" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" plain @click="loadData">查询</el-button>
              <el-button @click="resetFilter">重置</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="list" v-loading="loading" border stripe size="default" max-height="560">
            <el-table-column prop="lead_name" label="客户姓名" min-width="100" />
            <el-table-column label="联系方式" min-width="130">
              <template #default="{ row }">
                <span>{{ row.contact_value || row.lead_phone || '-' }}</span>
                <el-tag size="small" type="info" style="margin-left:4px">{{ row.contact_type_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="来源平台" width="100">
              <template #default="{ row }"><el-tag size="small">{{ row.channel_name }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="source_account_no" label="来源账号" width="120" />
            <el-table-column prop="customer_need" label="客户需求" min-width="140" show-overflow-tooltip />
            <el-table-column prop="contact_person" label="对接人" width="90" />
            <el-table-column label="归属运营" width="110">
              <template #default="{ row }">
                <el-link v-if="row.ops_owner" type="primary" @click="penetrate(row.ops_owner, row.ops_owner_name)">{{ row.ops_owner_name }}</el-link>
                <span v-else>{{ row.ops_owner_name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="承接人" width="110">
              <template #default="{ row }">
                <el-link v-if="row.closer" type="success" @click="penetrate(row.closer, row.closer_name)">{{ row.closer_name }}</el-link>
                <el-tag v-else-if="row.in_pool" type="warning" size="small">公海待领</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="获客成本" width="100">
              <template #default="{ row }">{{ num(row.acquisition_cost) }}</template>
            </el-table-column>
            <el-table-column label="签单金额" width="110">
              <template #default="{ row }">
                <span :class="row.deal_amount > 0 ? 'amt' : ''">{{ num(row.deal_amount) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="转化" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.is_deal" type="success" size="small">已成交</el-tag>
                <el-tag v-else type="info" size="small">未成交</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openFollow(row)">跟进</el-button>
                <el-button link type="info" @click="penetrate(row.ops_owner || row.closer, row.ops_owner_name || row.closer_name)">穿透</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ============ 数据看板 ============ -->
      <el-tab-pane label="数据看板（按平台/账号）" name="board">
        <el-card shadow="never">
          <template #header><span>各投放平台线索与转化统计（用于判断平台优化 / 关停）</span></template>
          <el-table :data="boardRows" border stripe size="default" v-loading="boardLoading">
            <el-table-column prop="channel" label="投放平台" min-width="120" />
            <el-table-column prop="total" label="线索数" width="100" />
            <el-table-column prop="deal" label="成交数" width="100" />
            <el-table-column label="转化率" width="160">
              <template #default="{ row }">
                <el-progress :percentage="row.rate" :stroke-width="14" :color="row.rate>=30?'#67c23a':(row.rate>=10?'#e6a23c':'#909399')" />
              </template>
            </el-table-column>
            <el-table-column label="签单金额(元)" width="140">
              <template #default="{ row }">{{ num(row.deal_amount) }}</template>
            </el-table-column>
            <el-table-column label="获客成本(元)" width="140">
              <template #default="{ row }">{{ num(row.cost) }}</template>
            </el-table-column>
            <el-table-column label="投产比(签单/成本)" width="140">
              <template #default="{ row }">
                <span :class="row.cost>0 ? 'amt' : 'muted'">{{ row.cost>0 ? (row.deal_amount/row.cost).toFixed(2) : '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never" style="margin-top:14px">
          <template #header><span>按「平台 + 账号」明细</span></template>
          <el-table :data="accountRows" border stripe size="default" max-height="460">
            <el-table-column prop="channel" label="平台" min-width="110" />
            <el-table-column prop="account" label="账号编号" min-width="140" />
            <el-table-column prop="total" label="线索数" width="90" />
            <el-table-column prop="deal" label="成交数" width="90" />
            <el-table-column label="转化率" width="100">
              <template #default="{ row }">{{ row.rate }}%</template>
            </el-table-column>
            <el-table-column label="签单金额(元)" width="130">
              <template #default="{ row }">{{ num(row.deal_amount) }}</template>
            </el-table-column>
            <el-table-column label="获客成本(元)" width="130">
              <template #default="{ row }">{{ num(row.cost) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 录入线索 -->
    <el-dialog v-model="createVisible" title="录入线索（多平台）" width="680px">
      <el-form :model="form" label-width="110px">
        <el-alert type="info" :closable="false" show-icon title="归属运营人自动取当前登录人" style="margin-bottom:12px" />
        <el-form-item label="来源平台" required>
          <el-select v-model="form.channel" placeholder="选择投放平台" style="width:100%">
            <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源账号编号" required>
          <el-input v-model="form.source_account_no" placeholder="如 DY-ACC-001，同一平台多账号独立统计" />
        </el-form-item>
        <el-form-item label="客户姓名" required>
          <el-input v-model="form.name" placeholder="客户姓名" />
        </el-form-item>
        <el-form-item label="联系方式" required>
          <el-select v-model="form.contact_type" style="width:110px">
            <el-option label="电话" value="PHONE" />
            <el-option label="微信" value="WECHAT" />
          </el-select>
          <el-input v-model="form.phone" placeholder="电话" style="width:150px;margin-left:8px" />
          <el-input v-model="form.wechat" placeholder="微信" style="width:150px;margin-left:8px" />
        </el-form-item>
        <el-form-item label="公司名称"><el-input v-model="form.company" /></el-form-item>
        <el-form-item label="意向业务"><el-input v-model="form.intention" placeholder="如：注册公司 / 代理记账 / 注销" /></el-form-item>
        <el-form-item label="客户需求"><el-input v-model="form.customer_need" type="textarea" :rows="2" placeholder="客户的具体需求描述" /></el-form-item>
        <el-form-item label="对接人"><el-input v-model="form.contact_person" placeholder="客户对接人姓名" /></el-form-item>
        <el-form-item label="获客成本(元)"><el-input-number v-model="form.acquisition_cost" :min="0" :precision="2" style="width:200px" /></el-form-item>
        <el-form-item label="签单金额(元)"><el-input-number v-model="form.deal_amount" :min="0" :precision="2" style="width:200px" /></el-form-item>
        <el-form-item label="指定成交师">
          <el-select v-model="form.closer" placeholder="不指定则系统按负载自动流转" clearable style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交并流转</el-button>
      </template>
    </el-dialog>

    <!-- 跟进记录 -->
    <el-dialog v-model="followVisible" title="线索跟进（第一次 / 二次 / 三次）" width="720px">
      <template v-if="current">
        <el-descriptions :column="2" size="small" border style="margin-bottom:10px">
          <el-descriptions-item label="客户">{{ current.lead_name }}</el-descriptions-item>
          <el-descriptions-item label="平台">{{ current.channel_name }}</el-descriptions-item>
          <el-descriptions-item label="对接人">{{ current.contact_person || '-' }}</el-descriptions-item>
          <el-descriptions-item label="需求">{{ current.customer_need || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">已有跟进</el-divider>
        <el-timeline>
          <el-timeline-item v-for="f in followList" :key="f.id" :timestamp="fmt(f.created_at)" placement="top">
            <strong>{{ f.round_label }} · {{ f.way_label }}</strong>
            <el-tag v-if="f.deal_happened" type="success" size="small" style="margin-left:6px">本次成交</el-tag>
            <div class="muted">{{ f.content }}</div>
            <div v-if="f.deal_amount" class="muted">签单金额：{{ num(f.deal_amount) }} 元</div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-if="!followList.length" description="暂无跟进记录" />

        <el-divider content-position="left">新增跟进</el-divider>
        <el-form :inline="true" label-width="80px">
          <el-form-item label="跟进轮次">
            <el-select v-model="fup.round_no" style="width:130px">
              <el-option label="第一次跟进" :value="1" />
              <el-option label="第二次跟进" :value="2" />
              <el-option label="第三次跟进" :value="3" />
            </el-select>
          </el-form-item>
          <el-form-item label="跟进方式">
            <el-select v-model="fup.way" style="width:120px">
              <el-option label="电话" value="PHONE" />
              <el-option label="微信" value="WECHAT" />
              <el-option label="上门" value="VISIT" />
              <el-option label="会议" value="MEETING" />
              <el-option label="其他" value="OTHER" />
            </el-select>
          </el-form-item>
          <el-form-item label="是否成交">
            <el-switch v-model="fup.deal_happened" />
          </el-form-item>
          <el-form-item v-if="fup.deal_happened" label="签单金额">
            <el-input-number v-model="fup.deal_amount" :min="0" :precision="2" style="width:160px" />
          </el-form-item>
        </el-form>
        <el-form label-width="80px">
          <el-form-item label="跟进内容">
            <el-input v-model="fup.content" type="textarea" :rows="3" placeholder="本次跟进具体内容" />
          </el-form-item>
        </el-form>
      </template>
      <template #footer>
        <el-button @click="followVisible = false">关闭</el-button>
        <el-button type="primary" :loading="fupLoading" @click="submitFollow">保存跟进</el-button>
      </template>
    </el-dialog>

    <!-- 穿透查看 -->
    <el-drawer v-model="penVisible" :title="'穿透查看 · ' + penName" size="62%">
      <template v-if="penData">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="人员">{{ penData.summary.user_name }}</el-descriptions-item>
          <el-descriptions-item label="负责线索总数">{{ penData.summary.total }}</el-descriptions-item>
          <el-descriptions-item label="成交数">{{ penData.summary.deal }}</el-descriptions-item>
          <el-descriptions-item label="签单总额(元)">{{ num(penData.summary.deal_amount) }}</el-descriptions-item>
          <el-descriptions-item label="获客成本(元)">{{ num(penData.summary.cost) }}</el-descriptions-item>
          <el-descriptions-item label="整体转化率">{{ penRate }}%</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">按平台 + 账号转化</el-divider>
        <el-table :data="penData.summary.by_account" border size="small" max-height="300">
          <el-table-column prop="channel" label="平台" />
          <el-table-column prop="account" label="账号" />
          <el-table-column prop="total" label="线索" width="70" />
          <el-table-column prop="deal" label="成交" width="70" />
          <el-table-column label="转化率" width="90">
            <template #default="{ row }">{{ row.rate }}%</template>
          </el-table-column>
          <el-table-column label="签单(元)" width="120">
            <template #default="{ row }">{{ num(row.deal_amount) }}</template>
          </el-table-column>
        </el-table>

        <el-divider content-position="left">全部线索明细</el-divider>
        <el-table :data="penData.rows" border size="small" max-height="360">
          <el-table-column prop="lead_name" label="客户" width="100" />
          <el-table-column prop="channel_name" label="平台" width="90" />
          <el-table-column prop="source_account_no" label="账号" width="100" />
          <el-table-column prop="contact_person" label="对接人" width="80" />
          <el-table-column label="签单(元)" width="110">
            <template #default="{ row }">{{ num(row.deal_amount) }}</template>
          </el-table-column>
          <el-table-column label="转化" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.is_deal" type="success" size="small">已成交</el-tag>
              <el-tag v-else type="info" size="small">未成交</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </template>
      <el-empty v-else-if="!penLoading" description="无数据" />
      <div v-else v-loading="true" style="height:200px" />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { growthApi } from '@/api/growth'
import { orgApi } from '@/api/index'
import { useUserStore } from '@/store/user'

const store = useUserStore()
const tab = ref('list')

const list = ref([])
const channels = ref([])
const users = ref([])
const loading = ref(false)
const filters = reactive({ channel: '', account: '' })

const createVisible = ref(false)
const submitting = ref(false)
const form = reactive({
  channel: '', source_account_no: '', name: '', phone: '', wechat: '',
  company: '', intention: '', customer_need: '', contact_person: '',
  acquisition_cost: 0, deal_amount: 0, closer: null, contact_type: 'PHONE'
})

const followVisible = ref(false)
const followList = ref([])
const fupLoading = ref(false)
const current = ref(null)
const fup = reactive({ round_no: 1, way: 'PHONE', content: '', deal_happened: false, deal_amount: 0 })

const penVisible = ref(false)
const penData = ref(null)
const penName = ref('')
const penLoading = ref(false)

const canCreate = computed(() => store.isBoss || store.isManager || store.isHR || store.isSuper)

function num(v) {
  const n = Number(v || 0)
  return n ? n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 }) : '0'
}
function fmt(t) { return t ? String(t).slice(0, 19).replace('T', ' ') : '' }

async function loadChannels() {
  try { const r = await growthApi.channels(); channels.value = Array.isArray(r) ? r : (r.results || []) } catch (e) {}
}
async function loadUsers() {
  try { const r = await orgApi.users({ page_size: 200 }); users.value = Array.isArray(r) ? r : (r.results || []) } catch (e) {}
}

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.channel) params.channel = filters.channel
    if (filters.account) params.source_account_no = filters.account
    const res = await growthApi.leads(params)
    list.value = Array.isArray(res) ? res : (res.results || [])
  } finally { loading.value = false }
}
function resetFilter() { filters.channel = ''; filters.account = ''; loadData() }

function openCreate() {
  Object.assign(form, {
    channel: channels.value[0]?.id || '', source_account_no: '', name: '', phone: '',
    wechat: '', company: '', intention: '', customer_need: '', contact_person: '',
    acquisition_cost: 0, deal_amount: 0, closer: null, contact_type: 'PHONE'
  })
  createVisible.value = true
}
async function submitCreate() {
  if (!form.channel) return ElMessage.warning('请选择来源平台')
  if (!form.source_account_no) return ElMessage.warning('请填写来源账号编号')
  if (!form.name) return ElMessage.warning('请填写客户姓名')
  if (form.contact_type === 'PHONE' && !form.phone) return ElMessage.warning('电话方式请填写电话')
  if (!form.phone && !form.wechat) return ElMessage.warning('电话与微信至少填一项')
  submitting.value = true
  try {
    await growthApi.createLead({ ...form, acquisition_cost: form.acquisition_cost || 0, deal_amount: form.deal_amount || 0 })
    ElMessage.success('录入成功，已自动流转')
    createVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

async function openFollow(row) {
  current.value = row
  followVisible.value = true
  followList.value = []
  try {
    const r = await growthApi.followups({ lead_ext: row.id })
    followList.value = Array.isArray(r) ? r : (r.results || [])
  } catch (e) {}
}
async function submitFollow() {
  if (!fup.content) return ElMessage.warning('请填写跟进内容')
  fupLoading.value = true
  try {
    await growthApi.createFollowup({
      lead_ext: current.value.id, round_no: fup.round_no, way: fup.way,
      content: fup.content, deal_happened: fup.deal_happened,
      deal_amount: fup.deal_happened ? (fup.deal_amount || 0) : 0
    })
    ElMessage.success('已保存跟进')
    const r = await growthApi.followups({ lead_ext: current.value.id })
    followList.value = Array.isArray(r) ? r : (r.results || [])
    Object.assign(fup, { content: '', deal_happened: false, deal_amount: 0 })
    loadData()
  } finally { fupLoading.value = false }
}

async function penetrate(uid, name) {
  if (!uid) return
  penName.value = name || ''
  penVisible.value = true
  penData.value = null
  penLoading.value = true
  try {
    const r = await growthApi.byPerson(uid)
    penData.value = r || null
  } catch (e) {} finally { penLoading.value = false }
}

// ---------- 数据看板聚合 ----------
const boardTotal = computed(() => list.value.length)
const boardDeal = computed(() => list.value.filter(r => r.is_deal).length)
const boardRate = computed(() => boardTotal.value ? Math.round(boardDeal.value / boardTotal.value * 100) : 0)
const boardAmount = computed(() => list.value.reduce((s, r) => s + Number(r.deal_amount || 0), 0))
const boardLoading = ref(false)

const boardRows = computed(() => {
  const m = {}
  for (const r of list.value) {
    const k = r.channel_name || '未知'
    if (!m[k]) m[k] = { channel: k, total: 0, deal: 0, deal_amount: 0, cost: 0 }
    m[k].total += 1
    if (r.is_deal) m[k].deal += 1
    m[k].deal_amount += Number(r.deal_amount || 0)
    m[k].cost += Number(r.acquisition_cost || 0)
  }
  return Object.values(m).map(x => ({ ...x, rate: x.total ? Math.round(x.deal / x.total * 100) : 0 }))
})
const accountRows = computed(() => {
  const m = {}
  for (const r of list.value) {
    const k = (r.channel_name || '未知') + '::' + (r.source_account_no || '-')
    if (!m[k]) m[k] = { channel: r.channel_name || '未知', account: r.source_account_no || '-', total: 0, deal: 0, deal_amount: 0, cost: 0 }
    m[k].total += 1
    if (r.is_deal) m[k].deal += 1
    m[k].deal_amount += Number(r.deal_amount || 0)
    m[k].cost += Number(r.acquisition_cost || 0)
  }
  return Object.values(m).map(x => ({ ...x, rate: x.total ? Math.round(x.deal / x.total * 100) : 0 }))
})
const penRate = computed(() => {
  const s = penData.value?.summary
  return s && s.total ? Math.round(s.deal / s.total * 100) : 0
})

onMounted(() => { loadChannels(); loadUsers(); loadData() })
</script>

<style scoped>
.lead-entry { padding: 4px; }
.stat-row { margin-bottom: 14px; }
.mini-card { text-align: center; }
.mini-label { font-size: 13px; color: #909399; }
.mini-value { font-size: 24px; font-weight: 600; margin-top: 6px; color: #303133; }
.mini-value.ok { color: #67c23a; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { margin-bottom: 8px; }
.amt { color: #67c23a; font-weight: 600; }
.muted { color: #909399; }
</style>
