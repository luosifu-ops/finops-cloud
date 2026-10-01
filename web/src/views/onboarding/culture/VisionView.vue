<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">愿景 · 使命 · 价值观</h2>
      <el-tag type="success" effect="plain">我们因何存在，去向何方</el-tag>
    </div>

    <el-empty v-if="!loading && !list.length" description="暂未发布愿景使命价值观内容" :image-size="90">
      <template #description>
        <div>暂未发布愿景使命价值观内容</div>
        <div class="empty-tip">内容由管理员在「文化内容管理」中维护（分类：愿景与价值观）</div>
      </template>
    </el-empty>

    <el-row :gutter="16" v-else>
      <el-col :span="12" v-for="item in list" :key="item.id">
        <el-card shadow="never" class="vision-card">
          <div class="v-head">
            <el-tag size="small" effect="dark" :type="item.category === 'VALUE' ? 'warning' : 'primary'">
              {{ item.category === 'VALUE' ? '价值观' : '愿景使命' }}
            </el-tag>
            <span class="v-title">{{ item.title }}</span>
          </div>
          <div class="v-content" v-html="item.content || '（暂无详述）'"></div>
          <div class="v-video" v-if="item.video_url">
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
    const r = await onboardingApi.cultures({ category: 'VISION' })
    list.value = parse(r)
  } catch (e) {} finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.vision-card { border-radius: 10px; margin-bottom: 16px; height: 100%; }
.v-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.v-title { font-size: 16px; font-weight: 700; }
.v-content { font-size: 14px; line-height: 1.9; color: #1f2329; }
.v-content :deep(p) { margin: 0 0 6px; }
.v-video { margin-top: 12px; }
.v-video a { color: var(--primary); text-decoration: none; font-size: 13px; }
.empty-tip { font-size: 12px; color: var(--text-sub); margin-top: 6px; }
</style>
