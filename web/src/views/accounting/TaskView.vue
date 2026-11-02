<template>
  <BaseListView
    title="做账任务"
    baseUrl="/accounting/monthly-tasks/"
    :columns="columns"
    :formFields="formFields"
    :searchFields="searchFields"
    :optionSources="optionSources"
  />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import http from '@/api'

const STATUS = {
  WAIT_DOC: '待收资料', DOING: '做账中', WAIT_CONFIRM: '待客户确认',
  DECLARED: '已申报', DONE: '已完成', DELAYED: '已延期', SUSPENDED: '已暂停',
}

const columns = [
  { prop: 'client_name', label: '客户', minWidth: 160 },
  { prop: 'period', label: '税款所属期', width: 110 },
  { prop: 'accountant_name', label: '会计', width: 100 },
  { prop: 'status', label: '状态', width: 110, dict: STATUS },
  { prop: 'deadline', label: '申报截止', width: 110 },
  { prop: 'is_overdue', label: '是否逾期', width: 90 },
  { prop: 'vat_amount', label: '增值税', width: 100 },
  { prop: 'total_tax', label: '总税额', width: 100 },
  { prop: 'zero_declare', label: '零申报', width: 80 },
  { prop: 'remark', label: '备注', minWidth: 130 },
]

// —— 新增/编辑表单（2026-10-30 增量：录错可改、可删）——
const formFields = [
  { prop: 'client', label: '客户', type: 'select', required: true },
  { prop: 'period', label: '税款所属期', type: 'text', required: true, placeholder: '如 2026-10' },
  { prop: 'status', label: '状态', type: 'select', options: Object.entries(STATUS).map(([value, label]) => ({ value, label })) },
  { prop: 'accountant', label: '会计', type: 'select' },
  { prop: 'doc_received_at', label: '收资料日', type: 'date' },
  { prop: 'voucher_done_at', label: '凭证完成日', type: 'date' },
  { prop: 'declared_at', label: '申报日期', type: 'date' },
  { prop: 'deadline', label: '申报截止', type: 'date' },
  { prop: 'income', label: '收入', type: 'number' },
  { prop: 'cost', label: '成本', type: 'number' },
  { prop: 'profit', label: '利润', type: 'number' },
  { prop: 'vat_amount', label: '增值税', type: 'number' },
  { prop: 'surtax_amount', label: '附加税', type: 'number' },
  { prop: 'cit_amount', label: '企业所得税', type: 'number' },
  { prop: 'iit_amount', label: '个税', type: 'number' },
  { prop: 'stamp_amount', label: '印花税', type: 'number' },
  { prop: 'total_tax', label: '总税额', type: 'number' },
  { prop: 'is_overdue', label: '是否逾期', type: 'switch' },
  { prop: 'zero_declare', label: '零申报', type: 'switch' },
  { prop: 'remark', label: '备注', type: 'textarea' },
]

const searchFields = [
  { prop: 'client_name', label: '客户' },
  { prop: 'period', label: '税款所属期' },
]

// —— FK 下拉选项：客户（代账客户）+ 员工（会计）——
const optionSources = ref({})
function loadOptions() {
  http.get('/accounting/clients/', { params: { page_size: 500 } }).then(resp => {
    const rows = resp?.data?.results || resp?.results || []
    optionSources.value.client = rows.map(c => ({ value: c.id, label: c.customer_name || ('客户#' + c.id) }))
  }).catch(() => {})
  http.get('/accounts/users/', { params: { page_size: 500 } }).then(resp => {
    const rows = resp?.results || resp?.data?.results || []
    optionSources.value.accountant = rows.map(u => ({ value: u.id, label: u.display_name || u.username }))
  }).catch(() => {})
}
onMounted(loadOptions)
</script>
