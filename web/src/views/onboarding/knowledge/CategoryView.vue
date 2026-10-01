<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">{{ title }}</h2>
      <el-tag type="success" effect="plain">学完标记为「已掌握」，进度自动累计</el-tag>
    </div>

    <el-card shadow="never" class="prog-card" v-if="list.length">
      <div class="prog-row">
        <span class="prog-label">本栏目学习进度</span>
        <span class="prog-num">{{ finishedCount }} / {{ totalCount }}</span>
      </div>
      <el-progress :percentage="percent" :stroke-width="14" striped />
    </el-card>

    <el-table :data="list" v-loading="loading" border stripe style="width:100%" @row-click="openDetail" class="kb-table">
      <el-table-column prop="title" label="文章标题" min-width="220" show-overflow-tooltip />
      <el-table-column label="难度" width="110" align="center">
        <template #default="{ row }">
          <el-tag :type="levelType(row.level)" size="small" effect="plain">{{ levelLabel(row.level) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="必修" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.is_required" type="danger" size="small">必修</el-tag>
          <span v-else class="muted">选学</span>
        </template>
      </el-table-column>
      <el-table-column prop="view_count" label="阅读量" width="90" align="center" />
      <el-table-column label="掌握" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="learnedSet.has(row.id) ? 'success' : 'info'" size="small" effect="dark">
            {{ learnedSet.has(row.id) ? '已学完' : '学习中' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !list.length" :description="emptyText" :image-size="90">
      <template #description>
        <div>{{ emptyText }}</div>
        <div class="empty-tip">该栏目内容由管理员在「知识库维护」中补充</div>
      </template>
    </el-empty>

    <el-drawer v-model="drawer" :title="current?.title" size="50%" @closed="current = null">
      <div v-if="current" v-loading="detailLoading">
        <div class="kb-tags">
          <el-tag :type="levelType(current.level)" size="small" effect="plain">{{ levelLabel(current.level) }}</el-tag>
          <el-tag v-if="current.is_required" type="danger" size="small">必修</el-tag>
          <el-tag v-for="t in tagList(current.tags)" :key="t" size="small" effect="plain">{{ t }}</el-tag>
        </div>
        <p class="kb-summary" v-if="current.summary">{{ current.summary }}</p>
        <div class="kb-content" v-html="current.content || '（暂无内容）'"></div>
        <div class="drawer-foot">
          <el-button
            v-if="!learnedSet.has(current.id)"
            type="primary" :loading="learning" @click="markLearn(current)"
          >标记学完</el-button>
          <el-tag v-else type="success" effect="dark">已完成学习 🎉</el-tag>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { onboardingApi } from '@/api'

const props = defineProps({
  category: { type: String, required: true },
  title: { type: String, default: '' },
})

// 学习状态本地持久化（localStorage）：course/作业/文章均按 id 记录“已学完”，
// 刷新、切换栏目、重新登录后状态保留；纯前端实现，不触碰后端字段与数据库。
const LS_KEY = 'kb_learned_ids_v1'
function loadLearned() {
  try {
    const arr = JSON.parse(localStorage.getItem(LS_KEY) || '[]')
    return new Set(Array.isArray(arr) ? arr : [])
  } catch { return new Set() }
}
function persistLearned(set) {
  try { localStorage.setItem(LS_KEY, JSON.stringify([...set])) } catch {}
}

const levelMap = {
  BASIC: { label: '入门', type: 'success' },
  MIDDLE: { label: '进阶', type: 'warning' },
  ADVANCED: { label: '高阶', type: 'danger' },
}
const levelLabel = (l) => (levelMap[l] ? levelMap[l].label : (l || '—'))
const levelType = (l) => (levelMap[l] ? levelMap[l].type : 'info')

const list = ref([])
const loading = ref(false)
const learnedSet = ref(loadLearned())
const drawer = ref(false)
const current = ref(null)
const detailLoading = ref(false)
const learning = ref(false)

const totalCount = computed(() => list.value.length)
const finishedCount = computed(() => list.value.filter(r => learnedSet.value.has(r.id)).length)
const percent = computed(() => { const t = totalCount.value; return t ? Math.round(finishedCount.value / t * 100) : 0 })

const emptyText = '暂无学习文章'

function tagList(tags) {
  if (!tags) return []
  if (Array.isArray(tags)) return tags
  return String(tags).split(/[,，]/).map(s => s.trim()).filter(Boolean)
}
function parseList(resp) {
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
    const r1 = await onboardingApi.articles({ category: props.category })
    list.value = parseList(r1)
    learnedSet.value = loadLearned() // 重新加载时同步最新本地记录
  } catch (e) {} finally { loading.value = false }
}

function openDetail(row) { current.value = row; drawer.value = true }

async function markLearn(row) {
  learning.value = true
  try {
    // 优先走后端学习记录（若已部署该接口），失败则降级为本地记录，保证状态必留存
    try { await onboardingApi.learn(row.id, { finished: true }) } catch {}
    const s = new Set(learnedSet.value)
    s.add(row.id)
    learnedSet.value = s
    persistLearned(s)
    ElMessage.success('已标记为学完')
  } finally { learning.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.prog-card { border-radius: 10px; margin-bottom: 14px; }
.prog-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.prog-label { font-weight: 600; font-size: 14px; }
.prog-num { font-size: 13px; color: var(--text-sub); }
.kb-table :deep(tbody tr) { cursor: pointer; }
.kb-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.kb-summary { font-size: 13px; color: #86909c; line-height: 1.7; margin: 0 0 14px; }
.kb-content { font-size: 14px; line-height: 1.9; color: #1f2329; white-space: pre-wrap; }
.kb-content :deep(p) { margin: 0 0 8px; }
.muted { color: var(--text-sub); font-size: 13px; }
.drawer-foot { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--border); }
.empty-tip { font-size: 12px; color: var(--text-sub); margin-top: 6px; }
</style>
