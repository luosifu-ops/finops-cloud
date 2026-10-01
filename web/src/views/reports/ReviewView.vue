<template>
  <BaseListView
    title="专项复盘"
    baseUrl="/reports/review-reports/"
    :columns="columns"
    :formFields="formFields"
    :can-delete="true"
  />
</template>

<script setup>
import BaseListView from '@/components/BaseListView.vue'

const columns = [
  { prop: 'kind_name', label: '类型', width: 110 },
  { prop: 'title', label: '标题', minWidth: 160 },
  { prop: 'user_name', label: '员工', width: 100 },
  { prop: 'background', label: '背景', minWidth: 160 },
  { prop: 'process', label: '过程', minWidth: 160 },
  { prop: 'cause', label: '原因', minWidth: 140 },
  { prop: 'improvement', label: '改进措施', minWidth: 140 },
  { prop: 'action_plan', label: '行动计划', minWidth: 140 },
  { prop: 'created_at', label: '创建时间', width: 160 },
]

const formFields = [
  { prop: 'kind', label: '复盘类型', type: 'text', required: true },
  { prop: 'title', label: '标题', type: 'text', required: true },
  { prop: 'background', label: '背景', type: 'textarea' },
  { prop: 'process', label: '过程', type: 'textarea' },
  { prop: 'cause', label: '原因', type: 'textarea' },
  { prop: 'improvement', label: '改进措施', type: 'textarea' },
  { prop: 'action_plan', label: '行动计划', type: 'textarea' },
]
</script>
