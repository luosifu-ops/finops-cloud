<template>
  <BaseListView title="投放总览" baseUrl="/ops/daily-stats/summary/" read-only raw-array :can-delete="false" />
</template>

<script setup>
import BaseListView from '@/components/BaseListView.vue'
</script>
