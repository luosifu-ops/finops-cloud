<template>
  <BaseListView
    title="工作周报"
    baseUrl="/reports/weekly-reports/"
    :columns="columns"
    :formFields="formFields"
    :can-delete="true"
  />
</template>

<script setup>
import BaseListView from '@/components/BaseListView.vue'

const columns = [
  { prop: 'year', label: '年份', width: 80 },
  { prop: 'week', label: '周次', width: 80 },
  { prop: 'user_name', label: '员工', width: 100 },
  { prop: 'start_date', label: '开始日期', width: 120 },
  { prop: 'end_date', label: '结束日期', width: 120 },
  { prop: 'summary', label: '本周总结', minWidth: 180 },
  { prop: 'data', label: '各项数据', minWidth: 160 },
  { prop: 'next_plan', label: '下周计划', minWidth: 160 },
  { prop: 'problems', label: '存在问题', minWidth: 140 },
  { prop: 'score', label: '评分', width: 80 },
]

const formFields = [
  { prop: 'year', label: '年份', type: 'number' },
  { prop: 'week', label: '周次', type: 'number' },
  { prop: 'start_date', label: '开始日期', type: 'date' },
  { prop: 'end_date', label: '结束日期', type: 'date' },
  { prop: 'summary', label: '本周总结', type: 'textarea' },
  { prop: 'data', label: '各项数据', type: 'textarea' },
  { prop: 'next_plan', label: '下周计划', type: 'textarea' },
  { prop: 'problems', label: '存在问题', type: 'textarea' },
]
</script>
