<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">入职与离职管理</h2>
      <el-button type="primary" :icon="UserFilled" @click="openCreate">办理入职</el-button>
    </div>

    <!-- 统计 -->
    <el-row :gutter="14" style="margin-bottom:16px">
      <el-col :span="6" v-for="s in statCards" :key="s.label">
        <el-card shadow="never" class="stat-card">
          <div class="label">{{ s.label }}</div>
          <div class="value" :style="{ color: s.color }">{{ s.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <div class="card-title">员工名册
        <el-button text size="small" :icon="Refresh" @click="reload" style="float:right">刷新</el-button>
      </div>
      <el-table :data="list" v-loading="loading" size="small" stripe max-height="520" empty-text="暂无员工">
        <el-table-column prop="name" label="姓名" width="110" />
        <el-table-column prop="username" label="账号" width="120" />
        <el-table-column prop="dept_name" label="部门" width="100" />
        <el-table-column prop="team_name" label="小组" width="100" />
        <el-table-column prop="position_name" label="岗位" width="110" />
        <el-table-column prop="role_name" label="角色" width="100" />
        <el-table-column label="状态" width="90">
          <template #default="{row}"><el-tag size="small" :type="statusType(row.status)">{{ row.status_name }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="entry_date" label="入职日期" width="120" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{row}">
            <el-button v-if="row.status !== 'RESIGNED'" link type="danger" size="small" @click="offboard(row)">办理离职</el-button>
            <span v-else class="muted">已离职</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 入职弹窗：三步向导（2026-10-28 Boss 指示完善入职流程） -->
    <el-dialog v-model="visible" title="办理入职 · 分步向导" width="600px" :close-on-click-modal="false" @closed="resetForm">
      <el-steps :active="step" align-center finish-status="success" style="margin-bottom:22px">
        <el-step title="基础信息" />
        <el-step title="部门归属" />
        <el-step title="薪酬确认" />
      </el-steps>

      <!-- 第 1 步：基础信息 -->
      <div v-show="step === 0">
        <el-form :model="form" label-width="92px">
          <el-form-item label="登录账号" required>
            <el-input v-model="form.username" placeholder="员工登录账号，如 zhangsan" />
          </el-form-item>
          <el-form-item label="姓名" required>
            <el-input v-model="form.first_name" placeholder="员工姓名" />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="form.phone" placeholder="联系电话（可用于验证码登录）" />
          </el-form-item>
        </el-form>
      </div>

      <!-- 第 2 步：部门归属 -->
      <div v-show="step === 1">
        <el-form :model="form" label-width="92px">
          <el-form-item label="所属部门" required>
            <el-select v-model="form.department" placeholder="选择部门（入职即分配部门）" style="width:100%" @change="onDeptChange">
              <el-option v-for="d in deptOptions" :key="d.id" :label="d.name" :value="d.id" />
            </el-select>
            <div v-if="!deptOptions.length" class="warn-tip">
              暂无部门！请先到「行政人事部 → 组织与人员 → 组织架构」新增部门
            </div>
          </el-form-item>
          <el-form-item label="小组">
            <el-select v-model="form.team" placeholder="选择小组（可选）" clearable style="width:100%">
              <el-option v-for="t in teamOptionsFiltered" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="岗位">
            <el-select v-model="form.position" placeholder="选择岗位（可选）" clearable style="width:100%">
              <el-option v-for="p in posOptionsFiltered" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="角色" required>
            <el-select v-model="form.role" style="width:100%">
              <el-option v-for="r in roleOptions" :key="r.value" :label="r.label" :value="r.value" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <!-- 第 3 步：薪酬与确认 -->
      <div v-show="step === 2">
        <el-form :model="form" label-width="92px">
          <el-form-item label="入职日期">
            <el-date-picker v-model="form.entry_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
          </el-form-item>
          <el-form-item label="底薪(元)">
            <el-input-number v-model="form.base_salary" :min="0" :step="500" style="width:100%" />
          </el-form-item>
          <el-form-item label="月度目标(元)">
            <el-input-number v-model="form.month_target" :min="0" :step="1000" style="width:100%" />
          </el-form-item>
        </el-form>
        <el-descriptions :column="2" border size="small" style="margin-top:6px">
          <el-descriptions-item label="账号">{{ form.username || '-' }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ form.first_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="部门">{{ deptName(form.department) }}</el-descriptions-item>
          <el-descriptions-item label="小组">{{ teamName(form.team) }}</el-descriptions-item>
          <el-descriptions-item label="岗位">{{ posName(form.position) }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ roleLabel(form.role) }}</el-descriptions-item>
        </el-descriptions>
        <el-alert type="info" :closable="false" show-icon style="margin-top:10px"
          title="确认后系统自动创建员工账号，初始密码为 123456，请提醒员工首次登录后修改。" />
      </div>

      <template #footer>
        <el-button v-if="step > 0" @click="step--">上一步</el-button>
        <el-button v-if="step < 2" type="primary" @click="nextStep">下一步</el-button>
        <el-button v-if="step === 2" type="primary" :loading="saving" @click="submit">确认入职</el-button>
        <el-button @click="visible = false">取消</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UserFilled, Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { orgApi } from '@/api'

const statusMap = { PROBATION: '试用期', REGULAR: '正式', INTERN: '实习', RESIGNED: '已离职' }
const statusType = (s) => ({ PROBATION: 'warning', REGULAR: 'success', INTERN: '', RESIGNED: 'info' }[s] || 'info')

const list = ref([])
const loading = ref(false)
const deptOptions = ref([])
const teamOptions = ref([])
const posOptions = ref([])
const roleOptions = [
  { value: 'EMPLOYEE', label: '员工' }, { value: 'LEADER', label: '组长/主管' },
  { value: 'MANAGER', label: '部门经理' }, { value: 'HR', label: '人事行政' }, { value: 'BOSS', label: '老板/总经理' },
]

const visible = ref(false)
const saving = ref(false)
const step = ref(0)
const form = reactive({
  username: '', first_name: '', phone: '', department: null, team: null,
  position: null, role: 'EMPLOYEE', entry_date: dayjs().format('YYYY-MM-DD'),
  base_salary: 3500, month_target: 0,
})

// 向导辅助：名称回显 + 按部门过滤小组/岗位
const teamOptionsFiltered = computed(() => {
  if (!form.department) return []
  return (teamOptions.value || []).filter(t => !t.department || t.department === form.department)
})
const posOptionsFiltered = computed(() => {
  if (!form.department) return []
  return (posOptions.value || []).filter(p => !p.department || p.department === form.department)
})
const deptName = (id) => (deptOptions.value.find(d => d.id === id) || {}).name || '-'
const teamName = (id) => (teamOptions.value.find(t => t.id === id) || {}).name || '-'
const posName = (id) => (posOptions.value.find(p => p.id === id) || {}).name || '-'
const roleLabel = (v) => (roleOptions.find(r => r.value === v) || {}).label || v

function nextStep() {
  if (step.value === 0) {
    if (!form.username) return ElMessage.warning('第 1 步：请填写登录账号')
    if (!form.first_name) return ElMessage.warning('第 1 步：请填写姓名')
  }
  if (step.value === 1) {
    if (!form.department) return ElMessage.warning('第 2 步：请选择所属部门（入职即分配部门）')
  }
  step.value++
}

const statCards = computed(() => {
  const all = list.value
  const cnt = (s) => all.filter(u => u.status === s).length
  return [
    { label: '在职总数', value: all.length, color: '#1f2329' },
    { label: '试用期', value: cnt('PROBATION'), color: '#c07a12' },
    { label: '正式', value: cnt('REGULAR'), color: '#12865a' },
    { label: '已离职', value: cnt('RESIGNED'), color: '#c3372c' },
  ]
})

async function reload() {
  loading.value = true
  try {
    const r = await orgApi.users({ page_size: 300 })
    const rows = (r.results || r.data || []).map(u => ({
      ...u,
      name: u.name || u.first_name || u.username,
      dept_name: u.department_name || '-',
      team_name: u.team_name || '-',
      position_name: u.position_name || '-',
      role_name: (roleOptions.find(x => x.value === u.role) || {}).label || u.role,
      status_name: statusMap[u.status] || u.status,
    }))
    list.value = rows
  } finally { loading.value = false }
}

async function loadOptions() {
  const [d, t, p] = await Promise.all([
    orgApi.departments({ page_size: 50 }),
    orgApi.teams({ page_size: 100 }),
    orgApi.positions({ page_size: 100 }),
  ])
  deptOptions.value = d.results || d.data || []
  teamOptions.value = t.results || t.data || []
  posOptions.value = p.results || p.data || []
}
function onDeptChange() {
  // 切换部门时清空小组/岗位，避免跨部门脏数据
  form.team = null
  form.position = null
}

function resetForm() {
  Object.assign(form, {
    username: '', first_name: '', phone: '', department: null, team: null,
    position: null, role: 'EMPLOYEE', entry_date: dayjs().format('YYYY-MM-DD'),
    base_salary: 3500, month_target: 0,
  })
  step.value = 0
}
function openCreate() { resetForm(); visible.value = true }

async function submit() {
  if (!form.username) return ElMessage.warning('请填写登录账号')
  if (!form.first_name) return ElMessage.warning('请填写姓名')
  if (!form.department) return ElMessage.warning('请选择所属部门（入职即分配部门）')
  saving.value = true
  try {
    const pwd = '123456'
    await orgApi.createUser({
      username: form.username, first_name: form.first_name, phone: form.phone,
      password: pwd,
      department: form.department, team: form.team || null, position: form.position || null,
      role: form.role, status: 'PROBATION', entry_date: form.entry_date,
      base_salary: form.base_salary, month_target: form.month_target,
    })
    ElMessage.success(`入职办理成功！账号 ${form.username}，初始密码 ${pwd}，请告知员工登录后修改`)
    visible.value = false
    reload()
  } catch (e) { ElMessage.error('入职失败，请检查账号是否重复') }
  finally { saving.value = false }
}

async function offboard(row) {
  try {
    await ElMessageBox.confirm(`确认将「${row.name}」办理离职？`, '办理离职', { type: 'warning' })
  } catch { return }
  try {
    await orgApi.updateUser(row.id, { status: 'RESIGNED', leave_date: dayjs().format('YYYY-MM-DD') })
    ElMessage.success('已办理离职')
    reload()
  } catch (e) { ElMessage.error('操作失败') }
}

onMounted(() => { reload(); loadOptions() })
</script>

<style scoped>
.stat-card { border-radius: 10px; border: 1px solid var(--border); }
.stat-card .value { font-size: 24px; font-weight: 800; }
.card-title { font-weight: 700; margin-bottom: 14px; font-size: 15px; }
.muted { color: var(--text-sub); font-size: 13px; }
.warn-tip { color: #c3372c; font-size: 12px; line-height: 1.6; margin-top: 4px; }
</style>
