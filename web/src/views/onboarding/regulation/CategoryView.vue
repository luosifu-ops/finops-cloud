<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">{{ title }}</h2>
      <el-tag type="info" effect="plain">请认真阅读，要求已读的制度需点击确认</el-tag>
    </div>

    <el-table :data="list" v-loading="loading" border stripe style="width:100%" @row-click="openDetail" class="reg-table">
      <el-table-column prop="title" label="制度名称" min-width="200" show-overflow-tooltip />
      <el-table-column prop="version" label="版本号" width="110" />
      <el-table-column prop="effective_date" label="生效日期" width="130" />
      <el-table-column label="要求已读" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.must_read" type="danger" size="small" effect="plain">需确认</el-tag>
          <el-tag v-else size="small" effect="plain">选读</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="我的状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="readSet.has(row.id) ? 'success' : 'info'" size="small" effect="dark">
            {{ readSet.has(row.id) ? '已读' : '未读' }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !list.length" :description="emptyText" :image-size="90">
      <template #description>
        <div>{{ emptyText }}</div>
        <div class="empty-tip">制度内容由管理员在「制度维护」中发布</div>
      </template>
    </el-empty>

    <el-drawer v-model="drawer" :title="current?.title" size="46%" @closed="current = null">
      <div v-if="current" v-loading="detailLoading">
        <el-descriptions :column="2" size="small" border class="meta">
          <el-descriptions-item label="版本号">{{ current.version || '—' }}</el-descriptions-item>
          <el-descriptions-item label="生效日期">{{ current.effective_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="要求已读">
            {{ current.must_read ? '需要确认' : '选读' }}
          </el-descriptions-item>
          <el-descriptions-item label="我的状态">
            <el-tag :type="readSet.has(current.id) ? 'success' : 'info'" size="small">
              {{ readSet.has(current.id) ? '已读' : '未读' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div class="content" v-html="current.content || '（暂无正文）'"></div>
        <div class="drawer-foot">
          <el-button
            v-if="current.must_read && !readSet.has(current.id)"
            type="primary" :loading="acking" @click="ack(current)"
          >我已阅读并确认</el-button>
          <el-tag v-else-if="readSet.has(current.id)" type="success" effect="dark">你已确认阅读</el-tag>
          <span v-else class="opt-tip">本条为选读制度，无需确认</span>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { onboardingApi } from '@/api'

const props = defineProps({
  category: { type: String, required: true },
  title: { type: String, default: '' },
})

const list = ref([])
const loading = ref(false)
const readSet = ref(new Set())
const drawer = ref(false)
const current = ref(null)
const detailLoading = ref(false)
const acking = ref(false)

const emptyText = '暂无相关制度'

function parseList(resp) {
  const body = resp || {}
  let p = body
  if (body && typeof body === 'object' && !Array.isArray(body) && 'code' in body && 'data' in body) p = body.data
  if (p && p.results) return p.results || []
  if (Array.isArray(p)) return p
  return []
}
function parseAcks(resp) {
  const body = resp || {}
  let p = body
  if (body && typeof body === 'object' && !Array.isArray(body) && 'code' in body && 'data' in body) p = body.data
  const arr = Array.isArray(p) ? p : (p && Array.isArray(p.data) ? p.data : [])
  const s = new Set()
  arr.forEach(it => { const id = it.regulation ?? it.id; if (id != null) s.add(id) })
  return s
}

async function load() {
  loading.value = true
  try {
    const [r1, r2] = await Promise.all([
      onboardingApi.regulations({ category: props.category }),
      onboardingApi.myAcks(),
    ])
    list.value = parseList(r1)
    readSet.value = parseAcks(r2)
  } catch (e) {} finally { loading.value = false }
}

function openDetail(row) {
  current.value = row
  drawer.value = true
}

async function ack(row) {
  acking.value = true
  try {
    await onboardingApi.ack(row.id)
    readSet.value = new Set(readSet.value).add(row.id)
    ElMessage.success('已确认阅读')
  } catch (e) { ElMessage.error('确认失败，请重试') }
  finally { acking.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.reg-table :deep(tbody tr) { cursor: pointer; }
.meta { margin-bottom: 16px; }
.content { font-size: 14px; line-height: 1.9; color: #1f2329; white-space: pre-wrap; }
.content :deep(p) { margin: 0 0 8px; }
.drawer-foot { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--border); }
.opt-tip { font-size: 13px; color: var(--text-sub); }
.empty-tip { font-size: 12px; color: var(--text-sub); margin-top: 6px; }
</style>
