<template>
  <div>
    <el-tabs v-model="tab">
      <el-tab-pane label="转正申请" name="regularization" />
      <el-tab-pane label="调岗调级" name="transfer" />
      <el-tab-pane label="离职交接" name="resign" />
    </el-tabs>
    <HrApprovableView v-if="tab==='regularization'" :key="'reg'" title="转正申请"
      baseUrl="/hr/regularizations/" :columns="reg.columns" :formFields="reg.formFields" :depends="depends" />
    <HrApprovableView v-else-if="tab==='transfer'" :key="'tr'" title="调岗调级"
      baseUrl="/hr/transfers/" :columns="tr.columns" :formFields="tr.formFields" :depends="depends" />
    <HrApprovableView v-else :key="'rs'" title="离职交接"
      baseUrl="/hr/resignations/" :columns="rs.columns" :formFields="rs.formFields" :depends="depends" />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import HrApprovableView from './HrApprovableView.vue'
const tab = ref('regularization')
const depends = {
  user: '/accounts/users/', department: '/accounts/departments/',
  position: '/accounts/positions/', 'job-level': '/hr/job-levels/',
}
const reg = {
  columns: [
    { prop: 'user_name', label: '申请人', width: 110 },
    { prop: 'probation_end', label: '试用期到期', width: 120 },
    { prop: 'apply_date', label: '申请日期', width: 120 },
    { prop: 'summary', label: '试用期总结', minWidth: 220 },
    { prop: 'status_name', label: '状态', width: 100 },
    { prop: 'approver_name', label: '审批人', width: 110 },
  ],
  formFields: [
    { prop: 'user', label: '申请人', type: 'select', depends: 'user', required: true },
    { prop: 'probation_end', label: '试用期到期', type: 'date' },
    { prop: 'apply_date', label: '申请日期', type: 'date' },
    { prop: 'summary', label: '试用期总结', type: 'textarea' },
  ],
}
const tr = {
  columns: [
    { prop: 'user_name', label: '员工', width: 110 },
    { prop: 'from_department_name', label: '原部门', width: 120 },
    { prop: 'to_department_name', label: '调入部门', width: 120 },
    { prop: 'from_position_name', label: '原岗位', width: 120 },
    { prop: 'to_position_name', label: '调入岗位', width: 120 },
    { prop: 'from_job_level_name', label: '原职级', width: 120 },
    { prop: 'to_job_level_name', label: '调入职级', width: 120 },
    { prop: 'reason', label: '异动原因', minWidth: 160 },
    { prop: 'status_name', label: '状态', width: 100 },
  ],
  formFields: [
    { prop: 'user', label: '员工', type: 'select', depends: 'user', required: true },
    { prop: 'from_department', label: '原部门', type: 'select', depends: 'department' },
    { prop: 'to_department', label: '调入部门', type: 'select', depends: 'department', required: true },
    { prop: 'from_position', label: '原岗位', type: 'select', depends: 'position' },
    { prop: 'to_position', label: '调入岗位', type: 'select', depends: 'position' },
    { prop: 'from_job_level', label: '原职级', type: 'select', depends: 'job-level' },
    { prop: 'to_job_level', label: '调入职级', type: 'select', depends: 'job-level' },
    { prop: 'reason', label: '异动原因', type: 'textarea' },
  ],
}
const rs = {
  columns: [
    { prop: 'user_name', label: '离职人', width: 110 },
    { prop: 'resign_date', label: '预计离职', width: 120 },
    { prop: 'reason_type', label: '离职原因', width: 120 },
    { prop: 'handover_to_name', label: '交接人', width: 110 },
    { prop: 'handover_items', label: '交接事项', minWidth: 200 },
    { prop: 'status_name', label: '状态', width: 100 },
  ],
  formFields: [
    { prop: 'user', label: '离职人', type: 'select', depends: 'user', required: true },
    { prop: 'resign_date', label: '预计离职', type: 'date' },
    { prop: 'reason_type', label: '离职原因', type: 'text' },
    { prop: 'reason', label: '离职说明', type: 'textarea' },
    { prop: 'handover_to', label: '交接人', type: 'select', depends: 'user' },
    { prop: 'handover_items', label: '交接事项', type: 'textarea' },
  ],
}
</script>
