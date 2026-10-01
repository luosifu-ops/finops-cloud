<template>
  <div class="anchor">
    <!-- 统计卡片 -->
    <el-row :gutter="14" class="anchor-kpis">
      <el-col :span="6" v-for="k in stats" :key="k.label">
        <el-card shadow="hover">
          <div class="kpi"><div class="num">{{ k.value }}</div><div class="lab">{{ k.label }}</div></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="14" class="anchor-main">
      <!-- 主播列表（复用 BaseListView：原样迁移） -->
      <el-col :span="17">
        <BaseListView
          title="主播管理"
          base-url="/sales/streamers/"
          :columns="columns"
          :form-fields="formFields"
          :search-fields="searchFields"
        />
      </el-col>

      <!-- 本月 GMV 排行 -->
      <el-col :span="7">
        <el-card shadow="never" header="本月 GMV 排行">
          <div v-for="(a, i) in rank" :key="a.id || a.name" class="rank-item">
            <span class="rank-no" :class="{ top: i < 3 }">{{ i + 1 }}</span>
            <span class="rank-name">{{ a.name }}</span>
            <span class="rank-gmv">¥{{ fmt(a.gmv) }}</span>
          </div>
          <el-empty v-if="!rank.length" description="暂无数据" :image-size="70" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import { orgApi, salesApi } from '@/api'

const deptOptions = ref([])
const userOptions = ref([])
const all = ref([])

const columns = [
  { prop: 'name', label: '主播昵称', width: 120 },
  { prop: 'platform_name', label: '平台', width: 80 },
  { prop: 'account', label: '账号/主页ID', minWidth: 130 },
  { prop: 'department_name', label: '所属部门', width: 90 },
  { prop: 'manager_name', label: '负责人', width: 90 },
  { prop: 'status_name', label: '状态', width: 80 },
  { prop: 'fans_count', label: '粉丝数', width: 90, align: 'right' },
  { prop: 'live_count', label: '本月开播', width: 90, align: 'right' },
  { prop: 'gmv', label: '本月GMV', width: 110, align: 'right' },
  { prop: 'commission_rate', label: '提成%', width: 80, align: 'right' },
]

const searchFields = [
  { prop: 'platform', label: '平台', type: 'select', options: [
    { value: 'DOUYIN', label: '抖音' }, { value: 'KUAISHOU', label: '快手' },
    { value: 'VIDEO', label: '视频号' }, { value: 'RED', label: '小红书' }, { value: 'OTHER', label: '其他' },
  ] },
  { prop: 'status', label: '状态', type: 'select', options: [
    { value: 'ACTIVE', label: '开播中' }, { value: 'INACTIVE', label: '停播' }, { value: 'RESIGNED', label: '已离职' },
  ] },
]

const formFields = ref([
  { prop: 'name', label: '主播昵称', type: 'text', required: true },
  { prop: 'platform', label: '平台', type: 'select', required: true, options: [
    { value: 'DOUYIN', label: '抖音' }, { value: 'KUAISHOU', label: '快手' },
    { value: 'VIDEO', label: '视频号' }, { value: 'RED', label: '小红书' }, { value: 'OTHER', label: '其他' },
  ] },
  { prop: 'account', label: '账号/主页ID', type: 'text' },
  { prop: 'phone', label: '联系电话', type: 'text' },
  { prop: 'department', label: '所属部门', type: 'select', options: [] },
  { prop: 'manager', label: '负责人', type: 'select', options: [] },
  { prop: 'status', label: '状态', type: 'select', options: [
    { value: 'ACTIVE', label: '开播中' }, { value: 'INACTIVE', label: '停播' }, { value: 'RESIGNED', label: '已离职' },
  ] },
  { prop: 'entry_date', label: '入职日期', type: 'date' },
  { prop: 'fans_count', label: '粉丝数', type: 'number' },
  { prop: 'live_count', label: '本月开播场次', type: 'number' },
  { prop: 'gmv', label: '本月GMV(元)', type: 'number' },
  { prop: 'commission_rate', label: '提成比例(%)', type: 'number' },
  { prop: 'remark', label: '备注', type: 'textarea' },
])

const fmt = (n) => (n || 0).toLocaleString('zh-CN')

function unwrap(resp) {
  if (!resp) return []
  if (Array.isArray(resp)) return resp
  if (resp.results) return resp.results
  if (resp.data && Array.isArray(resp.data.results)) return resp.data.results
  if (resp.data && Array.isArray(resp.data.list)) return resp.data.list
  if (resp.data && Array.isArray(resp.data)) return resp.data
  if (resp.list) return resp.list
  return resp.data ? [resp.data] : []
}

const stats = computed(() => {
  const arr = all.value
  const totalGmv = arr.reduce((s, x) => s + (Number(x.gmv) || 0), 0)
  const totalFans = arr.reduce((s, x) => s + (Number(x.fans_count) || 0), 0)
  const liveCount = arr.filter(x => x.status === 'ACTIVE').length
  return [
    { label: '主播总数', value: arr.length },
    { label: '在播人数', value: liveCount },
    { label: '本月总GMV', value: '¥' + fmt(totalGmv) },
    { label: '总粉丝数', value: fmt(totalFans) },
  ]
})

const rank = computed(() =>
  [...all.value].sort((a, b) => (Number(b.gmv) || 0) - (Number(a.gmv) || 0)).slice(0, 8)
)

async function loadAll() {
  try {
    const r = await salesApi.streamers({ page_size: 500 })
    all.value = unwrap(r)
  } catch (e) {
    all.value = []
  }
}

onMounted(async () => {
  const [d, u] = await Promise.all([
    orgApi.departments({ page_size: 50 }).catch(() => ({ results: [] })),
    orgApi.users({ page_size: 300 }).catch(() => ({ results: [] })),
  ])
  const depts = d.results || d.data || []
  const users = u.results || u.data || []
  const deptOpts = depts.map(x => ({ value: x.id, label: x.name }))
  const userOpts = users.map(x => ({ value: x.id, label: x.name || x.first_name || x.username }))
  formFields.value = formFields.value.map(f => {
    if (f.prop === 'department') return { ...f, options: deptOpts }
    if (f.prop === 'manager') return { ...f, options: userOpts }
    return f
  })
  loadAll()
})
</script>

<style scoped>
.anchor-kpis { margin-bottom: 14px; }
.kpi { text-align: center; padding: 4px 0; }
.kpi .num { font-size: 22px; font-weight: 700; color: var(--primary); }
.kpi .lab { color: var(--text-sub); font-size: 12px; margin-top: 4px; }
.anchor-main { align-items: flex-start; }
.rank-item { display: flex; align-items: center; gap: 10px; padding: 9px 4px; border-bottom: 1px solid var(--border); }
.rank-no { width: 22px; height: 22px; line-height: 22px; text-align: center; border-radius: 50%; background: var(--border); color: var(--text-sub); font-size: 12px; }
.rank-no.top { background: var(--primary); color: #fff; }
.rank-name { flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-gmv { font-weight: 600; color: var(--primary); }
</style>
