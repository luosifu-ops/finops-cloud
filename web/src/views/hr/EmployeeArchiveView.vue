<template>
  <HrGenericView title="员工档案" baseUrl="/accounts/users/" :readOnly="true" :canDelete="false"
    :columns="columns" :searchFields="searchFields" :depends="depends" />
</template>
<script setup>
import HrGenericView from './HrGenericView.vue'
const columns = [
  { prop: 'employee_no', label: '工号', width: 110 },
  { prop: 'display_name', label: '姓名', width: 110 },
  { prop: 'department_name', label: '部门', width: 120 },
  { prop: 'position_name', label: '岗位', width: 120 },
  { prop: 'job_level_name', label: '职级序列', width: 130 },
  { prop: 'role_name', label: '角色', width: 100 },
  { prop: 'status_name', label: '在职状态', width: 100 },
  { prop: 'entry_date', label: '入职日期', width: 120 },
  { prop: 'probation_end', label: '试用期到期', width: 120 },
  { prop: 'phone', label: '手机号', width: 130 },
]
const searchFields = [
  { prop: 'department', label: '部门', type: 'select', depends: 'department' },
  { prop: 'status', label: '状态', type: 'select', options: [
    { value: 'PROBATION', label: '试用期' }, { value: 'REGULAR', label: '正式' },
    { value: 'INTERN', label: '实习' }, { value: 'RESIGNED', label: '已离职' } ] },
]
const depends = { department: '/accounts/departments/' }
</script>
