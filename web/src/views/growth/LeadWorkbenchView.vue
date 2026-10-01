<template>
  <div class="growth-page">
    <!-- 顶部指标条 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">我的录入</div>
          <div class="mini-value">{{ total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">待承接（公海）</div>
          <div class="mini-value warn">{{ poolWaiting }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">已成交（0阶段）</div>
          <div class="mini-value ok">{{ dealCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">我的角色</div>
          <div class="mini-value small">{{ roleLabel }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作区 -->
    <el-card shadow="never" class="main-card">
      <template #header>
        <div class="card-header">
          <span>线索工作台 · 多平台录入与全链路流转</span>
          <div>
            <el-button v-if="canCreateLead" type="primary" @click="openCreate">+ 录入线索</el-button>
            <el-button @click="goPool">公海 →</el-button>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选 -->
      <el-form :inline="true" size="default" class="filter-bar">
        <el-form-item label="平台">
          <el-select v-model="filters.channel" placeholder="全部平台" clearable style="width:140px">
            <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="3570阶段">
          <el-select v-model="filters.stage" placeholder="全部" clearable style="width:120px">
            <el-option label="3阶段" value="S3" />
            <el-option label="5阶段" value="S5" />
            <el-option label="7阶段" value="S7" />
            <el-option label="0成交" value="S0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" plain @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table :data="list" v-loading="loading" border stripe size="default">
        <el-table-column prop="lead_name" label="客户" min-width="120" />
        <el-table-column prop="lead_phone" label="电话" width="130" />
        <el-table-column label="来源平台" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ row.channel_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_account_no" label="来源账号" width="130" />
        <el-table-column prop="ops_owner_name" label="归属运营" width="110" />
        <el-table-column prop="closer_name" label="承接人" width="110">
          <template #default="{ row }">
            <span v-if="row.closer_name">{{ row.closer_name }}</span>
            <el-tag v-else-if="row.in_pool" type="warning" size="small">公海待领</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="3570阶段" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.stage_3570" :type="stageTagType(row.stage_3570)" size="small">
              {{ row.stage_label }}
            </el-tag>
            <span v-else class="muted">未标记</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canManage" link type="danger" @click="openAssign(row)">分配</el-button>
            <el-button link type="primary" @click="openStage(row)">标记阶段</el-button>
            <el-button link type="success" @click="doAccept(row)">承接</el-button>
            <el-button link type="warning" @click="doReturn(row)">退公海</el-button>
            <el-button link @click="openFlows(row)">流转</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 录入对话框 -->
    <el-dialog v-model="createVisible" title="录入线索（多平台）" width="620px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="来源平台" required>
          <el-select v-model="form.channel" placeholder="选择投放平台" style="width:100%">
            <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源账号编号" required>
          <el-input v-model="form.source_account_no" placeholder="如 DY-ACC-001，用于多账号区分" />
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
        <el-form-item label="公司名称">
          <el-input v-model="form.company" />
        </el-form-item>
        <el-form-item label="意向业务">
          <el-input v-model="form.intention" placeholder="如：注册公司 / 代理记账 / 注销" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-alert type="info" :closable="false" show-icon
                  title="提交后系统按成交师负载自动流转；若无可用成交师则自动进入公海" />
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交并流转</el-button>
      </template>
    </el-dialog>

    <!-- 3570 标记 -->
    <el-dialog v-model="stageVisible" title="标记 3570 阶段" width="420px">
      <el-form label-width="90px">
        <el-form-item label="客户">{{ current?.lead_name }}</el-form-item>
        <el-form-item label="阶段">
          <el-radio-group v-model="stageValue">
            <el-radio-button label="S3">3阶段</el-radio-button>
            <el-radio-button label="S5">5阶段</el-radio-button>
            <el-radio-button label="S7">7阶段</el-radio-button>
            <el-radio-button label="S0">0成交</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="stageRemark" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="stageVisible = false">取消</el-button>
        <el-button type="primary" @click="submitStage">确定</el-button>
      </template>
    </el-dialog>

    <!-- 流转记录 -->
    <el-dialog v-model="flowVisible" title="线索流转记录" width="560px">
      <el-timeline>
        <el-timeline-item v-for="f in flows" :key="f.id" :timestamp="fmt(f.created_at)" placement="top">
          <strong>{{ f.action_label }}</strong>
          <div class="muted">{{ f.from_user_name || '系统' }} → {{ f.to_user_name || '-' }} {{ f.remark ? '· ' + f.remark : '' }}</div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-if="!flows.length" description="暂无流转记录" />
    </el-dialog>

    <!-- 管理层分配 -->
    <el-dialog v-model="assignVisible" title="管理层分配线索" width="480px">
      <el-alert type="info" :closable="false" show-icon
                title="仅管理层可见：把线索指派给某运营（归属）或成交师（承接），分配后移出公海并留痕" />
      <el-form label-width="100px" style="margin-top:12px">
        <el-form-item label="客户">{{ current?.lead_name }}</el-form-item>
        <el-form-item label="归属运营">
          <el-select v-model="assignForm.owner_id" placeholder="不改动运营" clearable style="width:100%">
            <el-option v-for="u in opsUsers" :key="u.user" :label="u.user_name" :value="u.user" />
          </el-select>
        </el-form-item>
        <el-form-item label="承接人">
          <el-select v-model="assignForm.closer_id" placeholder="不改动承接人" clearable style="width:100%">
            <el-option v-for="u in closerUsers" :key="u.user" :label="u.user_name" :value="u.user" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="assignForm.remark" placeholder="选填，如：转交王经理跟进" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="assigning" @click="submitAssign">确认分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { growthApi } from '@/api/growth'
import { useUserStore } from '@/store/user'

const router = useRouter()
const store = useUserStore()

const list = ref([])
const channels = ref([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const poolWaiting = ref(0)
const roleLabel = ref('未配置')

const filters = reactive({ channel: '', stage: '' })

const createVisible = ref(false)
const stageVisible = ref(false)
const flowVisible = ref(false)
const current = ref(null)
const stageValue = ref('S3')
const stageRemark = ref('')
const flows = ref([])

// 管理层分配
const assignVisible = ref(false)
const assigning = ref(false)
const roleCanViewAll = ref(false)
const opsUsers = ref([])
const closerUsers = ref([])
const assignForm = reactive({ owner_id: null, closer_id: null, remark: '' })

const form = reactive({
  channel: '', source_account_no: '', name: '', phone: '', wechat: '',
  company: '', intention: '', remark: '', contact_type: 'PHONE'
})

const dealCount = computed(() => list.value.filter(r => r.stage_3570 === 'S0').length)
// 录入权限：超管 / 经理 / 老板 / HR 之一即可；演示访客不可写
const canCreateLead = computed(() => !store.isDemo && (store.isBoss || store.isManager || store.isHR || store.isSuper))
// 管理层（可看全量）才拥有「分配」权限，与后端 IsGrowthAdmin(can_view_all) 对齐
const canManage = computed(() => !store.isDemo && (roleCanViewAll.value || store.isBoss || store.isManager || store.isSuper))

function stageTagType(s) {
  return { S3: 'info', S5: 'primary', S7: 'warning', S0: 'success' }[s] || 'info'
}
function fmt(t) {
  return t ? String(t).slice(0, 19).replace('T', ' ') : ''
}

async function loadChannels() {
  try {
    const res = await growthApi.channels()
    channels.value = Array.isArray(res) ? res : (res.results || [])
  } catch (e) { /* 拦截器已提示 */ }
}

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.channel) params.channel = filters.channel
    if (filters.stage) params.stage = filters.stage
    const res = await growthApi.leads(params)
    list.value = Array.isArray(res) ? res : (res.results || [])
    total.value = Array.isArray(res) ? res.length : (res.count || list.value.length)
    const p = await growthApi.statsPool()
    poolWaiting.value = p.waiting || 0
  } finally {
    loading.value = false
  }
}

async function loadRole() {
  try {
    const r = await growthApi.myRole()
    if (!r) { roleLabel.value = '未配置'; return }
    roleCanViewAll.value = !!r.can_view_all
    roleLabel.value = r.has_role ? r.role_label : (r.can_view_all ? '超级总账号' : '未配置')
    if (canManage.value) loadGrowthRoles()
  } catch (e) { /* ignore */ }
}

async function loadGrowthRoles() {
  try {
    const res = await growthApi.growthRoles()
    const rows = Array.isArray(res) ? res : (res.results || [])
    opsUsers.value = rows.filter(r => r.role === 'OPS')
    closerUsers.value = rows.filter(r => r.role === 'CLOSER')
  } catch (e) { /* 非管理层会 403，忽略即可 */ }
}

function openCreate() {
  Object.assign(form, {
    channel: channels.value[0]?.id || '', source_account_no: '', name: '', phone: '',
    wechat: '', company: '', intention: '', remark: '', contact_type: 'PHONE'
  })
  createVisible.value = true
}

async function submitCreate() {
  if (!form.channel) return ElMessage.warning('请选择来源平台')
  if (!form.source_account_no) return ElMessage.warning('请填写来源账号编号')
  if (!form.name) return ElMessage.warning('请填写客户姓名')
  if (form.contact_type === 'PHONE' && !form.phone) return ElMessage.warning('联系方式为电话时必填电话')
  if (!form.phone && !form.wechat) return ElMessage.warning('电话与微信至少填一项')

  submitting.value = true
  try {
    await growthApi.createLead({ ...form })
    ElMessage.success('录入成功，已自动流转')
    createVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

async function doAccept(row) {
  await growthApi.acceptLead(row.id)
  ElMessage.success('已承接')
  loadData()
}

async function doReturn(row) {
  const { value } = await ElMessageBox.prompt('填写退回原因', '退回公海', {
    inputPlaceholder: '如：客户失联 / 无法跟进', inputValue: ''
  }).catch(() => ({ value: null }))
  if (value === null) return
  await growthApi.returnPool(row.id, { reason: value || '无法跟进' })
  ElMessage.success('已退回公海，可二次分配')
  loadData()
}

function openStage(row) {
  current.value = row
  stageValue.value = row.stage_3570 || 'S3'
  stageRemark.value = ''
  stageVisible.value = true
}

async function submitStage() {
  await growthApi.setStage(current.value.id, { stage: stageValue.value, remark: stageRemark.value })
  ElMessage.success('已标记')
  stageVisible.value = false
  loadData()
}

async function openFlows(row) {
  current.value = row
  flowVisible.value = true
  flows.value = await growthApi.leadFlows(row.id) || []
}

function openAssign(row) {
  current.value = row
  assignForm.owner_id = row.ops_owner || null
  assignForm.closer_id = row.closer || null
  assignForm.remark = ''
  assignVisible.value = true
}

async function submitAssign() {
  if (!assignForm.owner_id && !assignForm.closer_id) {
    return ElMessage.warning('请至少选择「归属运营」或「承接人」之一')
  }
  assigning.value = true
  try {
    await growthApi.assignLead(current.value.id, { ...assignForm })
    ElMessage.success('已分配，线索已移出公海并留痕')
    assignVisible.value = false
    loadData()
  } finally {
    assigning.value = false
  }
}

onMounted(() => {
  loadChannels()
  loadRole()
  loadData()
})
</script>

<style scoped>
.growth-page { padding: 4px; }
.stat-row { margin-bottom: 14px; }
.mini-card { text-align: center; }
.mini-label { font-size: 13px; color: #909399; }
.mini-value { font-size: 24px; font-weight: 600; margin-top: 6px; color: #303133; }
.mini-value.warn { color: #e6a23c; }
.mini-value.ok { color: #67c23a; }
.mini-value.small { font-size: 16px; }
.main-card { margin-top: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { margin-bottom: 8px; }
.muted { color: #909399; }
</style>
