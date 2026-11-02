<template>
  <div class="dec-page">
    <div class="page-head">
      <h2 class="page-title">纳税申报</h2>
      <div class="head-tools">
        <el-select v-model="filters.status" placeholder="申报状态" clearable style="width: 130px" @change="load">
          <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
        </el-select>
        <el-select v-model="filters.tax_type" placeholder="税种" clearable filterable style="width: 150px" @change="load">
          <el-option v-for="t in taxTypes" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-input
          v-model="filters.period"
          placeholder="税款所属期 如 2026-09"
          clearable
          style="width: 190px"
          @clear="load"
          @keyup.enter="load"
        />
        <el-button type="primary" @click="load">查询</el-button>
        <el-button @click="loadDeadline">临近申报</el-button>
        <el-button type="success" @click="openCreate">新增申报</el-button>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" border stripe style="width: 100%">
        <el-table-column type="index" label="序号" width="55" />
        <el-table-column prop="client_name" label="客户" min-width="170" show-overflow-tooltip />
        <el-table-column prop="tax_type_name" label="税种" width="120" />
        <el-table-column prop="period" label="税款所属期" width="120" />
        <el-table-column prop="deadline" label="申报截止日" width="130" />
        <el-table-column prop="amount" label="申报税额" width="120" align="right">
          <template #default="{ row }">{{ fmtMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="paid_amount" label="已缴税额" width="120" align="right">
          <template #default="{ row }">{{ fmtMoney(row.paid_amount) }}</template>
        </el-table-column>
        <el-table-column prop="status_name" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small" effect="light">{{ row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="申报人" width="110" />
        <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="['PENDING', 'OVERDUE', 'ZERO'].includes(row.status)"
              link
              type="success"
              @click="markDeclared(row)"
            >标记已申报</el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="total > pageSize"
        class="pager"
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPage"
      />
      <el-empty v-if="!loading && list.length === 0" description="暂无纳税申报记录，点击右上角“新增申报”创建" />
    </el-card>

    <!-- 新增 / 编辑 弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑申报' : '新增申报'" width="580px" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-form-item label="关联任务" required>
          <el-select v-model="form.task" filterable placeholder="选择月度做账任务" style="width: 100%">
            <el-option v-for="t in tasks" :key="t.id" :label="`${t.client_name} · ${t.period}`" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="税种">
          <el-select v-model="form.tax_type" clearable filterable placeholder="选择税种" style="width: 100%">
            <el-option v-for="t in taxTypes" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="税款所属期">
          <el-input v-model="form.period" placeholder="如 2026-09" />
        </el-form-item>
        <el-form-item label="申报截止日">
          <el-date-picker v-model="form.deadline" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="申报税额">
          <el-input-number v-model="form.amount" :min="0" :precision="2" :step="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="已缴税额">
          <el-input-number v-model="form.paid_amount" :min="0" :precision="2" :step="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="申报人">
          <PersonSelect v-model="form.operator" placeholder="选择申报人" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api'
import PersonSelect from '@/components/PersonSelect.vue'

const loading = ref(false)
const saving = ref(false)
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const rawList = ref([])

const filters = reactive({ status: '', tax_type: '', period: '' })

const list = computed(() => {
  const p = (filters.period || '').trim()
  if (!p) return rawList.value
  return rawList.value.filter((r) => (r.period || '').includes(p))
})

const statusOptions = [
  { value: 'PENDING', label: '待申报' },
  { value: 'DECLARED', label: '已申报' },
  { value: 'PAID', label: '已缴税' },
  { value: 'OVERDUE', label: '逾期' },
  { value: 'ZERO', label: '零申报' },
]
function statusTag(s) {
  return { PENDING: 'warning', DECLARED: 'success', PAID: 'success', OVERDUE: 'danger', ZERO: 'info' }[s] || 'info'
}
function fmtMoney(v) {
  const n = Number(v || 0)
  return '¥' + n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 下拉数据
const taxTypes = ref([])
const tasks = ref([])
const users = ref([])

async function loadOptions() {
  try {
    const [tt, tk, us] = await Promise.all([
      http.get('/accounting/tax-types/', { params: { page_size: 100 } }),
      http.get('/accounting/monthly-tasks/', { params: { page_size: 300 } }),
      http.get('/accounts/users/', { params: { page_size: 300 } }),
    ])
    taxTypes.value = Array.isArray(tt) ? tt : (tt.results || [])
    tasks.value = Array.isArray(tk) ? tk : (tk.results || [])
    users.value = Array.isArray(us) ? us : (us.results || [])
  } catch (e) { /* 下拉失败不影响主列表 */ }
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filters.status) params.status = filters.status
    if (filters.tax_type) params.tax_type = filters.tax_type
    const r = await http.get('/accounting/tax-declarations/', { params })
    rawList.value = r.results || []
    total.value = r.count || rawList.value.length
  } catch (e) {
    rawList.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onPage(p) {
  page.value = p
  load()
}

async function loadDeadline() {
  loading.value = true
  try {
    const r = await http.get('/accounting/tax-declarations/deadline/', { params: { days: 15 } })
    const data = (r && r.data) || []
    const arr = Array.isArray(data) ? data : (data.results || [])
    rawList.value = arr
    total.value = arr.length
    filters.status = ''
    filters.tax_type = ''
    filters.period = ''
    if (arr.length === 0) ElMessage.info('近 15 天内暂无待申报记录')
  } catch (e) {
    rawList.value = []
  } finally {
    loading.value = false
  }
}

// 新增 / 编辑
const dialogVisible = ref(false)
const editingId = ref(null)
const form = reactive({
  task: null, tax_type: null, period: '', deadline: '', amount: 0, paid_amount: 0, status: 'PENDING', operator: null, remark: '',
})

function resetForm() {
  editingId.value = null
  Object.assign(form, {
    task: null, tax_type: null, period: '', deadline: '', amount: 0, paid_amount: 0, status: 'PENDING', operator: null, remark: '',
  })
}
function openCreate() {
  resetForm()
  dialogVisible.value = true
}
function openEdit(row) {
  resetForm()
  editingId.value = row.id
  form.task = row.task
  form.tax_type = row.tax_type
  form.period = row.period
  form.deadline = row.deadline
  form.amount = Number(row.amount) || 0
  form.paid_amount = Number(row.paid_amount) || 0
  form.status = row.status
  form.operator = row.operator
  form.remark = row.remark || ''
  dialogVisible.value = true
}

async function submit() {
  if (!form.task) {
    ElMessage.warning('请选择关联任务')
    return
  }
  saving.value = true
  const payload = {
    task: form.task,
    tax_type: form.tax_type || null,
    period: form.period,
    deadline: form.deadline || null,
    amount: form.amount,
    paid_amount: form.paid_amount,
    status: form.status,
    operator: form.operator || null,
    remark: form.remark,
  }
  try {
    if (editingId.value) {
      await http.patch(`/accounting/tax-declarations/${editingId.value}/`, payload)
      ElMessage.success('已保存')
    } else {
      await http.post('/accounting/tax-declarations/', payload)
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    load()
  } catch (e) {
    ElMessage.error('保存失败，请检查字段')
  } finally {
    saving.value = false
  }
}

async function markDeclared(row) {
  try {
    await http.post(`/accounting/tax-declarations/${row.id}/declare/`)
    ElMessage.success('已标记为已申报')
    load()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.client_name || ''} ${row.tax_type_name || ''}」的申报记录？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await http.delete(`/accounting/tax-declarations/${row.id}/`)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  loadOptions()
  load()
})
</script>

<style scoped>
.dec-page { padding: 4px; }
.page-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px; flex-wrap: wrap; gap: 10px;
}
.page-title { font-size: 18px; margin: 0; }
.head-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.table-card { border-radius: 10px; }
.pager { margin-top: 14px; display: flex; justify-content: flex-end; }
</style>
