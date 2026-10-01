<template>
  <BaseListView
    title="工作月报"
    baseUrl="/reports/monthly-reports/"
    :columns="columns"
    :formFields="formFields"
    :can-delete="true"
  />
</template>

<script setup>
import BaseListView from '@/components/BaseListView.vue'

const columns = [
  { prop: 'month', label: '月份', width: 100 },
  { prop: 'user_name', label: '员工', width: 100 },
  { prop: 'summary', label: '本月总结', minWidth: 180 },
  { prop: 'data', label: '各项数据', minWidth: 160 },
  { prop: 'performance', label: '业绩情况', minWidth: 140 },
  { prop: 'target', label: '下月目标', minWidth: 140 },
  { prop: 'next_plan', label: '下月计划', minWidth: 140 },
  { prop: 'self_review', label: '自我复盘', minWidth: 140 },
  { prop: 'score', label: '评分', width: 80 },
]

const formFields = [
  { prop: 'month', label: '月份(YYYY-MM)', type: 'text', required: true },
  { prop: 'summary', label: '本月总结', type: 'textarea' },
  { prop: 'data', label: '各项数据', type: 'textarea' },
  { prop: 'performance', label: '业绩情况', type: 'textarea' },
  { prop: 'target', label: '下月目标', type: 'textarea' },
  { prop: 'next_plan', label: '下月计划', type: 'textarea' },
  { prop: 'self_review', label: '自我复盘', type: 'textarea' },
]
</script>
