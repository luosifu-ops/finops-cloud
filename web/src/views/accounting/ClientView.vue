<template>
  <BaseListView
    title="代账客户"
    baseUrl="/accounting/clients/"
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

// —— 列表列（dict：枚举码 → 中文，走全站统一 formatCell）——
const columns = [
  { prop: 'customer_name', label: '客户名称', minWidth: 160 },
  { prop: 'taxpayer_type', label: '纳税人类型', width: 110, dict: { GENERAL: '一般纳税人', SMALL: '小规模纳税人', INDIVIDUAL: '个体户' } },
  { prop: 'tax_no', label: '税号', minWidth: 150 },
  { prop: 'accountant_name', label: '会计', width: 100 },
  { prop: 'assistant_name', label: '助理', width: 100 },
  { prop: 'status', label: '服务状态', width: 100, dict: { ACTIVE: '服务中', PAUSED: '暂停', STOPPED: '终止', TRANSFERRING: '转出中' } },
  { prop: 'monthly_fee', label: '月服务费', width: 110 },
  { prop: 'service_start', label: '服务开始', width: 110 },
  { prop: 'service_end', label: '服务到期', width: 110 },
  { prop: 'zero_declare', label: '零申报', width: 80 },
  { prop: 'remark', label: '备注', minWidth: 130 },
]

// —— 新增/编辑表单（2026-10-30 增量：录错可改、可删，显式字段替代 autoForm）——
const formFields = [
  { prop: 'customer', label: '客户', type: 'select', required: true },
  { prop: 'taxpayer_type', label: '纳税人类型', type: 'select', options: [
    { value: 'SMALL', label: '小规模纳税人' }, { value: 'GENERAL', label: '一般纳税人' }, { value: 'INDIVIDUAL', label: '个体户' },
  ] },
  { prop: 'tax_no', label: '税号', type: 'text' },
  { prop: 'tax_bureau', label: '主管税务机关', type: 'text' },
  { prop: 'status', label: '服务状态', type: 'select', options: [
    { value: 'ACTIVE', label: '服务中' }, { value: 'PAUSED', label: '暂停' }, { value: 'STOPPED', label: '终止' }, { value: 'TRANSFERRING', label: '转出中' },
  ] },
  { prop: 'accountant', label: '会计', type: 'select' },
  { prop: 'assistant', label: '助理', type: 'select' },
  { prop: 'bank_name', label: '开户行', type: 'text' },
  { prop: 'bank_account', label: '银行账户', type: 'text' },
  { prop: 'social_no', label: '社保账号', type: 'text' },
  { prop: 'ele_tax_account', label: '电子税局账号', type: 'text' },
  { prop: 'ele_tax_password', label: '电子税局密码', type: 'text' },
  { prop: 'ukey_password', label: 'UKey 密码', type: 'text' },
  { prop: 'service_start', label: '服务开始', type: 'date' },
  { prop: 'service_end', label: '服务到期', type: 'date' },
  { prop: 'monthly_fee', label: '月服务费', type: 'number' },
  { prop: 'zero_declare', label: '零申报', type: 'switch' },
  { prop: 'remark', label: '备注', type: 'textarea' },
]

const searchFields = [
  { prop: 'customer_name', label: '客户名称' },
  { prop: 'tax_no', label: '税号' },
]

// —— FK 下拉选项：客户 + 员工（会计/助理）——
const optionSources = ref({})
function loadOptions() {
  // 客户（电销客户档案）
  http.get('/sales/customers/', { params: { page_size: 500 } }).then(resp => {
    const rows = resp?.data?.results || resp?.results || []
    optionSources.value.customer = rows.map(c => ({ value: c.id, label: c.name }))
  }).catch(() => {})
  // 员工（会计 / 助理）
  http.get('/accounts/users/', { params: { page_size: 500 } }).then(resp => {
    const rows = resp?.results || resp?.data?.results || []
    const opts = rows.map(u => ({ value: u.id, label: u.display_name || u.username }))
    optionSources.value.accountant = opts
    optionSources.value.assistant = opts
  }).catch(() => {})
}
onMounted(loadOptions)
</script>
