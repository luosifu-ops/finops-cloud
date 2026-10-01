<template>
  <div class="page">
    <h2 class="page-title">合作政策</h2>
    <p class="text-muted" style="margin-top:-8px">财税企管云 · 城市合伙人与渠道招商合作政策</p>
    <el-timeline class="policy-tl">
      <el-timeline-item v-for="p in policies" :key="p.id" :timestamp="p.title" placement="top" :hollow="true">
        <el-card shadow="never" class="policy-card">
          <div class="policy-title">{{ p.title }}</div>
          <div class="policy-content">{{ p.content }}</div>
        </el-card>
      </el-timeline-item>
    </el-timeline>
    <el-empty v-if="!policies.length" description="暂无政策" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { investmentApi } from '@/api'
function unwrap(r) {
  if (!r) return []
  if (Array.isArray(r)) return r
  if (r.results) return r.results
  if (r.data && Array.isArray(r.data.results)) return r.data.results
  if (r.data && Array.isArray(r.data)) return r.data
  return []
}
const policies = ref([])
onMounted(async () => {
  try { policies.value = unwrap(await investmentApi.policies()).sort((a, b) => a.sort_order - b.sort_order) } catch (e) { policies.value = [] }
})
</script>

<style scoped>
.policy-tl { padding: 8px 4px; }
.policy-card { border-radius: 14px; }
.policy-title { font-size: 16px; font-weight: 700; color: var(--primary); margin-bottom: 8px; }
.policy-content { white-space: pre-wrap; line-height: 1.7; color: var(--text-main); font-size: 14px; }
</style>
