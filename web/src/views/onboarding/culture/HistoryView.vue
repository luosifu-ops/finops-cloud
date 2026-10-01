<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">发展历程</h2>
      <el-tag type="info" effect="plain">每一步，都是成长的脚印</el-tag>
    </div>

    <el-empty v-if="!loading && !list.length" description="暂未发布发展历程" :image-size="90">
      <template #description>
        <div>暂未发布发展历程</div>
        <div class="empty-tip">内容由管理员在「文化内容管理」中维护（分类：发展历程）</div>
      </template>
    </el-empty>

    <el-card shadow="never" class="timeline-card" v-else>
      <el-timeline>
        <el-timeline-item
          v-for="item in list"
          :key="item.id"
          :timestamp="item.title"
          placement="top"
          :color="item.sort % 2 === 0 ? '#409eff' : '#67c23a'"
        >
          <el-card shadow="hover" class="tl-inner">
            <div class="tl-content" v-html="item.content || '（暂无详述）'"></div>
            <div class="tl-video" v-if="item.video_url">
              <a :href="item.video_url" target="_blank" rel="noopener">▶ 相关影像</a>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { onboardingApi } from '@/api'

const list = ref([])
const loading = ref(false)

function parse(resp) {
  const body = resp || {}
  let p = body
  if (body && typeof body === 'object' && !Array.isArray(body) && 'code' in body && 'data' in body) p = body.data
  if (p && p.results) return (p.results || []).slice().sort((a, b) => (a.sort || 0) - (b.sort || 0))
  if (Array.isArray(p)) return p.slice().sort((a, b) => (a.sort || 0) - (b.sort || 0))
  return []
}

async function load() {
  loading.value = true
  try {
    const r = await onboardingApi.cultures({ category: 'HISTORY' })
    list.value = parse(r)
  } catch (e) {} finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.timeline-card { border-radius: 10px; }
.tl-inner { border-radius: 8px; }
.tl-content { font-size: 14px; line-height: 1.9; color: #1f2329; }
.tl-content :deep(p) { margin: 0 0 6px; }
.tl-video { margin-top: 8px; }
.tl-video a { color: var(--primary); text-decoration: none; font-size: 13px; }
.empty-tip { font-size: 12px; color: var(--text-sub); margin-top: 6px; }
</style>
