<template>
  <BaseListView title="转化漏斗" baseUrl="/ops/daily-stats/funnel/" read-only raw-array :can-delete="false"
    :columns="funnelColumns" />
</template>

<script setup>
import BaseListView from '@/components/BaseListView.vue'

// 转化漏斗字段已汉化：转化环节 / 数量 / 占展现比 / 较上一步转化（仅前端展示，不动接口与字段）
const funnelColumns = [
  { prop: 'name', label: '转化环节', minWidth: 140 },
  { prop: 'count', label: '数量', width: 120, align: 'right' },
  { prop: 'rate_from_top', label: '占展现比(%)', width: 150, align: 'right' },
  { prop: 'rate_from_prev', label: '较上一步转化(%)', width: 170, align: 'right' },
]
</script>
