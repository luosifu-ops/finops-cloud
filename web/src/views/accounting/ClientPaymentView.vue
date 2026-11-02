<template>
  <div>
    <!-- 收款总览卡片 -->
    <el-row :gutter="14" class="pay-kpis">
      <el-col :span="6">
        <el-card shadow="hover"><div class="kpi"><div class="num">¥{{ fmt(stats.total_due) }}</div><div class="lab">应收合计</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div class="kpi"><div class="num ok">¥{{ fmt(stats.total_paid) }}</div><div class="lab">已收合计</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div class="kpi"><div class="num danger">¥{{ fmt(stats.total_due_left) }}</div><div class="lab">未收合计</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><div class="kpi"><div class="num">{{ stats.unpaid_count ?? 0 }}</div><div class="lab">欠费笔数</div></div></el-card>
      </el-col>
    </el-row>

    <BaseListView
      ref="listRef"
      title="服务费收款台账"
      base-url="/accounting/client-payments/"
      :columns="columns"
      :form-fields="formFields"
      :search-fields="searchFields"
      :option-sources="optionSources"
    >
      <template #row-actions="{ row }">
        <el-button v-if="row.status !== 'PAID' && row.status !== 'REFUNDED'" link type="success" @click="quickPaid(row)">全额收清</el-button>
      </template>
    </BaseListView>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import http from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const listRef = ref(null)
const stats = ref({})
const optionSources = ref({ client: [] })

const fmt = (n) => Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const columns = [
  { prop: 'client_name', label: '代账客户', minWidth: 140 },
  { prop: 'period', label: '服务期间', width: 110 },
  { prop: 'amount_due', label: '应收金额', width: 120, align: 'right' },
  { prop: 'amount_paid', label: '已收金额', width: 120, align: 'right' },
  { prop: 'amount_due_left', label: '未收金额', width: 120, align: 'right' },
  { prop: 'status_name', label: '状态', width: 100 },
  { prop: 'method_name', label: '收款方式', width: 100 },
  { prop: 'paid_date', label: '收款日期', width: 110 },
  { prop: 'voucher_no', label: '收据/流水号', width: 130 },
  { prop: 'operator_name', label: '经手人', width: 100 },
  { prop: 'remark', label: '备注', minWidth: 140 },
]
const formFields = [
  { prop: 'client', label: '代账客户', type: 'select', required: true },
  { prop: 'period', label: '服务期间', type: 'text', required: true, placeholder: '如 2026-10、2026-Q4、2026-年度' },
  { prop: 'amount_due', label: '应收金额(元)', type: 'number', required: true },
  { prop: 'amount_paid', label: '已收金额(元)', type: 'number' },
  { prop: 'paid_date', label: '收款日期', type: 'date' },
  { prop: 'method', label: '收款方式', type: 'select', options: [
    { value: 'BANK', label: '对公转账' }, { value: 'WX', label: '微信' },
    { value: 'ALIPAY', label: '支付宝' }, { value: 'CASH', label: '现金' }, { value: 'OTHER', label: '其他' },
  ] },
  { prop: 'status', label: '状态', type: 'select', options: [
    { value: 'UNPAID', label: '未收' }, { value: 'PARTIAL', label: '部分到账' },
    { value: 'PAID', label: '已收清' }, { value: 'REFUNDED', label: '已退费' },
  ] },
  { prop: 'voucher_no', label: '收据/流水号', type: 'text' },
  { prop: 'remark', label: '备注', type: 'textarea' },
]
const searchFields = [
  { prop: 'search', label: '客户/期间/流水号', type: 'text' },
  { prop: 'status', label: '状态', type: 'select', options: formFields.find(f => f.prop === 'status').options },
  { prop: 'period', label: '服务期间', type: 'text' },
]

async function loadStats() {
  try {
    const r = await http.get('/accounting/client-payments/statistics/')
    stats.value = r?.data?.data || r?.data || {}
  } catch (e) { /* 静默 */ }
}
async function loadClients() {
  try {
    const r = await http.get('/accounting/clients/', { params: { page_size: 500 } })
    const rows = r?.results || r?.data?.results || r?.data || []
    optionSources.value = { client: rows.map(c => ({ value: c.id, label: c.customer_name || `客户${c.id}` })) }
  } catch (e) { /* 静默 */ }
}
async function quickPaid(row) {
  try {
    await ElMessageBox.confirm(`确认「${row.client_name}」${row.period} 服务费 ${fmt(row.amount_due_left)} 元已全额收清？`, '收清确认', { type: 'success' })
  } catch { return }
  try {
    await http.patch(`/accounting/client-payments/${row.id}/`, {
      amount_paid: row.amount_due, status: 'PAID', paid_date: new Date().toISOString().slice(0, 10),
    })
    ElMessage.success('已登记收清')
    loadStats()
  } catch (e) { ElMessage.error('操作失败，请重试') }
}

onMounted(() => { loadStats(); loadClients() })
</script>

<style scoped>
.pay-kpis { margin-bottom: 14px; }
.kpi { text-align: center; padding: 4px 0; }
.kpi .num { font-size: 22px; font-weight: 700; color: var(--primary); }
.kpi .num.ok { color: var(--el-color-success, #67c23a); }
.kpi .num.danger { color: var(--el-color-danger, #f56c6c); }
.kpi .lab { color: var(--text-sub); font-size: 12px; margin-top: 4px; }
</style>
