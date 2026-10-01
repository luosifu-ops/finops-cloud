<template>
  <HrGenericView title="档案变更日志" baseUrl="/hr/change-logs/" :readOnly="true" :canDelete="false"
    :columns="columns" :searchFields="searchFields" :depends="depends" />
</template>
<script setup>
import HrGenericView from './HrGenericView.vue'
const columns = [
  { prop: 'user_name', label: '员工', width: 110 },
  { prop: 'action_name', label: '操作', width: 100 },
  { prop: 'field', label: '字段', width: 130 },
  { prop: 'old_value', label: '原值', minWidth: 160, showOverflowTooltip: true },
  { prop: 'new_value', label: '新值', minWidth: 160, showOverflowTooltip: true },
  { prop: 'operator_name', label: '操作人', width: 110 },
  { prop: 'created_at', label: '时间', width: 160 },
]
const searchFields = [
  { prop: 'user', label: '员工', type: 'select', depends: 'user' },
]
const depends = { user: '/accounts/users/' }
</script>
