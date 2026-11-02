<template>
  <div class="yzf">
    <el-alert v-if="!data.has_api_key" type="info" :closable="false" show-icon
      title="本地账套台账模式"
      description="账套由会计部在此维护（增删改查均已落库）；配置 YUNZHANGFANG_API_KEY 后可对接云账房自动同步凭证与报表。"
      style="margin-bottom:12px" />

    <div class="yzf-head">
      <div>
        <h2 style="margin:0">云账房 · 财税数据中心</h2>
        <p class="sub">{{ data.account_name }}　·　账套 {{ data.book_total || 0 }} 个　·　凭证 {{ data.voucher_total || 0 }} 张</p>
      </div>
      <div>
        <el-button type="primary" @click="openCreate">+ 新增账套</el-button>
        <el-button @click="openPortal(data.portal_url)">前往云账房 ›</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="8"><el-card shadow="hover"><div class="kpi"><div class="num">{{ data.books.length }}</div><div class="lab">托管账套</div></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="hover"><div class="kpi"><div class="num">{{ data.pending_vouchers }}</div><div class="lab">待处理做账任务</div></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="hover"><div class="kpi"><div class="num">{{ totalVouchers }}</div><div class="lab">凭证总数</div></div></el-card></el-col>
    </el-row>

    <el-card style="margin-top:16px">
      <template #header>
        <div class="card-head">
          <span>账套列表</span>
          <div class="filters">
            <el-input v-model="filters.keyword" placeholder="账套名称 / 账套号" clearable style="width:200px"
              @keyup.enter="load" @clear="load" />
            <el-select v-model="filters.status" placeholder="全部状态" clearable style="width:130px" @change="load">
              <el-option label="启用中" value="ACTIVE" />
              <el-option label="已暂停" value="PAUSED" />
              <el-option label="已封存" value="CLOSED" />
            </el-select>
            <el-button @click="load">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="data.books" border stripe v-loading="loading">
        <el-table-column prop="name" label="账套名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="client_name" label="所属客户" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.client_name || '—' }}</template>
        </el-table-column>
        <el-table-column prop="taxpayer_type" label="纳税人类型" width="120" />
        <el-table-column prop="period" label="会计期间" width="110" />
        <el-table-column prop="vouchers" label="凭证数" width="90" align="center" />
        <el-table-column prop="yz_account_no" label="云账房账套号" width="150">
          <template #default="{ row }">{{ row.yz_account_no || '—' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === '启用中' ? 'success' : (row.status === '已暂停' ? 'warning' : 'info')">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="row.status === '启用中'" link type="warning" @click="setStatus(row, 'PAUSED')">暂停</el-button>
            <el-button v-else link type="success" @click="setStatus(row, 'ACTIVE')">启用</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="data.hint || '暂无账套，点击右上角「新增账套」开始维护'" :image-size="80" />
        </template>
      </el-table>
    </el-card>

    <!-- 新增/编辑账套 -->
    <el-dialog v-model="boxVisible" :title="editingId ? '编辑账套' : '新增账套'" width="560px" @closed="resetForm">
      <el-form :model="form" label-width="110px">
        <el-form-item label="所属代账客户" required>
          <el-select v-model="form.client" filterable placeholder="选择代账客户" style="width:100%"
            no-data-text="暂无代账客户，请先在「代账客户」页把成交客户转入代账">
            <el-option v-for="c in clients" :key="c.id" :label="c.customer_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="账套名称" required>
          <el-input v-model="form.name" placeholder="如：昆明云创科技有限公司（小规模）" maxlength="200" />
        </el-form-item>
        <el-form-item label="纳税人类型">
          <el-select v-model="form.taxpayer_type" style="width:100%">
            <el-option label="一般纳税人" value="GENERAL" />
            <el-option label="小规模纳税人" value="SMALL" />
            <el-option label="个体工商户" value="INDIVIDUAL" />
          </el-select>
        </el-form-item>
        <el-form-item label="会计期间" required>
          <el-input v-model="form.period" placeholder="如 2026-10（格式 YYYY-MM）" maxlength="7" />
        </el-form-item>
        <el-form-item label="期初余额">
          <el-input-number v-model="form.opening_balance" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
        <el-form-item label="凭证数">
          <el-input-number v-model="form.voucher_count" :min="0" style="width:100%" />
        </el-form-item>
        <el-form-item label="云账房账套号">
          <el-input v-model="form.yz_account_no" placeholder="选填，用于与云账房对应" maxlength="60" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width:100%">
            <el-option label="启用中" value="ACTIVE" />
            <el-option label="已暂停" value="PAUSED" />
            <el-option label="已封存" value="CLOSED" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="300" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="boxVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { integrationApi, accApi } from '@/api'

const data = ref({
  books: [], reports: [], account_name: '', pending_vouchers: 0,
  portal_url: 'https://www.yunzhangfang.com', is_demo: true, has_api_key: false,
  book_total: 0, voucher_total: 0, hint: ''
})
const loading = ref(false)
const filters = reactive({ keyword: '', status: '' })
const clients = ref([])
const totalVouchers = computed(() => data.value.books.reduce((s, b) => s + (b.vouchers || 0), 0))

// —— 账套增删改 ——
const boxVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)
const form = reactive({
  client: null, name: '', taxpayer_type: 'SMALL', period: '', opening_balance: 0,
  voucher_count: 0, yz_account_no: '', status: 'ACTIVE', remark: ''
})
const currentPeriod = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, '0')}`

async function load() {
  loading.value = true
  try {
    const r = await integrationApi.yunzhangfang()
    data.value = { ...data.value, ...(r.data || {}) }
  } catch (e) { /* 拦截器已提示 */ } finally { loading.value = false }
}

async function loadClients() {
  try {
    const r = await accApi.clients({ page_size: 500 })
    clients.value = r?.results || r?.data?.results || (Array.isArray(r) ? r : [])
  } catch (e) { clients.value = [] }
}

function resetForm() {
  editingId.value = null
  Object.assign(form, {
    client: null, name: '', taxpayer_type: 'SMALL', period: currentPeriod,
    opening_balance: 0, voucher_count: 0, yz_account_no: '', status: 'ACTIVE', remark: ''
  })
}

function openCreate() {
  resetForm()
  boxVisible.value = true
  if (!clients.value.length) loadClients()
}

function openEdit(row) {
  resetForm()
  editingId.value = row.id
  Object.assign(form, {
    client: row.client || null,
    name: row.name,
    taxpayer_type: row.taxpayer_type || 'SMALL',
    period: row.period,
    opening_balance: Number(row.opening_balance || 0),
    voucher_count: row.voucher_count || 0,
    yz_account_no: row.yz_account_no || '',
    status: row.status === '启用中' ? 'ACTIVE' : (row.status === '已暂停' ? 'PAUSED' : 'CLOSED'),
    remark: row.remark || ''
  })
  boxVisible.value = true
}

async function save() {
  if (!form.client) return ElMessage.warning('请选择所属代账客户')
  if (!form.name.trim()) return ElMessage.warning('请填写账套名称')
  if (!/^\d{4}-\d{2}$/.test(form.period)) return ElMessage.warning('会计期间格式应为 YYYY-MM，如 2026-10')
  saving.value = true
  try {
    if (editingId.value) {
      await accApi.updateBookSet(editingId.value, { ...form })
      ElMessage.success('已保存')
    } else {
      await accApi.createBookSet({ ...form })
      ElMessage.success('账套已创建')
    }
    boxVisible.value = false
    await load()
  } catch (e) { /* 拦截器已提示 */ } finally { saving.value = false }
}

async function setStatus(row, status) {
  try {
    await accApi.updateBookSet(row.id, { status })
    ElMessage.success(status === 'ACTIVE' ? '已启用' : '已暂停')
    load()
  } catch (e) { /* 拦截器已提示 */ }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除账套「${row.name}」？删除后可在操作日志追溯。`, '删除账套', { type: 'warning' })
  } catch { return }
  try {
    await accApi.deleteBookSet(row.id)
    ElMessage.success('已删除')
    load()
  } catch (e) { /* 拦截器已提示 */ }
}

function openPortal(url) { if (url) window.open(url, '_blank') }

onMounted(() => { load(); loadClients() })
</script>

<style scoped>
.yzf-head { display: flex; align-items: center; justify-content: space-between; background: #fff; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.yzf-head .sub { color: var(--text-sub); margin: 6px 0 0; font-size: 13px; }
.kpi { text-align: center; padding: 8px 0; }
.kpi .num { font-size: 28px; font-weight: 700; color: var(--primary); }
.kpi .lab { color: var(--text-sub); font-size: 13px; margin-top: 4px; }
.card-head { display: flex; align-items: center; justify-content: space-between; }
.filters { display: flex; gap: 8px; align-items: center; }
</style>
