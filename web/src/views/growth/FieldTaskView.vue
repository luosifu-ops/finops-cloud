<template>
  <div class="field-tasks">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>外勤任务池 · 精细化进度节点管理</span>
          <div>
            <el-button v-if="canManage" type="success" plain @click="openFromDeal">成交单 → 生成外勤任务</el-button>
            <el-button type="primary" @click="openCreate">+ 新建外勤任务</el-button>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

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

      <el-table :data="list" v-loading="loading" border stripe size="default" max-height="560">
        <el-table-column label="外勤单号" width="140">
          <template #default="{ row }"><span class="order-no">{{ row.task_no || formatOrderNo(row) }}</span></template>
        </el-table-column>
        <el-table-column prop="customer_name" label="客户名称" min-width="120" />
        <el-table-column label="客户类型" width="90">
          <template #default="{ row }"><el-tag size="small">{{ row.customer_type_label }}</el-tag></template>
        </el-table-column>
        <el-table-column label="业务类型" width="100">
          <template #default="{ row }"><el-tag type="warning" size="small">{{ row.business_type_label }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="task_type" label="任务类型" width="120" />
        <el-table-column prop="from_order_no" label="来源成交单号" width="120" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ row.status_label }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="assignee_name" label="外勤人员" width="100" />
        <el-table-column prop="creator_name" label="下单人" width="100" />
        <el-table-column label="当前进度" width="140">
          <template #default="{ row }"><span class="latest-node">{{ row.latest_node || '-' }}</span></template>
        </el-table-column>
        <el-table-column label="进度节点" min-width="200">
          <template #default="{ row }">
            <div class="nodes-mini">
              <span v-for="n in (row.nodes || [])" :key="n.id" class="node-pill" :class="n.status.toLowerCase()">
                {{ n.node_label }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openNodes(row)">节点进度</el-button>
            <el-button v-if="canManage" link type="warning" @click="openAssign(row)">派单</el-button>
            <el-button v-if="row.status === 'PENDING'" link type="success" @click="accept(row)">接单</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
    <el-dialog v-model="assignVisible" title="外勤主管派单" width="460px">
      <el-form label-width="90px">
        <el-form-item label="任务">{{ current?.order_no || current?.customer_name }}</el-form-item>
        <el-form-item label="外勤人员">
          <el-select
            v-model="assignUid"
            placeholder="选择外勤人员，或输入姓名后回车手动录入"
            style="width:100%"
            filterable
            allow-create
            default-first-option
            clearable>
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
          <div style="font-size:12px;color:#909399;margin-top:4px;line-height:1.5">可直接输入外勤人员姓名（系统外人员将以姓名文本留存）</div>
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
import { ElMessage } from 'element-plus'
import { growthApi } from '@/api/growth'
import { orgApi } from '@/api/index'
import { useUserStore } from '@/store/user'

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

const list = ref([])
const loading = ref(false)
const filters = reactive({ status: '' })
const users = ref([])

const createVisible = ref(false)
const dealVisible = ref(false)
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

function statusType(s) {
  return { PENDING: 'info', ACCEPTED: 'primary', IN_PROGRESS: 'warning', DONE: 'success', CLOSED: 'info' }[s] || 'info'
}
function statusType2(s) {
  return { PENDING: 'info', IN_PROGRESS: 'warning', DONE: 'success' }[s] || 'info'
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
    await growthApi.assignFieldTask(current.value.id, payload)
    ElMessage.success('已派单')
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
.field-tasks { padding: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { margin-bottom: 8px; }
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
