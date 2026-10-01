<template>
  <div>
    <el-tabs v-model="tab">
      <el-tab-pane label="通讯录可见权限" name="ab" />
      <el-tab-pane label="角色权限预设" name="rp" />
    </el-tabs>
    <HrGenericView v-if="tab==='ab'" :key="'ab'" title="通讯录可见权限" baseUrl="/hr/addressbook-visibility/"
      :columns="ab.columns" :formFields="ab.formFields" />
    <HrGenericView v-else :key="'rp'" title="角色权限预设" baseUrl="/hr/role-presets/"
      :columns="rp.columns" :formFields="rp.formFields" />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import HrGenericView from './HrGenericView.vue'
const tab = ref('ab')
const ab = {
  columns: [
    { prop: 'name', label: '规则名称', width: 160 },
    { prop: 'role_name', label: '适用角色', width: 120 },
    { prop: 'see_all', label: '可看全公司', width: 110 },
    { prop: 'see_self_dept', label: '仅看本部门', width: 110 },
  ],
  formFields: [
    { prop: 'name', label: '规则名称', type: 'text', required: true },
    { prop: 'role', label: '适用角色', type: 'select', options: [
      { value: 'BOSS', label: '老板/总经理' }, { value: 'MANAGER', label: '部门经理' },
      { value: 'LEADER', label: '组长/主管' }, { value: 'EMPLOYEE', label: '员工' },
      { value: 'HR', label: '人事行政' } ] },
    { prop: 'see_all', label: '可看全公司', type: 'switch' },
    { prop: 'see_self_dept', label: '仅看本部门', type: 'switch' },
  ],
}
const rp = {
  columns: [
    { prop: 'role_name', label: '角色', width: 140 },
    { prop: 'can_view_addressbook', label: '通讯录', width: 90 },
    { prop: 'can_view_archives', label: '人事档案', width: 100 },
    { prop: 'can_view_salary', label: '薪资', width: 80 },
    { prop: 'can_view_contract', label: '合同', width: 80 },
    { prop: 'can_view_performance', label: '绩效', width: 80 },
    { prop: 'can_manage_attendance', label: '考勤', width: 80 },
    { prop: 'can_approve', label: '审批', width: 80 },
  ],
  formFields: [
    { prop: 'role', label: '角色', type: 'select', options: [
      { value: 'SUPERADMIN', label: '超级管理员' }, { value: 'HR', label: '人事管理员' },
      { value: 'MANAGER', label: '部门主管' }, { value: 'EMPLOYEE', label: '普通员工' } ] },
    { prop: 'can_view_addressbook', label: '查看通讯录', type: 'switch' },
    { prop: 'can_view_archives', label: '查看人事档案', type: 'switch' },
    { prop: 'can_view_salary', label: '查看薪资', type: 'switch' },
    { prop: 'can_view_contract', label: '查看合同', type: 'switch' },
    { prop: 'can_view_performance', label: '查看绩效', type: 'switch' },
    { prop: 'can_manage_attendance', label: '管理考勤', type: 'switch' },
    { prop: 'can_approve', label: '发起/审批', type: 'switch' },
  ],
}
</script>
