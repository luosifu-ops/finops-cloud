<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">管理理念</h2>
      <el-tag type="success" effect="plain">我们如何管事、待人、成事</el-tag>
    </div>

    <el-empty v-if="!loading && !list.length" description="暂未发布管理理念内容" :image-size="90">
      <template #description>
        <div>暂未发布管理理念内容</div>
        <div class="empty-tip">内容由管理员在「文化内容管理」中维护（分类：管理理念）</div>
      </template>
    </el-empty>

    <el-row :gutter="16" v-else>
      <el-col :span="12" v-for="item in list" :key="item.id">
        <el-card shadow="never" class="manage-card">
          <div class="m-head">
            <el-tag size="small" effect="dark" type="primary">{{ item.title }}</el-tag>
          </div>
          <div class="m-content" v-html="item.content || '（暂无详述）'"></div>
          <div class="m-video" v-if="item.video_url">
            <a :href="item.video_url" target="_blank" rel="noopener">▶ 观看讲解视频</a>
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
    const r = await onboardingApi.cultures({ category: 'MANAGE' })
    list.value = parse(r)
  } catch (e) {} finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.manage-card { border-radius: 10px; margin-bottom: 16px; height: 100%; }
.m-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.m-content { font-size: 14px; line-height: 1.9; color: #1f2329; }
.m-content :deep(p) { margin: 0 0 6px; }
.m-content :deep(li) { margin: 2px 0; }
.m-video { margin-top: 12px; }
.m-video a { color: var(--primary); text-decoration: none; font-size: 13px; }
.empty-tip { font-size: 12px; color: var(--text-sub); margin-top: 6px; }
</style>
