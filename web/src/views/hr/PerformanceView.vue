<template>
  <div>
    <el-tabs v-model="tab">
      <el-tab-pane label="绩效方案" name="plan" />
      <el-tab-pane label="绩效考核" name="review" />
    </el-tabs>
    <HrGenericView v-if="tab==='plan'" :key="'p'" title="绩效方案" baseUrl="/hr/performance-plans/"
      :columns="p.columns" :formFields="p.formFields" :depends="depends" />
    <HrGenericView v-else :key="'r'" title="绩效考核" baseUrl="/hr/performance-reviews/"
      :columns="r.columns" :formFields="r.formFields" :depends="depends" />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import HrGenericView from './HrGenericView.vue'
const tab = ref('plan')
const depends = { user: '/accounts/users/', department: '/accounts/departments/', plan: '/hr/performance-plans/' }
const p = {
  columns: [
    { prop: 'name', label: '方案名称', width: 160 },
    { prop: 'department_name', label: '适用部门', width: 140 },
    { prop: 'cycle_name', label: '周期', width: 100 },
    { prop: 'is_active', label: '启用', width: 80 },
  ],
  formFields: [
    { prop: 'name', label: '方案名称', type: 'text', required: true },
    { prop: 'department', label: '适用部门', type: 'select', depends: 'department' },
    { prop: 'cycle', label: '考核周期', type: 'select', options: [
      { value: 'MONTH', label: '月度' }, { value: 'QUARTER', label: '季度' }, { value: 'YEAR', label: '年度' } ] },
    { prop: 'template', label: '考核表(JSON/文本)', type: 'textarea' },
    { prop: 'is_active', label: '启用', type: 'switch' },
  ],
}
const r = {
  columns: [
    { prop: 'user_name', label: '被考核人', width: 110 },
    { prop: 'plan_name', label: '方案', width: 140 },
    { prop: 'period', label: '考核周期', width: 120 },
    { prop: 'reviewer_name', label: '考核人', width: 110 },
    { prop: 'score', label: '得分', width: 90 },
    { prop: 'grade', label: '等级', width: 90 },
    { prop: 'status_name', label: '状态', width: 100 },
  ],
  formFields: [
    { prop: 'user', label: '被考核人', type: 'select', depends: 'user', required: true },
    { prop: 'plan', label: '绩效方案', type: 'select', depends: 'plan' },
    { prop: 'reviewer', label: '考核人', type: 'select', depends: 'user' },
    { prop: 'period', label: '考核周期(如2026-Q3)', type: 'text', required: true },
    { prop: 'score', label: '综合得分', type: 'number' },
    { prop: 'grade', label: '等级', type: 'text' },
    { prop: 'result', label: '考核结果/评语', type: 'textarea' },
  ],
}
</script>
