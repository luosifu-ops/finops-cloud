<template>
  <BaseListView title="团队汇报" baseUrl="/reports/daily-reports/team/" read-only raw-array :can-delete="false" />
</template>

<script setup>
import BaseListView from '@/components/BaseListView.vue'
</script>
