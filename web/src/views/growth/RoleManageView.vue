<template>
  <div class="growth-page">
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">已配置角色</div>
          <div class="mini-value">{{ total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">运营部</div>
          <div class="mini-value">{{ roleCount('OPS') }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">成交师</div>
          <div class="mini-value">{{ roleCount('CLOSER') }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">外勤人员</div>
          <div class="mini-value">{{ roleCount('FIELD') }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="main-card">
      <template #header>
        <div class="card-header">
          <span>增长中心 · 角色分配（运营 / 成交师 / 外勤 / 增值业务）</span>
          <div>
            <el-button type="primary" @click="openAdd">+ 分配角色</el-button>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" border stripe size="default">
        <el-table-column prop="user_name" label="员工" min-width="140" />
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <el-tag :type="roleColor(row.role)" size="small">{{ row.role_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="dept_label" label="所属部门" width="140" />
        <el-table-column label="是否超管" width="110">
          <template #default="{ row }">
            <el-switch v-model="row.can_view_all" @change="toggleAdmin(row)" />
          </template>
        </el-table-column>
        <el-table-column label="用户ID" width="80">
          <template #default="{ row }">{{ row.user }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="doDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !list.length" description="尚无角色分配" />
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="formVisible" :title="editing ? '编辑角色' : '分配新角色'" width="520px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="员工" required>
          <PersonSelect v-model="form.user" placeholder="选择员工" :disabled="true" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="form.role" placeholder="选择角色" style="width:100%">
            <el-option label="运营部 · 录入线索" value="OPS" />
            <el-option label="成交师 · 承接线索" value="CLOSER" />
            <el-option label="外勤人员 · 现场办理" value="FIELD" />
            <el-option label="增值专员 VA_STAFF · 增值台账" value="VA_STAFF" />
            <el-option label="增值主管 VA_MANAGER · 增值全部门" value="VA_MANAGER" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属部门">
          <el-select v-model="form.dept_key" placeholder="不限" clearable style="width:100%">
            <el-option label="增长中心" value="GROWTH" />
            <el-option label="增值业务部" value="VALUE_ADDED" />
            <el-option label="运营部" value="OPS" />
            <el-option label="电销部" value="SALES" />
          </el-select>
        </el-form-item>
        <el-form-item label="超级总账号">
          <el-switch v-model="form.can_view_all" />
          <span style="margin-left:8px;color:#909399;font-size:12px">开 = 可看全部数据 + 录入越权保护失效</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">{{ editing ? '保存' : '分配' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { growthApi } from '@/api/growth'
import axios from 'axios'
import PersonSelect from '@/components/PersonSelect.vue'

const list = ref([])
const users = ref([])
const loading = ref(false)
const formVisible = ref(false)
const editing = ref(false)

const form = reactive({ user: null, role: 'OPS', dept_key: 'GROWTH', can_view_all: false })

const total = computed(() => list.value.length)
function roleCount(r) { return list.value.filter(x => x.role === r).length }

function roleColor(r) {
  return { OPS: 'success', CLOSER: 'warning', FIELD: 'info',
           VA_STAFF: 'primary', VA_MANAGER: 'danger' }[r] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const res = await growthApi.growthRoles()
    list.value = Array.isArray(res) ? res : (res.results || [])
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  try {
    const http2 = axios.create({ baseURL: '/api', timeout: 20000 })
    const token = localStorage.getItem('token')
    if (token) http2.defaults.headers.Authorization = 'Bearer ' + token
    const res = await http2.get('/accounts/users/', { params: { page_size: 200 } })
    const raw = res.data
    const list2 = Array.isArray(raw?.results) ? raw.results : (Array.isArray(raw) ? raw : [])
    users.value = list2.filter(u => u && u.is_active !== false)
  } catch (e) { users.value = [] }
}

function openAdd() {
  editing.value = false
  Object.assign(form, { user: null, role: 'OPS', dept_key: 'GROWTH', can_view_all: false })
  if (!users.value.length) loadUsers()
  formVisible.value = true
}

function openEdit(row) {
  editing.value = true
  Object.assign(form, {
    id: row.id, user: row.user, role: row.role,
    dept_key: row.dept_key || '', can_view_all: !!row.can_view_all
  })
  if (!users.value.length) loadUsers()
  formVisible.value = true
}

async function submitForm() {
  if (!form.user) return ElMessage.warning('请选择员工')
  if (!form.role) return ElMessage.warning('请选择角色')
  try {
    if (editing.value) {
      await growthApi.updateGrowthRole(form.id, {
        role: form.role, dept_key: form.dept_key, can_view_all: form.can_view_all
      })
      ElMessage.success('已保存')
    } else {
      await growthApi.createGrowthRole({ ...form })
      ElMessage.success('已分配')
    }
    formVisible.value = false
    loadData()
  } catch (e) {}
}

async function toggleAdmin(row) {
  try {
    await growthApi.updateGrowthRole(row.id, { can_view_all: row.can_view_all })
    ElMessage.success('已更新')
  } catch (e) { row.can_view_all = !row.can_view_all }
}

async function doDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除 ${row.user_name} 的 ${row.role_label} 角色？`, '删除角色', { type: 'warning' })
    await growthApi.deleteGrowthRole(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) {}
}

onMounted(loadData)
</script>

<style scoped>
.growth-page { padding: 4px; }
.stat-row { margin-bottom: 14px; }
.mini-card { text-align: center; }
.mini-label { font-size: 13px; color: #909399; }
.mini-value { font-size: 24px; font-weight: 600; margin-top: 6px; color: #303133; }
.main-card { margin-top: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
