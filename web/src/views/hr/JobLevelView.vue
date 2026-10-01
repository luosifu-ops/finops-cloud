<template>
  <HrGenericView title="岗位职级库" baseUrl="/hr/job-levels/"
    :columns="columns" :formFields="formFields" />
</template>
<script setup>
import HrGenericView from './HrGenericView.vue'
const columns = [
  { prop: 'name', label: '职级名称', width: 140 },
  { prop: 'sequence_name', label: '职级序列', width: 140 },
  { prop: 'level', label: '级别', width: 80 },
  { prop: 'description', label: '职级说明', minWidth: 220 },
]
const formFields = [
  { prop: 'name', label: '职级名称', type: 'text', required: true },
  { prop: 'sequence', label: '职级序列', type: 'select', options: [
    { value: 'MANAGE', label: '管理序列' }, { value: 'SALES', label: '销售序列' },
    { value: 'FINANCE', label: '财务会计序列' }, { value: 'OPS_HOST', label: '运营主播序列' },
    { value: 'SUPPORT', label: '职能支持序列' } ] },
  { prop: 'level', label: '级别', type: 'number' },
  { prop: 'description', label: '职级说明', type: 'textarea' },
]
</script>
