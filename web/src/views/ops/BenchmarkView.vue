<template>
  <div class="bm">
    <!-- 搜索区 -->
    <el-card class="bm-search" shadow="never">
      <el-input
        v-model="q"
        placeholder="输入账号昵称 / ID / 领域标签，如 财税老王"
        clearable
        style="width:300px"
        @keyup.enter="search"
      />
      <el-radio-group v-model="platform" style="margin:0 12px">
        <el-radio-button
          v-for="p in platformOptions"
          :key="p.value"
          :value="p.value"
        >{{ p.label }}</el-radio-button>
      </el-radio-group>
      <el-select v-model="sort" placeholder="排序维度" style="width:130px">
        <el-option label="粉丝数" value="fans" />
        <el-option label="点赞数" value="likes" />
        <el-option label="作品数" value="works" />
        <el-option label="平均播放" value="avg_play" />
      </el-select>
      <el-select v-model="fansLevel" placeholder="粉丝量级" clearable style="width:130px;margin-left:10px">
        <el-option label="不限量级" value="" />
        <el-option label="< 1万" value="lt1" />
        <el-option label="1-10万" value="1to10" />
        <el-option label="10-50万" value="10to50" />
        <el-option label="50万+" value="gt50" />
      </el-select>
      <el-switch
        v-model="onlyDk"
        active-text="仅看抖音快手"
        style="margin-left:14px"
        @change="() => {}"
      />
      <el-button type="primary" :loading="loading" style="margin-left:14px" @click="search">查 询</el-button>
      <el-button :disabled="!list.length" @click="exportCsv">导出 CSV</el-button>
      <el-button type="success" plain @click="openCreate">+ 录入对标账号</el-button>
      <el-tag v-if="source === 'library'" type="success" size="small" style="margin-left:10px">对标账号库</el-tag>
      <el-tag v-else-if="source === 'demo'" type="info" size="small" style="margin-left:10px">演示样本（库内暂无匹配，欢迎录入真实对标账号）</el-tag>
    </el-card>

    <!-- 录入/编辑对标账号 -->
    <el-dialog v-model="createVisible" :title="editingId ? '编辑对标账号' : '录入对标账号'" width="560px">
      <el-form :model="bform" label-width="100px">
        <el-form-item label="平台" required>
          <el-select v-model="bform.platform" style="width:100%">
            <el-option v-for="p in platformOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号昵称" required>
          <el-input v-model="bform.nickname" placeholder="对标账号昵称" />
        </el-form-item>
        <el-form-item label="账号ID">
          <el-input v-model="bform.account_id" placeholder="抖音号 / 账号ID" />
        </el-form-item>
        <el-form-item label="数据概况">
          <el-input-number v-model="bform.fans" :min="0" controls-position="right" placeholder="粉丝" style="width:120px" />
          <el-input-number v-model="bform.likes" :min="0" controls-position="right" placeholder="点赞" style="width:120px;margin-left:6px" />
          <el-input-number v-model="bform.works" :min="0" controls-position="right" placeholder="作品" style="width:110px;margin-left:6px" />
          <el-input-number v-model="bform.avg_play" :min="0" controls-position="right" placeholder="均播" style="width:120px;margin-left:6px" />
        </el-form-item>
        <el-form-item label="领域标签">
          <el-input v-model="bform.tags" placeholder="多个标签用英文逗号分隔，如 财税,代账,创业" />
        </el-form-item>
        <el-form-item label="简介/签名">
          <el-input v-model="bform.sign" type="textarea" :rows="2" placeholder="账号简介或签名" />
        </el-form-item>
        <el-form-item label="主页链接">
          <el-input v-model="bform.url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="bform.note" placeholder="选填，如：内容风格值得借鉴" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">{{ editingId ? '保存修改' : '提交入库' }}</el-button>
      </template>
    </el-dialog>

    <!-- 结果区 -->
    <el-table
      v-loading="loading"
      :data="pageList"
      border
      stripe
      class="bm-table"
      empty-text="输入关键词查询多平台对标账号"
      @row-click="openDetail"
    >
      <el-table-column label="平台" width="100">
        <template #default="{ row }">
          <el-tag :style="platformTagStyle(row.platform)" effect="dark" size="small">{{ row.platform_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="nickname" label="账号昵称" min-width="140" show-overflow-tooltip />
      <el-table-column prop="account_id" label="账号ID" min-width="130" show-overflow-tooltip />
      <el-table-column label="粉丝数" width="110" align="right">
        <template #default="{ row }">{{ fmt(row.fans) }}</template>
      </el-table-column>
      <el-table-column label="点赞数" width="110" align="right">
        <template #default="{ row }">{{ fmt(row.likes) }}</template>
      </el-table-column>
      <el-table-column label="作品数" width="90" align="right">
        <template #default="{ row }">{{ fmt(row.works) }}</template>
      </el-table-column>
      <el-table-column label="平均播放" width="110" align="right">
        <template #default="{ row }">{{ fmt(row.avg_play) }}</template>
      </el-table-column>
      <el-table-column label="领域标签" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <el-tag v-for="t in (row.tags || [])" :key="t" size="small" type="info" style="margin-right:6px">{{ t }}</el-tag>
          <span v-if="!row.tags || !row.tags.length" class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="openDetail(row)">详情</el-button>
          <template v-if="row.is_library">
            <el-button link type="warning" @click.stop="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click.stop="removeAccount(row)">删除</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <div class="bm-pager" v-if="filteredList.length">
      <span class="muted">共 {{ filteredList.length }} 个账号</span>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawer" :title="current.nickname || '账号详情'" size="460px">
      <template v-if="current.id">
        <div class="bm-detail-head">
          <el-tag :style="platformTagStyle(current.platform)" effect="dark">{{ current.platform_label }}</el-tag>
          <span class="bm-sign">{{ current.sign || '暂无简介' }}</span>
        </div>
        <el-descriptions :column="2" border style="margin-top:12px">
          <el-descriptions-item label="账号ID">{{ current.account_id }}</el-descriptions-item>
          <el-descriptions-item label="粉丝数">{{ fmt(current.fans) }}</el-descriptions-item>
          <el-descriptions-item label="点赞数">{{ fmt(current.likes) }}</el-descriptions-item>
          <el-descriptions-item label="作品数">{{ fmt(current.works) }}</el-descriptions-item>
          <el-descriptions-item label="平均播放">{{ fmt(current.avg_play) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ current.updated_at || '—' }}</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top:14px">
          <span class="bm-label">领域标签：</span>
          <el-tag v-for="t in (current.tags || [])" :key="t" size="small" type="info" style="margin-right:6px">{{ t }}</el-tag>
        </div>

        <el-divider content-position="left">近 7 天作品表现</el-divider>
        <el-table v-if="trend.length" :data="trend" border size="small">
          <el-table-column prop="date" label="日期" width="110" />
          <el-table-column prop="play" label="播放" align="right" />
          <el-table-column prop="like" label="点赞" align="right" />
        </el-table>
        <el-empty v-else description="暂无趋势数据" :image-size="80" />

        <el-button type="primary" plain style="margin-top:14px" @click="openPortal(current.url)">前往主页 ›</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { integrationApi } from '@/api'

const PLATFORM_FALLBACK = [
  { value: 'ALL', label: '全部' },
  { value: 'DOUYIN', label: '抖音' },
  { value: 'KUAISHOU', label: '快手' },
  { value: 'XIAOHONGSHU', label: '小红书' },
  { value: 'SHIPINHAO', label: '视频号' },
]
// 平台配色：抖音黑 / 快手橙 / 小红书红 / 视频号绿
const PLATFORM_COLOR = {
  DOUYIN: { color: '#fff', bg: '#161823' },
  KUAISHOU: { color: '#fff', bg: '#FF6600' },
  XIAOHONGSHU: { color: '#fff', bg: '#FF2442' },
  SHIPINHAO: { color: '#fff', bg: '#07C160' },
}

const q = ref('')
const platform = ref('ALL')
const sort = ref('fans')
const fansLevel = ref('')
const onlyDk = ref(false)
const loading = ref(false)
const list = ref([])
const source = ref('')
const platformOptions = ref(PLATFORM_FALLBACK)
const drawer = ref(false)
const current = ref({})
const trend = ref([])

const fmt = (n) => (n || 0).toLocaleString('zh-CN')

function platformTagStyle(p) {
  const c = PLATFORM_COLOR[p] || { color: '#fff', bg: '#909399' }
  return { color: c.color, backgroundColor: c.bg, borderColor: c.bg }
}

// 兼容 {code,data} / {count,results} / 裸数组 / {data:{list,total}}
function unwrap(resp) {
  if (!resp) return { list: [], total: 0, source: '' }
  if (Array.isArray(resp)) return { list: resp, total: resp.length, source: '' }
  if (resp.data && Array.isArray(resp.data.list)) {
    return { list: resp.data.list, total: resp.data.total ?? resp.data.list.length, source: resp.data.source || '' }
  }
  if (resp.data && Array.isArray(resp.data.results)) {
    return { list: resp.data.results, total: resp.data.count ?? resp.data.results.length, source: '' }
  }
  if (Array.isArray(resp.results)) return { list: resp.results, total: resp.count ?? resp.results.length, source: '' }
  if (Array.isArray(resp.data)) return { list: resp.data, total: resp.data.length, source: '' }
  if (resp.data && typeof resp.data === 'object') return { list: [resp.data], total: 1, source: '' }
  return { list: [], total: 0, source: '' }
}

const filteredList = computed(() => {
  let arr = list.value
  if (onlyDk.value) arr = arr.filter(x => ['DOUYIN', 'KUAISHOU'].includes(x.platform))
  if (fansLevel.value) {
    arr = arr.filter(x => {
      const f = x.fans || 0
      if (fansLevel.value === 'lt1') return f < 10000
      if (fansLevel.value === '1to10') return f >= 10000 && f < 100000
      if (fansLevel.value === '10to50') return f >= 100000 && f < 500000
      if (fansLevel.value === 'gt50') return f >= 500000
      return true
    })
  }
  return arr
})
const pageList = computed(() => filteredList.value.slice(0, 100))

async function search() {
  if (!q.value.trim()) { ElMessage.warning('请输入账号昵称 / ID / 领域标签'); return }
  loading.value = true
  try {
    const r = await integrationApi.benchmarkSearch({ q: q.value.trim(), platform: platform.value, sort: sort.value })
    const u = unwrap(r)
    list.value = u.list
    source.value = u.source
    if (!list.value.length) ElMessage.info('未找到匹配账号')
  } catch (e) {
    list.value = []
  } finally {
    loading.value = false
  }
}

function openDetail(row) {
  current.value = row
  trend.value = Array.isArray(row.trend) ? row.trend : []
  drawer.value = true
}

// ==================== 对标账号库：录入 / 编辑 / 删除（2026-11-02） ====================
const createVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)
const bform = ref({ platform: 'DOUYIN', nickname: '', account_id: '', fans: 0, likes: 0, works: 0, avg_play: 0, tags: '', sign: '', url: '', note: '' })

function openCreate() {
  editingId.value = null
  bform.value = { platform: platform.value === 'ALL' ? 'DOUYIN' : platform.value, nickname: '', account_id: '', fans: 0, likes: 0, works: 0, avg_play: 0, tags: q.value || '', sign: '', url: '', note: '' }
  createVisible.value = true
}

function openEdit(row) {
  editingId.value = row.id
  bform.value = {
    platform: row.platform || 'DOUYIN', nickname: row.nickname || '', account_id: row.account_id || '',
    fans: Number(row.fans || 0), likes: Number(row.likes || 0), works: Number(row.works || 0),
    avg_play: Number(row.avg_play || 0), tags: Array.isArray(row.tags) ? row.tags.join(',') : (row.tags || ''),
    sign: row.sign || '', url: row.url || '', note: row.note || '',
  }
  createVisible.value = true
}

async function submitCreate() {
  if (!String(bform.value.nickname || '').trim()) return ElMessage.warning('请填写账号昵称')
  saving.value = true
  try {
    const payload = { ...bform.value }
    if (editingId.value) {
      await integrationApi.updateBenchmarkAccount(editingId.value, payload)
      ElMessage.success('已保存修改')
    } else {
      await integrationApi.createBenchmarkAccount(payload)
      ElMessage.success('已入库，全员可检索')
    }
    createVisible.value = false
    search()
  } catch (e) { /* 拦截器已提示 */ } finally { saving.value = false }
}

async function removeAccount(row) {
  try {
    await ElMessageBox.confirm(`确认删除对标账号「${row.nickname}」？`, '删除确认', {
      type: 'warning', confirmButtonText: '确认删除', confirmButtonClass: 'el-button--danger',
    })
  } catch { return }
  try {
    await integrationApi.deleteBenchmarkAccount(row.id)
    ElMessage.success('已删除')
    search()
  } catch (e) { /* 拦截器已提示 */ }
}

function openPortal(url) { if (url) window.open(url, '_blank') }

function exportCsv() {
  const rows = filteredList.value
  if (!rows.length) return
  const head = ['平台', '昵称', '账号ID', '粉丝数', '点赞数', '作品数', '平均播放', '标签']
  const lines = [head.join(',')]
  rows.forEach(x => {
    const cells = [
      x.platform_label, x.nickname, x.account_id,
      x.fans || 0, x.likes || 0, x.works || 0, x.avg_play || 0,
      (x.tags || []).join('/'),
    ].map(c => `"${String(c).replace(/"/g, '""')}"`)
    lines.push(cells.join(','))
  })
  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `对标账号_${q.value || 'search'}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
  ElMessage.success('已导出当前结果')
}

async function loadPlatforms() {
  try {
    const r = await integrationApi.benchmarkPlatforms()
    const data = r?.data || r?.results || []
    if (Array.isArray(data) && data.length) {
      platformOptions.value = [{ value: 'ALL', label: '全部' }, ...data]
    }
  } catch (e) {
    platformOptions.value = PLATFORM_FALLBACK
  }
}

onMounted(loadPlatforms)
</script>

<style scoped>
.bm-search { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.bm-table { cursor: pointer; }
.bm-pager { margin-top: 12px; display: flex; justify-content: flex-end; }
.muted { color: var(--text-sub); font-size: 13px; }
.bm-detail-head { display: flex; flex-direction: column; gap: 8px; }
.bm-sign { color: var(--text-sub); font-size: 13px; }
.bm-label { font-size: 13px; color: var(--text-sub); }
</style>
