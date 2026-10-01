<template>
  <div class="page">
    <h2 class="page-title">招商资料</h2>
    <el-tabs v-model="active" class="mat-tabs">
      <el-tab-pane v-for="c in categories" :key="c.value" :label="c.label" :name="c.value">
        <el-row :gutter="14">
          <el-col v-for="m in listOf(active)" :key="m.id" :xs="24" :sm="12" :md="8">
            <el-card shadow="hover" class="mat-card">
              <div class="mat-cat"><el-tag size="small">{{ m.category_display }}</el-tag></div>
              <div class="mat-title">{{ m.title }}</div>
              <div class="mat-sum">{{ m.summary }}</div>
              <el-button :disabled="!m.file_url || m.file_url === '#'" type="primary" link @click="open(m)">查看 / 下载</el-button>
            </el-card>
          </el-col>
        </el-row>
        <el-empty v-if="!listOf(active).length" description="该分类暂无资料" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { investmentApi } from '@/api'
const categories = [
  { value: 'MANUAL', label: '合作手册' },
  { value: 'MODEL', label: '收益模型' },
  { value: 'CASE', label: '成功案例' },
  { value: 'BRAND', label: '品牌素材' },
]
const active = ref('MANUAL')
const all = ref([])
function unwrap(r) {
  if (!r) return []
  if (Array.isArray(r)) return r
  if (r.results) return r.results
  if (r.data && Array.isArray(r.data.results)) return r.data.results
  if (r.data && Array.isArray(r.data)) return r.data
  return []
}
const listOf = (cat) => all.value.filter(m => m.category === cat)
const open = (m) => { if (m.file_url && m.file_url !== '#') window.open(m.file_url, '_blank') }
onMounted(async () => {
  try { all.value = unwrap(await investmentApi.materials()) } catch (e) { all.value = [] }
})
</script>

<style scoped>
.mat-card { border-radius: 14px; margin-bottom: 14px; min-height: 150px; }
.mat-cat { margin-bottom: 8px; }
.mat-title { font-size: 15px; font-weight: 700; margin-bottom: 6px; }
.mat-sum { font-size: 13px; color: var(--text-sub); line-height: 1.6; margin-bottom: 10px; min-height: 42px; }
</style>
