<template>
  <BaseListView
    title="工商事项"
    baseUrl="/accounting/business-items/"
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

const ITEM_TYPE = {
  REGISTER: '注册', CHANGE: '变更', CANCEL: '注销', ABNORMAL: '异常处理',
  ADDRESS: '地址迁移', LICENSE: '证照办理', BRANCH: '分公司', OTHER: '其他',
}
const STATUS = {
  PENDING: '待处理', PROCESSING: '办理中', DONE: '已完成', REJECTED: '已驳回', CANCELED: '已取消',
}

const columns = [
  { prop: 'client_name', label: '客户', minWidth: 150 },
  { prop: 'title', label: '事项标题', minWidth: 150 },
  { prop: 'item_type', label: '事项类型', width: 100, dict: ITEM_TYPE },
  { prop: 'status', label: '状态', width: 95, dict: STATUS },
  { prop: 'handler_name', label: '处理人', width: 100 },
  { prop: 'start_at', label: '开始日期', width: 105 },
  { prop: 'due_at', label: '截止日期', width: 105 },
  { prop: 'finished_at', label: '完成日期', width: 105 },
  { prop: 'progress', label: '进度(%)', width: 85 },
  { prop: 'fee', label: '费用', width: 95 },
  { prop: 'result', label: '办理结果', minWidth: 130 },
]

// —— 新增/编辑表单（2026-10-30 增量：录错可改、可删）——
const formFields = [
  { prop: 'title', label: '事项标题', type: 'text', required: true },
  { prop: 'client', label: '客户', type: 'select' },
  { prop: 'item_type', label: '事项类型', type: 'select', options: Object.entries(ITEM_TYPE).map(([value, label]) => ({ value, label })) },
  { prop: 'status', label: '状态', type: 'select', options: Object.entries(STATUS).map(([value, label]) => ({ value, label })) },
  { prop: 'handler', label: '处理人', type: 'select' },
  { prop: 'start_at', label: '开始日期', type: 'date' },
  { prop: 'due_at', label: '截止日期', type: 'date' },
  { prop: 'finished_at', label: '完成日期', type: 'date' },
  { prop: 'progress', label: '进度(%)', type: 'number' },
  { prop: 'fee', label: '费用', type: 'number' },
  { prop: 'result', label: '办理结果', type: 'textarea' },
  { prop: 'remark', label: '备注', type: 'textarea' },
]

const searchFields = [
  { prop: 'title', label: '事项标题' },
  { prop: 'client_name', label: '客户' },
]

// —— FK 下拉选项：客户（代账客户）+ 员工（处理人）——
const optionSources = ref({})
function loadOptions() {
  http.get('/accounting/clients/', { params: { page_size: 500 } }).then(resp => {
    const rows = resp?.data?.results || resp?.results || []
    optionSources.value.client = rows.map(c => ({ value: c.id, label: c.customer_name || ('客户#' + c.id) }))
  }).catch(() => {})
  http.get('/accounts/users/', { params: { page_size: 500 } }).then(resp => {
    const rows = resp?.results || resp?.data?.results || []
    optionSources.value.handler = rows.map(u => ({ value: u.id, label: u.display_name || u.username }))
  }).catch(() => {})
}
onMounted(loadOptions)
</script>
