<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">员工故事</h2>
      <el-tag type="warning" effect="plain">在这里，看见彼此的成长</el-tag>
    </div>

    <el-empty v-if="!loading && !list.length" description="暂未发布员工故事" :image-size="90">
      <template #description>
        <div>暂未发布员工故事</div>
        <div class="empty-tip">内容由管理员在「文化内容管理」中维护（分类：员工故事）</div>
      </template>
    </el-empty>

    <el-row :gutter="16" v-else>
      <el-col :span="8" v-for="item in list" :key="item.id">
        <el-card shadow="never" class="story-card">
          <div class="s-title">{{ item.title }}</div>
          <div class="s-content" v-html="item.content || '（暂无内容）'"></div>
          <div class="s-foot" v-if="item.video_url">
            <a :href="item.video_url" target="_blank" rel="noopener">▶ 观看视频</a>
          </div>
        </el-card>
      </el-col>
    </el-row>
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
  if (p && p.results) return p.results || []
  if (Array.isArray(p)) return p
  return []
}

async function load() {
  loading.value = true
  try {
    const r = await onboardingApi.cultures({ category: 'STORY' })
    list.value = parse(r)
  } catch (e) {} finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.story-card { border-radius: 10px; margin-bottom: 16px; height: 100%; }
.s-title { font-size: 15px; font-weight: 700; margin-bottom: 10px; }
.s-content { font-size: 13px; line-height: 1.8; color: #4e5969; max-height: 220px; overflow: hidden; }
.s-content :deep(p) { margin: 0 0 6px; }
.s-foot { margin-top: 10px; }
.s-foot a { color: var(--primary); text-decoration: none; font-size: 13px; }
.empty-tip { font-size: 12px; color: var(--text-sub); margin-top: 6px; }
</style>
