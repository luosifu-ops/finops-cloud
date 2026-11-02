<template>
  <div>
    <BaseListView
      ref="listRef"
      title="员工管理"
      baseUrl="/accounts/users/"
      :columns="columns"
      :formFields="formFields"
      :searchFields="searchFields"
    >
      <template #header-extra>
        <el-button @click="downloadTemplate" :loading="tplLoading">下载导入模板</el-button>
        <el-button type="primary" plain @click="importVisible = true">批量导入员工</el-button>
      </template>
    </BaseListView>

    <!-- 批量导入 -->
    <el-dialog v-model="importVisible" title="批量导入员工（入/离职一批处理）" width="680px" @closed="onClosed">
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:12px"
        title="先下载模板按格式填写；部门/岗位需与系统中已有名称一致；初始密码留空则自动生成一次性密码" />

      <div class="imp-ops">
        <el-button @click="downloadTemplate">下载模板</el-button>
        <input ref="fileRef" type="file" accept=".csv,text/csv" style="display:none" @change="onFile" />
        <el-button type="primary" @click="fileRef?.click()">选择 CSV 文件</el-button>
        <span v-if="fileName" class="imp-file">{{ fileName }}（{{ rowCount }} 行）</span>
      </div>

      <div v-if="preview.length" class="imp-preview">
        <el-table :data="preview" border size="small" max-height="220">
          <el-table-column prop="name" label="姓名" width="90" />
          <el-table-column prop="phone" label="手机号" width="120" />
          <el-table-column prop="department_name" label="部门" width="100" />
          <el-table-column prop="position_name" label="岗位" width="110" />
          <el-table-column prop="role_name" label="角色" width="90" />
          <el-table-column prop="entry_date" label="入职日期" width="110" />
          <el-table-column prop="status_name" label="状态" width="90" />
        </el-table>
      </div>

      <div v-if="results.length" class="imp-result">
        <el-divider>导入结果：成功 {{ okCount }} 条，失败 {{ failCount }} 条</el-divider>
        <el-table :data="results" border size="small" max-height="240">
          <el-table-column prop="row" label="行号" width="70" />
          <el-table-column prop="name" label="姓名" width="90" />
          <el-table-column label="结果" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="row.ok ? 'success' : 'danger'">{{ row.ok ? '成功' : '失败' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="账号 / 原因" min-width="200">
            <template #default="{ row }">
              <span v-if="row.ok">{{ row.username }}</span>
              <span v-else class="imp-fail">{{ row.reason }}</span>
            </template>
          </el-table-column>
          <el-table-column label="一次性密码" width="150">
            <template #default="{ row }">
              <code v-if="row.one_time_password" class="imp-pwd">{{ row.one_time_password }}</code>
              <span v-else>—</span>
            </template>
          </el-table-column>
        </el-table>
        <div class="imp-note">※ 一次性密码仅本次展示，请立即复制转交员工；员工首次登录后建议自行修改。</div>
      </div>

      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="!preview.length" :loading="importing" @click="doImport">
          确认导入 {{ preview.length }} 条
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api'
import BaseListView from '@/components/BaseListView.vue'

const listRef = ref(null)
const tplLoading = ref(false)
const importVisible = ref(false)
const importing = ref(false)
const fileRef = ref(null)
const fileName = ref('')
const preview = ref([])
const results = ref([])
const okCount = computed(() => results.value.filter((r) => r.ok).length)
const failCount = computed(() => results.value.filter((r) => !r.ok).length)
const rowCount = computed(() => preview.value.length)

// ---------------- 角色 / 状态：以后端 choices 为准（中文） ----------------
// 值与 apps/accounts/models.py 的 ROLE_CHOICES / STATUS_CHOICES 严格对齐，
// 避免出现"下拉里没有当前值"或"选了存英文码"的问题。
const ROLE_OPTIONS = [
  { value: 'BOSS', label: '老板/总经理' },
  { value: 'MANAGER', label: '部门经理' },
  { value: 'LEADER', label: '组长/主管' },
  { value: 'HR', label: '人事行政' },
  { value: 'EMPLOYEE', label: '员工' },
]
const STATUS_OPTIONS = [
  { value: 'PROBATION', label: '试用期' },
  { value: 'REGULAR', label: '正式' },
  { value: 'INTERN', label: '实习' },
  { value: 'RESIGNED', label: '已离职' },
]

// ---------------- 列表列 ----------------
// 说明：角色/状态直接取后端 *_name（Django choices 的中文），
// 不再展示英文枚举码；用户名按 Boss 要求展示员工姓名，手机号单独一列。
const columns = [
  { prop: 'employee_no', label: '员工编号', width: 110 },
  { prop: 'username', label: '用户名', width: 130,
    formatter: (row) => row.display_name || row.username || '-' },
  { prop: 'display_name', label: '显示名', width: 130 },
  { prop: 'phone', label: '手机号', width: 130 },
  { prop: 'department_name', label: '部门', width: 110 },
  { prop: 'position_name', label: '岗位', width: 120 },
  { prop: 'role_name', label: '角色', width: 110 },
  { prop: 'status_name', label: '状态', width: 96 },
  { prop: 'entry_date', label: '入职日期', width: 116 },
  { prop: 'probation_end', label: '试用期结束', width: 116 },
  { prop: 'base_salary', label: '底薪(元)', width: 110 },
  { prop: 'month_target', label: '月目标(元)', width: 116 },
]

// ---------------- 新增/编辑表单 ----------------
// 用 reactive 是因为部门、岗位选项要等接口回来后再填入（保持同一引用即可响应）。
const formFields = reactive([
  { prop: 'first_name', label: '姓名', type: 'text', placeholder: '员工真实姓名（用于登录后显示）' },
  { prop: 'employee_no', label: '员工编号', type: 'text', placeholder: '留空自动生成，如 EMP0001' },
  { prop: 'username', label: '用户名', type: 'text', placeholder: '登录账号，留空自动用手机号' },
  { prop: 'phone', label: '手机号', type: 'text', placeholder: '11 位手机号，唯一' },
  { prop: 'department', label: '部门', type: 'select', options: [] },
  { prop: 'position', label: '岗位', type: 'select', options: [] },
  { prop: 'role', label: '角色', type: 'select', options: ROLE_OPTIONS, default: 'EMPLOYEE' },
  { prop: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS, default: 'PROBATION' },
  { prop: 'entry_date', label: '入职日期', type: 'date', default: null },
  { prop: 'probation_end', label: '试用期结束', type: 'date', default: null },
  { prop: 'base_salary', label: '底薪(元)', type: 'number' },
  { prop: 'month_target', label: '月目标(元)', type: 'number' },
])

// ---------------- 顶部筛选 ----------------
const searchFields = reactive([
  { prop: 'keyword', label: '姓名/手机号/工号' },
  { prop: 'department', label: '部门', type: 'select', options: [] },
  { prop: 'role', label: '角色', type: 'select', options: ROLE_OPTIONS },
  { prop: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS },
])

function fieldByProp(list, prop) {
  return list.find((f) => f.prop === prop)
}

async function loadOptions() {
  try {
    const d = await http.get('/accounts/departments/', { params: { page_size: 200 } })
    const rows = Array.isArray(d) ? d : (d?.results || [])
    const opts = rows.map((x) => ({ value: x.id, label: x.name }))
    fieldByProp(formFields, 'department').options = opts
    fieldByProp(searchFields, 'department').options = opts
  } catch (e) { /* 拦截器已提示 */ }
  try {
    const p = await http.get('/accounts/positions/', { params: { page_size: 200 } })
    const rows = Array.isArray(p) ? p : (p?.results || [])
    fieldByProp(formFields, 'position').options = rows.map((x) => ({ value: x.id, label: x.name }))
  } catch (e) { /* 拦截器已提示 */ }
}

onMounted(loadOptions)

// 表头别名 → 后端字段
const HEADER_MAP = {
  姓名: 'name', name: 'name',
  手机号: 'phone', 手机: 'phone', phone: 'phone',
  部门: 'department_name', 部门名称: 'department_name', department_name: 'department_name',
  岗位: 'position_name', 岗位名称: 'position_name', position_name: 'position_name',
  角色: 'role_name', role_name: 'role_name',
  入职日期: 'entry_date', entry_date: 'entry_date',
  状态: 'status_name', status_name: 'status_name',
  初始密码: 'password', 密码: 'password', password: 'password',
}

function parseCsvLine(line) {
  const out = []
  let cur = ''
  let inQ = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (inQ) {
      if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++ }
      else if (ch === '"') inQ = false
      else cur += ch
    } else if (ch === '"') inQ = true
    else if (ch === ',') { out.push(cur); cur = '' }
    else cur += ch
  }
  out.push(cur)
  return out
}

async function downloadTemplate() {
  tplLoading.value = true
  try {
    const resp = await http.get('/accounts/users/import-template/', { responseType: 'blob' })
    const blob = resp instanceof Blob ? resp : new Blob([resp], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'employee_import_template.csv'
    a.click()
    URL.revokeObjectURL(a.href)
    ElMessage.success('模板已下载')
  } catch (e) {
    ElMessage.error('模板下载失败，请重试')
  } finally { tplLoading.value = false }
}

async function onFile(ev) {
  const file = ev.target.files?.[0]
  if (!file) return
  const text = (await file.text()).replace(/^\uFEFF/, '')
  const lines = text.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length < 2) { ElMessage.warning('文件为空或只有表头'); return }
  const headers = parseCsvLine(lines[0]).map((h) => h.trim())
  const props = headers.map((h) => HEADER_MAP[h] || null)
  if (!props.includes('name') || !props.includes('phone')) {
    ElMessage.error('表头缺少「姓名」或「手机号」列，请使用下载的模板填写')
    return
  }
  const rows = []
  for (const line of lines.slice(1)) {
    const cells = parseCsvLine(line)
    const r = {}
    props.forEach((p, i) => { if (p && cells[i] !== undefined) r[p] = cells[i].trim() })
    if (Object.keys(r).length) rows.push(r)
  }
  preview.value = rows
  results.value = []
  fileName.value = file.name
  ev.target.value = ''
}

async function doImport() {
  if (!preview.value.length) return
  importing.value = true
  try {
    const r = await http.post('/accounts/users/bulk-import/', { rows: preview.value })
    results.value = r?.results || []
    ElMessage.success(r?.msg || '导入完成')
    listRef.value?.reload()
  } catch (e) { /* 拦截器已提示 */ } finally { importing.value = false }
}

function onClosed() {
  preview.value = []
  results.value = []
  fileName.value = ''
}
</script>

<style scoped>
.imp-ops { display: flex; align-items: center; gap: 10px; }
.imp-file { font-size: 12px; color: var(--text-sub); }
.imp-preview { margin-top: 12px; }
.imp-result { margin-top: 8px; }
.imp-fail { color: #f56c6c; }
.imp-pwd { background: #f2f4f7; padding: 2px 6px; border-radius: 4px; font-family: Menlo, monospace; }
.imp-note { font-size: 12px; color: var(--text-sub); margin-top: 8px; }
</style>
