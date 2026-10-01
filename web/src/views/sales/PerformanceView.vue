<template>
  <BaseListView title="业绩排行" baseUrl="/sales/contracts/performance/" read-only raw-array :can-delete="false" />
</template>

<script setup>
import BaseListView from '@/components/BaseListView.vue'
</script>
