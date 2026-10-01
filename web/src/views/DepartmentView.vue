<template>
  <BaseListView :title="title" :base-url="baseUrl" read-only raw-array />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import BaseListView from '@/components/BaseListView.vue'

const route = useRoute()
const code = computed(() => route.params.code || 'SALES')
const title = computed(() => `${code.value} · 部门看板`)
const baseUrl = computed(() => `/dashboard/department/${code.value}/`)
</script>
