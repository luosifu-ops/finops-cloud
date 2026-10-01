<template>
  <div>
    <el-tabs v-model="tab">
      <el-tab-pane label="考勤组" name="group" />
      <el-tab-pane label="排班表" name="shift" />
      <el-tab-pane label="假期余额" name="balance" />
    </el-tabs>
    <HrGenericView v-if="tab==='group'" :key="'g'" title="考勤组" baseUrl="/hr/attendance-groups/"
      :columns="g.columns" :formFields="g.formFields" :depends="depends" />
    <HrGenericView v-else-if="tab==='shift'" :key="'s'" title="排班表" baseUrl="/hr/shifts/"
      :columns="s.columns" :formFields="s.formFields" :depends="depends" />
    <HrGenericView v-else :key="'b'" title="假期余额" baseUrl="/hr/leave-balances/"
      :columns="b.columns" :formFields="b.formFields" :depends="depends" />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import HrGenericView from './HrGenericView.vue'
const tab = ref('group')
const depends = { user: '/accounts/users/', rule: '/hr/attendance-rules/' }
const g = {
  columns: [
    { prop: 'name', label: '考勤组名称', width: 160 },
    { prop: 'department_names', label: '适用部门', minWidth: 200 },
    { prop: 'rule_name', label: '考勤规则', width: 140 },
    { prop: 'description', label: '说明', minWidth: 200 },
  ],
  formFields: [
    { prop: 'name', label: '考勤组名称', type: 'text', required: true },
    { prop: 'rule', label: '考勤规则', type: 'select', depends: 'rule' },
    { prop: 'description', label: '说明', type: 'textarea' },
  ],
}
const s = {
  columns: [
    { prop: 'user_name', label: '员工', width: 110 },
    { prop: 'date', label: '日期', width: 130 },
    { prop: 'shift_name', label: '班次', width: 120 },
    { prop: 'note', label: '备注', minWidth: 160 },
  ],
  formFields: [
    { prop: 'user', label: '员工', type: 'select', depends: 'user', required: true },
    { prop: 'date', label: '排班日期', type: 'date', required: true },
    { prop: 'shift', label: '班次', type: 'select', options: [
      { value: 'MORNING', label: '早班' }, { value: 'AFTERNOON', label: '午班' },
      { value: 'NIGHT', label: '晚班/夜班' }, { value: 'REST', label: '休息' } ] },
    { prop: 'note', label: '备注', type: 'text' },
  ],
}
const b = {
  columns: [
    { prop: 'user_name', label: '员工', width: 110 },
    { prop: 'year', label: '年份', width: 90 },
    { prop: 'annual_total', label: '年假总额', width: 110 },
    { prop: 'annual_used', label: '年假已用', width: 110 },
    { prop: 'personal_total', label: '事假额度', width: 110 },
    { prop: 'personal_used', label: '事假已用', width: 110 },
    { prop: 'compensate_total', label: '调休总额', width: 110 },
    { prop: 'compensate_used', label: '调休已用', width: 110 },
  ],
  formFields: [
    { prop: 'user', label: '员工', type: 'select', depends: 'user', required: true },
    { prop: 'year', label: '年份', type: 'number' },
    { prop: 'annual_total', label: '年假总额(天)', type: 'number' },
    { prop: 'personal_total', label: '事假额度(天)', type: 'number' },
    { prop: 'compensate_total', label: '调休总额(天)', type: 'number' },
  ],
}
</script>
