<template>
  <div class="growth-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="block-title">外勤与增值业务</span>
          <el-button type="primary" @click="activeTab === 'field' ? openTask() : openProject()">
            + {{ activeTab === 'field' ? '新建外勤任务' : '新建增值项目' }}
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <!-- ============ 外勤 ============ -->
        <el-tab-pane label="外勤任务与进度" name="field">
          <el-table :data="tasks" v-loading="tLoading" border stripe>
            <el-table-column prop="title" label="任务" min-width="160" />
            <el-table-column prop="order_no" label="单号" width="130" />
            <el-table-column prop="customer_name" label="客户" width="150" />
            <el-table-column prop="task_type" label="类型" width="110" />
            <el-table-column prop="assignee_name" label="外勤" width="100">
              <template #default="{ row }">{{ row.assignee_name || '待分配' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="taskTagType(row.status)" size="small">{{ row.status_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="latest_node" label="最新节点" width="130">
              <template #default="{ row }">
                <span v-if="row.latest_node">{{ row.latest_node }}</span>
                <span v-else class="muted">暂无</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="380" fixed="right">
              <template #default="{ row }">
                <el-button link @click="viewProgress(row)">进度流水</el-button>
                <el-button link type="primary" @click="openReport(row)">上报进度</el-button>
                <el-button v-if="row.status === 'PENDING'" link type="success" @click="doAcceptTask(row)">接单</el-button>
                <el-button
                  v-if="row.status === 'ACCEPTED' || row.status === 'IN_PROGRESS'"
                  link type="danger" @click="doReturnBack(row)"
                >回退</el-button>
                <el-button link type="warning" @click="openEditTask(row)">编辑</el-button>
                <el-button link type="danger" @click="removeTask(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- ============ 增值业务部 ============ -->
        <el-tab-pane label="增值业务部台账" name="va">
          <el-table :data="projects" v-loading="pLoading" border stripe>
            <el-table-column prop="name" label="项目名称" min-width="180" />
            <el-table-column prop="customer_name" label="客户" width="150" />
            <el-table-column prop="project_type" label="业务类型" width="120" />
            <el-table-column prop="owner_name" label="负责人" width="110" />
            <el-table-column label="合同金额" width="120">
              <template #default="{ row }">¥{{ money(row.amount) }}</template>
            </el-table-column>
            <el-table-column label="成本" width="110">
              <template #default="{ row }">¥{{ money(row.cost) }}</template>
            </el-table-column>
            <el-table-column label="利润" width="120">
              <template #default="{ row }">
                <span class="profit">¥{{ money(row.profit) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="vaTagType(row.status)" size="small">{{ row.status_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button link type="warning" @click="openEditProject(row)">编辑</el-button>
                <el-button link type="danger" @click="removeProject(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 外勤任务：新建/编辑 -->
    <el-dialog v-model="taskVisible" :title="editingTaskId ? '编辑外勤任务' : '新建外勤任务'" width="560px">
      <el-form :model="taskForm" label-width="100px">
        <el-form-item label="任务标题" required><el-input v-model="taskForm.title" /></el-form-item>
        <el-form-item label="关联单号"><el-input v-model="taskForm.order_no" placeholder="选填，便于销售查询" /></el-form-item>
        <el-form-item label="客户名称"><el-input v-model="taskForm.customer_name" /></el-form-item>
        <el-form-item label="任务类型">
          <el-select v-model="taskForm.task_type" style="width:100%">
            <el-option v-for="t in taskTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="办理地点"><el-input v-model="taskForm.address" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="taskForm.remark" type="textarea" :rows="2" /></el-form-item>
        <el-alert type="info" :closable="false" show-icon
                  title="创建后由外勤人员接单并上报进度，销售可在本页实时查看" />
      </el-form>
      <template #footer>
        <el-button @click="taskVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitTask">{{ editingTaskId ? '保存修改' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- 外勤：进度上报 -->
    <el-dialog v-model="reportVisible" title="上报外勤进度" width="480px">
      <el-form :model="reportForm" label-width="90px">
        <el-form-item label="任务">{{ curTask?.title }}</el-form-item>
        <el-form-item label="办理节点" required>
          <el-select v-model="reportForm.node" allow-create filterable placeholder="选择或输入节点" style="width:100%">
            <el-option v-for="n in nodeOptions" :key="n" :label="n" :value="n" />
          </el-select>
        </el-form-item>
        <el-form-item label="进度说明"><el-input v-model="reportForm.content" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="更新状态">
          <el-select v-model="reportForm.status" style="width:100%">
            <el-option label="办理中" value="IN_PROGRESS" />
            <el-option label="已完成" value="DONE" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReport">上报</el-button>
      </template>
    </el-dialog>

    <!-- 进度流水 -->
    <el-dialog v-model="progressVisible" title="外勤进度流水" width="560px">
      <el-timeline>
        <el-timeline-item v-for="p in progresses" :key="p.id" :timestamp="fmt(p.created_at)" placement="top">
          <strong>{{ p.node }}</strong>
          <div class="muted">{{ p.content }} · {{ p.reported_by_name }}</div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-if="!progresses.length" description="暂无进度记录" />
    </el-dialog>

    <!-- 增值业务：新建/编辑 -->
    <el-dialog v-model="projVisible" :title="editingProjId ? '编辑增值项目' : '新建增值业务项目'" width="560px">
      <el-form :model="projForm" label-width="100px">
        <el-form-item label="项目名称" required><el-input v-model="projForm.name" /></el-form-item>
        <el-form-item label="客户名称"><el-input v-model="projForm.customer_name" /></el-form-item>
        <el-form-item label="业务类型">
          <el-select v-model="projForm.project_type" style="width:100%">
            <el-option v-for="t in vaTypes" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="合同金额"><el-input-number v-model="projForm.amount" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="成本"><el-input-number v-model="projForm.cost" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="projForm.status" style="width:100%">
            <el-option label="待启动" value="DRAFT" />
            <el-option label="进行中" value="DOING" />
            <el-option label="已完成" value="DONE" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="projForm.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitProject">{{ editingProjId ? '保存修改' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { growthApi } from '@/api/growth'

const activeTab = ref('field')
const tasks = ref([])
const projects = ref([])
const tLoading = ref(false)
const pLoading = ref(false)

const taskTypes = ['工商注册', '异常处理', '注销', '税务报到', '地址异常', '银行开户', '其他']
const vaTypes = ['高新认定', '资质办理', '税务筹划', '审计', '验资', '其他']
const nodeOptions = ['已取件', '已提交工商', '审核中', '审核通过', '已办结', '材料补正']

const taskVisible = ref(false)
const reportVisible = ref(false)
const progressVisible = ref(false)
const projVisible = ref(false)
const saving = ref(false)
const editingTaskId = ref(null)
const editingProjId = ref(null)
const curTask = ref(null)
const progresses = ref([])

const taskForm = reactive({ title: '', order_no: '', customer_name: '', task_type: '', address: '', remark: '' })
const reportForm = reactive({ node: '', content: '', status: 'IN_PROGRESS' })
const projForm = reactive({ name: '', customer_name: '', project_type: '', amount: 0, cost: 0, status: 'DRAFT', remark: '' })

function money(v) { return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function fmt(t) { return t ? String(t).slice(0, 19).replace('T', ' ') : '' }
function taskTagType(s) { return { PENDING: 'info', ACCEPTED: 'primary', IN_PROGRESS: 'warning', DONE: 'success', CLOSED: 'info' }[s] || 'info' }
function vaTagType(s) { return { DRAFT: 'info', DOING: 'warning', DONE: 'success', PAUSED: 'info', CANCELED: 'danger' }[s] || 'info' }

async function loadTasks() {
  tLoading.value = true
  try {
    const res = await growthApi.fieldTasks()
    tasks.value = Array.isArray(res) ? res : (res.results || [])
  } finally { tLoading.value = false }
}

async function loadProjects() {
  pLoading.value = true
  try {
    const res = await growthApi.projects()
    projects.value = Array.isArray(res) ? res : (res.results || [])
  } finally { pLoading.value = false }
}

function openTask() {
  Object.assign(taskForm, { title: '', order_no: '', customer_name: '', task_type: '', address: '', remark: '' })
  editingTaskId.value = null
  taskVisible.value = true
}

async function submitTask() {
  if (!taskForm.title) return ElMessage.warning('请填写任务标题')
  saving.value = true
  try {
    if (editingTaskId.value) {
      await growthApi.updateFieldTask(editingTaskId.value, { ...taskForm })
      ElMessage.success('已保存修改')
    } else {
      await growthApi.createFieldTask({ ...taskForm })
      ElMessage.success('已创建，等待外勤接单')
    }
    taskVisible.value = false
    loadTasks()
  } catch (e) {} finally { saving.value = false }
}

// 2026-10-31 增量：编辑外勤任务（回显，不含状态与外勤归属——状态走接单/上报，指派走主管派单）
function openEditTask(row) {
  editingTaskId.value = row.id
  Object.assign(taskForm, {
    title: row.title || '', order_no: row.order_no || '',
    customer_name: row.customer_name || '', task_type: row.task_type || '',
    address: row.address || '', remark: row.remark || '',
  })
  taskVisible.value = true
}

// 2026-10-31 增量：删除外勤任务（后端软删，保留进度与节点留痕）
async function removeTask(row) {
  try { await ElMessageBox.confirm(`确认删除任务「${row.title}」？`, '删除外勤任务', { type: 'warning', confirmButtonText: '确认删除' }) } catch { return }
  try {
    await growthApi.deleteFieldTask(row.id)
    ElMessage.success('已删除')
    loadTasks()
  } catch (e) {}
}

async function doAcceptTask(row) {
  await growthApi.acceptFieldTask(row.id)
  ElMessage.success('已接单')
  loadTasks()
}

// 外勤回退：把已接单/办理中的任务退回任务池，需填写原因
async function doReturnBack(row) {
  const { value } = await ElMessageBox.prompt(
    `回退任务「${row.title}」将退回外勤任务池，并通知派单人与下单人。请填写回退原因：`,
    '回退任务', {
      inputType: 'textarea',
      inputPlaceholder: '如：客户资料不齐无法办理 / 地址有误需重新确认',
      confirmButtonText: '确认回退',
    }).catch(() => ({ value: null }))
  if (value === null) return
  try {
    await growthApi.returnBackFieldTask(row.id, { reason: value || '' })
    ElMessage.success('已回退至外勤任务池')
    loadTasks()
  } catch (e) {}
}

function openReport(row) {
  curTask.value = row
  Object.assign(reportForm, { node: '', content: '', status: 'IN_PROGRESS' })
  reportVisible.value = true
}

async function submitReport() {
  if (!reportForm.node) return ElMessage.warning('请填写办理节点')
  await growthApi.reportProgress(curTask.value.id, { ...reportForm })
  ElMessage.success('进度已上报，销售端可实时查看')
  reportVisible.value = false
  loadTasks()
}

async function viewProgress(row) {
  curTask.value = row
  progressVisible.value = true
  progresses.value = await growthApi.taskProgresses(row.id) || []
}

function openProject() {
  Object.assign(projForm, { name: '', customer_name: '', project_type: '', amount: 0, cost: 0, status: 'DRAFT', remark: '' })
  editingProjId.value = null
  projVisible.value = true
}

async function submitProject() {
  if (!projForm.name) return ElMessage.warning('请填写项目名称')
  saving.value = true
  try {
    if (editingProjId.value) {
      await growthApi.updateProject(editingProjId.value, { ...projForm })
      ElMessage.success('已保存修改')
    } else {
      await growthApi.createProject({ ...projForm })
      ElMessage.success('已创建')
    }
    projVisible.value = false
    loadProjects()
  } catch (e) {} finally { saving.value = false }
}

// 2026-10-31 增量：编辑增值项目
function openEditProject(row) {
  editingProjId.value = row.id
  Object.assign(projForm, {
    name: row.name || '', customer_name: row.customer_name || '',
    project_type: row.project_type || '', amount: Number(row.amount || 0),
    cost: Number(row.cost || 0), status: row.status || 'DRAFT', remark: row.remark || '',
  })
  projVisible.value = true
}

// 2026-10-31 增量：删除增值项目
async function removeProject(row) {
  try { await ElMessageBox.confirm(`确认删除项目「${row.name}」？`, '删除增值项目', { type: 'warning', confirmButtonText: '确认删除' }) } catch { return }
  try {
    await growthApi.deleteProject(row.id)
    ElMessage.success('已删除')
    loadProjects()
  } catch (e) {}
}

onMounted(() => { loadTasks(); loadProjects() })
</script>

<style scoped>
.growth-page { padding: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.block-title { font-weight: 600; }
.muted { color: #909399; }
.profit { color: #67c23a; font-weight: 600; }
</style>
