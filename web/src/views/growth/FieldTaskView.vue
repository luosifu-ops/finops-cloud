<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">外勤任务池</h2>
        <p class="page-sub">各部门接单后单据统一流转到此池；外勤主管可派单，外勤本人可将手上单据再分配给其他外勤人员</p>
      </div>
      <div class="page-actions">
        <el-button type="success" plain @click="openTransfer">跨部门订单转接</el-button>
        <el-button v-if="canManage" type="success" plain @click="openFromDeal">成交单 → 生成外勤任务</el-button>
        <el-button type="primary" @click="openCreate">+ 新建外勤任务</el-button>
        <el-button @click="loadData">刷新</el-button>
      </div>
    </div>

    <div class="card ft-card">
      <el-form :inline="true" class="filter-bar">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width:140px">
            <el-option v-for="s in statusOps" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" plain @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="list" v-loading="loading" size="default" max-height="600">
        <el-table-column label="外勤单号" width="182">
          <template #default="{ row }"><span class="order-no">{{ row.task_no || formatOrderNo(row) }}</span></template>
        </el-table-column>
        <el-table-column prop="customer_name" label="客户名称" min-width="130" show-overflow-tooltip />
        <el-table-column label="客户类型" width="88">
          <template #default="{ row }"><el-tag size="small">{{ row.customer_type_label }}</el-tag></template>
        </el-table-column>
        <el-table-column label="业务类型" width="126">
          <template #default="{ row }">
            <el-tag type="warning" size="small">{{ row.business_type_label }}</el-tag>
            <div v-if="row.task_type && row.task_type !== row.business_type_label" class="sub-type">{{ row.task_type }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="from_order_no" label="来源成交单号" width="126" show-overflow-tooltip />
        <el-table-column label="状态" width="88">
          <template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ row.status_label }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="assignee_name" label="外勤人员" width="92" />
        <el-table-column prop="creator_name" label="下单人" width="88" />
        <el-table-column label="当前进度" width="140" show-overflow-tooltip>
          <template #default="{ row }"><span class="latest-node">{{ row.latest_node || '-' }}</span></template>
        </el-table-column>
        <el-table-column label="节点" width="92" align="center">
          <template #default="{ row }">
            <el-tooltip placement="top" effect="dark" :disabled="!(row.nodes || []).length">
              <template #content>
                <div class="node-tip">
                  <span v-for="n in (row.nodes || [])" :key="n.id" class="node-pill" :class="n.status.toLowerCase()">
                    {{ n.node_label }}
                  </span>
                </div>
              </template>
              <span class="node-brief">
                <span class="node-dot" :class="nodeState(row)"></span>
                {{ nodeDone(row) }}/{{ (row.nodes || []).length || 0 }}
              </span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openNodes(row)">节点进度</el-button>
            <el-button v-if="canEdit(row)" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="canEdit(row)" link type="danger" @click="removeTask(row)">删除</el-button>
            <el-button v-if="canAssign(row)" link type="warning" @click="openAssign(row)">
              {{ canManage ? '派单' : '再分配' }}
            </el-button>
            <el-button v-if="row.status === 'PENDING'" link type="success" @click="accept(row)">接单</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建外勤任务 -->
    <el-dialog v-model="createVisible" title="新建外勤任务" width="620px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="派单号（自动生成）">
          <el-input :model-value="''" disabled placeholder="保存后系统自动生成（WD 开头）" />
        </el-form-item>
        <el-form-item label="关联单号（选填）">
          <el-input v-model="form.order_no" placeholder="外部系统关联单号，如 F-2026-0001" />
        </el-form-item>
        <el-form-item label="客户名称" required><el-input v-model="form.customer_name" /></el-form-item>
        <el-form-item label="客户类型">
          <el-select v-model="form.customer_type" style="width:100%">
            <el-option label="企业" value="ENTERPRISE" />
            <el-option label="个体工商户" value="INDIVIDUAL" />
            <el-option label="个人" value="PERSONAL" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务类型">
          <el-select v-model="form.business_type" style="width:100%" @change="onBusinessTypeChange(form, 'task_type')">
            <el-option v-for="b in businessTypeOps" :key="b.value" :label="b.label" :value="b.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型"><el-input v-model="form.task_type" placeholder="如：工商注册 / 异常处理 / 注销" /></el-form-item>
        <el-form-item label="办理地点"><el-input v-model="form.address" /></el-form-item>
        <el-form-item label="要求完成时间"><el-date-picker v-model="form.due_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="可选" /></el-form-item>
        <el-alert type="info" :closable="false" show-icon title="提交后按业务类型自动生成进度节点模板" />
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">创建任务</el-button>
      </template>
    </el-dialog>

    <!-- 成交单自动流转 -->
    <el-dialog v-model="dealVisible" title="成交订单 → 自动生成外勤任务" width="620px">
      <el-form :model="dealForm" label-width="110px">
        <el-form-item label="客户名称" required><el-input v-model="dealForm.customer_name" /></el-form-item>
        <el-form-item label="来源成交单号"><el-input v-model="dealForm.from_order_no" placeholder="电销/运营成交订单号" /></el-form-item>
        <el-form-item label="客户类型">
          <el-select v-model="dealForm.customer_type" style="width:100%">
            <el-option label="企业" value="ENTERPRISE" />
            <el-option label="个体工商户" value="INDIVIDUAL" />
            <el-option label="个人" value="PERSONAL" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务类型">
          <el-select v-model="dealForm.business_type" style="width:100%" @change="onBusinessTypeChange(dealForm, 'task_type')">
            <el-option v-for="b in businessTypeOps" :key="b.value" :label="b.label" :value="b.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型"><el-input v-model="dealForm.task_type" placeholder="如：工商注册" /></el-form-item>
        <el-alert type="success" :closable="false" show-icon title="生成后任务进入外勤任务池，由外勤主管派单" />
      </el-form>
      <template #footer>
        <el-button @click="dealVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitDeal">生成并流转</el-button>
      </template>
    </el-dialog>

    <!-- 跨部门订单转接（2026-10-30 增量：其他部门将订单流转转接至外勤任务池） -->
    <el-dialog v-model="transferVisible" title="跨部门订单转接 → 外勤任务池" width="620px">
      <el-form :model="transferForm" label-width="110px">
        <el-form-item label="客户名称" required><el-input v-model="transferForm.customer_name" placeholder="客户 / 企业名称" /></el-form-item>
        <el-form-item label="关联单号"><el-input v-model="transferForm.order_no" placeholder="本部门订单 / 合同单号，如 HT-2026-0001" /></el-form-item>
        <el-form-item label="客户类型">
          <el-select v-model="transferForm.customer_type" style="width:100%">
            <el-option label="企业" value="ENTERPRISE" />
            <el-option label="个体工商户" value="INDIVIDUAL" />
            <el-option label="个人" value="PERSONAL" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务类型">
          <el-select v-model="transferForm.business_type" style="width:100%" @change="onBusinessTypeChange(transferForm, 'task_type')">
            <el-option v-for="b in businessTypeOps" :key="b.value" :label="b.label" :value="b.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型"><el-input v-model="transferForm.task_type" placeholder="如：工商注册 / 异常处理 / 注销" /></el-form-item>
        <el-form-item label="办理地点"><el-input v-model="transferForm.address" /></el-form-item>
        <el-form-item label="要求完成时间"><el-date-picker v-model="transferForm.due_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="可选" /></el-form-item>
        <el-form-item label="转接说明"><el-input v-model="transferForm.remark" type="textarea" :rows="2" placeholder="订单背景、需要外勤办理的事项（选填）" /></el-form-item>
        <el-alert type="success" :closable="false" show-icon title="转接后订单进入外勤任务池（待接收），由外勤主管派单办理，并自动通知外勤人员" />
      </el-form>
      <template #footer>
        <el-button @click="transferVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitTransfer">确认转接</el-button>
      </template>
    </el-dialog>

    <!-- 编辑外勤任务（2026-10-30 增量：录入错误后可修改） -->
    <el-dialog v-model="editVisible" title="编辑外勤任务" width="620px">
      <el-form :model="editForm" label-width="110px">
        <el-form-item label="任务标题" required><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="客户名称" required><el-input v-model="editForm.customer_name" /></el-form-item>
        <el-form-item label="客户类型">
          <el-select v-model="editForm.customer_type" style="width:100%">
            <el-option label="企业" value="ENTERPRISE" />
            <el-option label="个体工商户" value="INDIVIDUAL" />
            <el-option label="个人" value="PERSONAL" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务类型">
          <el-select v-model="editForm.business_type" style="width:100%" @change="onBusinessTypeChange(editForm, 'task_type')">
            <el-option v-for="b in businessTypeOps" :key="b.value" :label="b.label" :value="b.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型"><el-input v-model="editForm.task_type" /></el-form-item>
        <el-form-item label="办理地点"><el-input v-model="editForm.address" /></el-form-item>
        <el-form-item label="要求完成时间"><el-date-picker v-model="editForm.due_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="可选" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="editForm.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitEdit">保存修改</el-button>
      </template>
    </el-dialog>

    <!-- 节点进度管理 -->
    <el-dialog v-model="nodeVisible" title="外勤精细化进度节点" width="760px">
      <template v-if="current">
        <el-descriptions :column="2" border size="small" style="margin-bottom:10px">
          <el-descriptions-item label="外勤单号（派单号）">{{ current.task_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ current.customer_name }}</el-descriptions-item>
          <el-descriptions-item label="业务类型">{{ current.business_type_label }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">{{ current.task_type }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(current.status)" size="small">{{ current.status_label }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="外勤人员">{{ current.assignee_name || '未派单' }}</el-descriptions-item>
        </el-descriptions>

        <div class="add-node-bar">
          <span>点选添加节点：</span>
          <el-select v-model="nodeToAdd" placeholder="选择预设节点" size="small" style="width:180px">
            <el-option v-for="c in nodeChoices" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
          <el-button size="small" type="primary" :loading="addingNode" @click="addNode">添加</el-button>
        </div>

        <el-timeline>
          <el-timeline-item v-for="n in nodeList" :key="n.id" :timestamp="(n.done_at ? '完成：' + n.done_at : '待处理')" placement="top">
            <div class="node-row">
              <div>
                <strong>{{ n.node_label }}</strong>
                <el-tag size="small" :type="statusType2(n.status)" style="margin-left:6px">{{ n.status_label }}</el-tag>
              </div>
              <div class="node-ctrl">
                <el-select v-model="n.status" size="small" style="width:120px" @change="saveNode(n)">
                  <el-option label="待处理" value="PENDING" />
                  <el-option label="进行中" value="IN_PROGRESS" />
                  <el-option label="已完成" value="DONE" />
                </el-select>
                <el-date-picker v-model="n.done_at" size="small" type="date" value-format="YYYY-MM-DD"
                  placeholder="完成日期" style="width:150px;margin-left:8px" @change="saveNode(n)" />
              </div>
              <div v-if="n.remark" class="muted">{{ n.remark }}</div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-dialog>

    <!-- 派单 -->
    <el-dialog v-model="assignVisible" :title="canManage ? '外勤派单 / 再分配' : '再分配给其他外勤'" width="460px">
      <el-form label-width="90px">
        <el-form-item label="任务">{{ current?.order_no || current?.customer_name }}</el-form-item>
        <el-form-item label="外勤人员">
          <PersonSelect v-model="assignUid" :include-free-text="true"
            placeholder="选择外勤人员，或输入姓名新增" />
          <div style="font-size:12px;color:#909399;margin-top:4px;line-height:1.5">列表里没有该外勤？直接输入姓名即可一键新增人员</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitAssign">确认派单</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { growthApi } from '@/api/growth'
import { orgApi } from '@/api/index'
import { useUserStore } from '@/store/user'
import PersonSelect from '@/components/PersonSelect.vue'

const store = useUserStore()
const statusOps = [
  { label: '待接收', value: 'PENDING' }, { label: '已接收', value: 'ACCEPTED' },
  { label: '办理中', value: 'IN_PROGRESS' }, { label: '已完成', value: 'DONE' },
  { label: '已关闭', value: 'CLOSED' }
]
const businessTypeOps = [
  { label: '工商注册', value: 'REGISTER' },
  { label: '公司注销', value: 'CANCEL' },
  { label: '工商变更', value: 'CHANGE' },
  { label: '地址异常', value: 'ADDRESS_ABNORMAL' },
  { label: '税务报到', value: 'TAX_REGISTER' },
  { label: '异常处理', value: 'ABNORMAL' },
  { label: '通用', value: 'GENERAL' },
]
const businessTypeHint = {
  REGISTER: '工商注册',
  CANCEL: '公司注销',
  CHANGE: '工商变更',
  ADDRESS_ABNORMAL: '地址异常',
  TAX_REGISTER: '税务报到',
  ABNORMAL: '异常处理',
  GENERAL: '通用业务',
}
const canManage = computed(() => store.isBoss || store.isManager || store.isHR || store.isSuper)
// 派单 / 再分配：主管可派任意单；外勤本人可把手上这单再分配给其他外勤
const myId = computed(() => store.userInfo?.id || null)
function canAssign(row) {
  if (canManage.value) return true
  return !!myId.value && row.assignee === myId.value
}

const list = ref([])
const loading = ref(false)
const filters = reactive({ status: null })
const users = ref([])

const createVisible = ref(false)
const dealVisible = ref(false)
const transferVisible = ref(false)
const editVisible = ref(false)
const nodeVisible = ref(false)
const assignVisible = ref(false)
const submitting = ref(false)
const addingNode = ref(false)
const current = ref(null)
const nodeList = ref([])
const nodeChoices = ref([])
const nodeToAdd = ref('')
const assignUid = ref(null)

const form = reactive({ order_no: '', customer_name: '', customer_type: 'ENTERPRISE', business_type: 'REGISTER', task_type: '', address: '', due_at: '' })
const dealForm = reactive({ customer_name: '', from_order_no: '', customer_type: 'ENTERPRISE', business_type: 'REGISTER', task_type: '工商注册' })
const transferForm = reactive({ customer_name: '', order_no: '', customer_type: 'ENTERPRISE', business_type: 'REGISTER', task_type: '工商注册', address: '', due_at: '', remark: '' })
const editForm = reactive({ id: null, title: '', customer_name: '', customer_type: 'ENTERPRISE', business_type: 'REGISTER', task_type: '', address: '', due_at: '', remark: '' })

// 编辑权限：管理层可改任意单；其他人可改自己下单/转接的单
function canEdit(row) {
  if (canManage.value) return true
  const myIdV = myId.value
  return !!myIdV && (row.creator === myIdV || row.created_by === myIdV)
}

function statusType(s) {
  return { PENDING: 'info', ACCEPTED: 'primary', IN_PROGRESS: 'warning', DONE: 'success', CLOSED: 'info' }[s] || 'info'
}
function statusType2(s) {
  return { PENDING: 'info', IN_PROGRESS: 'warning', DONE: 'success' }[s] || 'info'
}
// 节点完成度（列表压缩展示，明细见 hover 提示 / 「节点进度」弹窗）
function nodeDone(row) {
  return (row.nodes || []).filter(n => n.status === 'DONE').length
}
function nodeState(row) {
  const nodes = row.nodes || []
  if (!nodes.length) return 'none'
  if (nodeDone(row) === nodes.length) return 'done'
  return nodes.some(n => n.status === 'IN_PROGRESS') ? 'doing' : 'pending'
}
// 外勤单号规范展示：有值直显，为空按 id 规范化为 WD-00042（不改动后端字段）
function formatOrderNo(row) {
  if (row && row.order_no && String(row.order_no).trim()) return row.order_no
  const id = (row && row.id) || 0
  return 'WD-' + String(id).padStart(5, '0')
}

async function loadUsers() {
  try { const r = await orgApi.users({ page_size: 200 }); users.value = Array.isArray(r) ? r : (r.results || []) } catch (e) {}
}
async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    const res = await growthApi.fieldTasks(params)
    list.value = Array.isArray(res) ? res : (res.results || [])
  } finally { loading.value = false }
}

function openCreate() {
  Object.assign(form, { order_no: '', customer_name: '', customer_type: 'ENTERPRISE', business_type: 'REGISTER', task_type: '', address: '', due_at: '' })
  createVisible.value = true
}
function onBusinessTypeChange(target, key) {
  target[key] = businessTypeHint[target.business_type] || target[key]
}
async function submitCreate() {
  if (!form.customer_name) return ElMessage.warning('请填写客户名称')
  submitting.value = true
  try {
    await growthApi.createFieldTask({ ...form })
    ElMessage.success('已创建，自动生成 5 个进度节点')
    createVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

function openFromDeal() {
  Object.assign(dealForm, { customer_name: '', from_order_no: '', customer_type: 'ENTERPRISE', business_type: 'REGISTER', task_type: '工商注册' })
  dealVisible.value = true
}
async function submitDeal() {
  if (!dealForm.customer_name && !dealForm.from_order_no) return ElMessage.warning('请至少填写客户名称或成交单号')
  submitting.value = true
  try {
    await growthApi.fromDeal({ ...dealForm })
    ElMessage.success('已生成外勤任务，进入任务池')
    dealVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

// —— 跨部门订单转接 ——
function openTransfer() {
  Object.assign(transferForm, { customer_name: '', order_no: '', customer_type: 'ENTERPRISE', business_type: 'REGISTER', task_type: '工商注册', address: '', due_at: '', remark: '' })
  transferVisible.value = true
}
async function submitTransfer() {
  if (!transferForm.customer_name && !transferForm.order_no) return ElMessage.warning('请至少填写客户名称或关联单号')
  submitting.value = true
  try {
    await growthApi.transferInFieldTask({ ...transferForm })
    ElMessage.success('转接成功，订单已进入外勤任务池并通知外勤人员')
    transferVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

// —— 编辑外勤任务 ——
function openEdit(row) {
  Object.assign(editForm, {
    id: row.id,
    title: row.title || '',
    customer_name: row.customer_name || '',
    customer_type: row.customer_type || 'ENTERPRISE',
    business_type: row.business_type || 'GENERAL',
    task_type: row.task_type || '',
    address: row.address || '',
    due_at: row.due_at || '',
    remark: row.remark || '',
  })
  editVisible.value = true
}
async function submitEdit() {
  if (!editForm.title) return ElMessage.warning('任务标题不能为空')
  if (!editForm.customer_name) return ElMessage.warning('请填写客户名称')
  submitting.value = true
  try {
    const { id, ...payload } = editForm
    await growthApi.updateFieldTask(id, payload)
    ElMessage.success('已保存修改')
    editVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

// —— 删除外勤任务（2026-10-30 增量：软删除，仅本人/管理层可删）——
async function removeTask(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除外勤任务「${row.title || row.customer_name || row.id}」吗？删除后任务及进度记录将不再显示，不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
  } catch { return }
  try {
    await growthApi.deleteFieldTask(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch { /* 拦截器已提示 */ }
}

async function openNodes(row) {
  current.value = row
  nodeVisible.value = true
  nodeToAdd.value = ''
  try {
    const r = await growthApi.fieldNodes({ task: row.id })
    nodeList.value = Array.isArray(r) ? r : (r.results || [])
  } catch (e) { nodeList.value = [] }
  loadNodeChoices()
}
async function loadNodeChoices() {
  try {
    const r = await growthApi.fieldTaskNodeChoices()
    nodeChoices.value = Array.isArray(r) ? r : (r.data || [])
  } catch (e) { nodeChoices.value = [] }
}
async function saveNode(n) {
  try { await growthApi.updateFieldNode(n.id, { status: n.status, done_at: n.done_at || null }) } catch (e) {}
}
async function addNode() {
  if (!nodeToAdd.value) return ElMessage.warning('请先选择节点')
  if (!current.value) return
  addingNode.value = true
  try {
    const r = await growthApi.addFieldNode(current.value.id, { node: nodeToAdd.value })
    nodeList.value.push(r)
    nodeToAdd.value = ''
    ElMessage.success('已添加节点')
  } catch (e) { ElMessage.error('添加失败') }
  finally { addingNode.value = false }
}

function openAssign(row) {
  current.value = row
  // 既有系统用户 → 回显 ID；手动录入姓名 → 回显姓名文本
  assignUid.value = row.assignee || row.assignee_name || null
  assignVisible.value = true
}
async function submitAssign() {
  const v = assignUid.value
  if (v === null || v === undefined || v === '') return ElMessage.warning('请选择或录入外勤人员')
  const payload = {}
  // 数字 → 选择既有系统用户；字符串 → 手动录入的外勤人员姓名
  if (typeof v === 'number' || /^\d+$/.test(String(v).trim())) {
    payload.assignee = Number(v)
  } else {
    payload.assignee_name = String(v).trim()
  }
  submitting.value = true
  try {
    const r = await growthApi.assignFieldTask(current.value.id, payload)
    ElMessage.success(r?.detail || '已完成派单')
    assignVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

async function accept(row) {
  try {
    await growthApi.acceptFieldTask(row.id, {})
    ElMessage.success('已接单，任务进入办理流程')
    loadData()
  } catch (e) { ElMessage.error('接单失败') }
}

onMounted(() => { loadUsers(); loadData() })
</script>

<style scoped>
.ft-card { padding: 18px 18px 12px; }
.filter-bar { margin-bottom: 10px; }
.order-no { white-space: nowrap; font-variant-numeric: tabular-nums; font-size: 13px; letter-spacing: -0.2px; }
.sub-type { font-size: 11px; color: var(--text-3, #909399); margin-top: 2px; }
.node-brief { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: var(--text-2, #606266); font-variant-numeric: tabular-nums; }
.node-dot { width: 7px; height: 7px; border-radius: 50%; background: #c0c4cc; flex: none; }
.node-dot.done { background: #67c23a; }
.node-dot.doing { background: #e6a23c; }
.node-tip { display: flex; flex-wrap: wrap; gap: 4px; max-width: 240px; }
.nodes-mini { display: flex; flex-wrap: wrap; gap: 4px; }
.node-pill { font-size: 11px; padding: 1px 6px; border-radius: 4px; border: 1px solid #dcdfe6; }
.node-pill.pending { background: #f4f4f5; color: #909399; }
.node-pill.in_progress { background: #fdf6ec; color: #e6a23c; border-color: #faecd8; }
.node-pill.done { background: #f0f9eb; color: #67c23a; border-color: #e1f3d8; }
.node-row { display: flex; flex-direction: column; gap: 6px; }
.node-ctrl { display: flex; align-items: center; }
.muted { color: #909399; font-size: 12px; }
.add-node-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; padding: 10px; background: #f5f7fa; border-radius: 6px; }
.add-node-bar span { color: #606266; font-size: 14px; }
.latest-node { color: #409eff; font-size: 13px; }
</style>
