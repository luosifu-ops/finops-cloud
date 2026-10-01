<template>
  <div class="dy">
    <el-alert v-if="data.is_demo" type="warning" :closable="false" show-icon title="当前为演示数据"
      description="在后端配置 DOUYIN_API_KEY 后显示真实对标数据（蝉妈妈 / 飞瓜等）。" style="margin-bottom:12px" />

    <div class="dy-search">
      <el-input v-model="q" placeholder="输入抖音号或昵称，如 财税老王" clearable style="width:320px" @keyup.enter="search" />
      <el-button type="primary" :loading="loading" @click="search">查 询</el-button>
      <el-button link type="primary" @click="openPortal('https://www.douyin.com')">前往抖音 ›</el-button>
    </div>

    <template v-if="data.nickname">
      <div class="dy-head">
        <div class="dy-avatar">{{ data.nickname.charAt(0) }}</div>
        <div>
          <h2 style="margin:0">{{ data.nickname }}</h2>
          <p class="sub">抖音号：{{ data.douyin_id }}</p>
        </div>
      </div>

      <el-row :gutter="16" class="dy-kpis">
        <el-col :span="4" v-for="k in kpis" :key="k.label">
          <el-card shadow="hover"><div class="kpi"><div class="num">{{ k.value }}</div><div class="lab">{{ k.label }}</div></div></el-card>
        </el-col>
      </el-row>

      <el-card style="margin-top:16px" header="人设标签">
        <el-tag v-for="t in (data.tags || [])" :key="t" style="margin-right:8px;margin-bottom:6px">{{ t }}</el-tag>
      </el-card>

      <el-card style="margin-top:16px" header="近期爆款视频">
        <el-table :data="data.hot_videos || []" border>
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="play" label="播放量" width="140" />
          <el-table-column prop="like" label="点赞量" width="140" />
        </el-table>
      </el-card>
    </template>
    <el-empty v-else description="输入账号查询抖音对标数据" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { integrationApi } from '@/api'

const q = ref('')
const loading = ref(false)
const data = ref({})

const fmt = (n) => (n || 0).toLocaleString('zh-CN')
const kpis = computed(() => [
  { label: '粉丝数', value: fmt(data.value.fans) },
  { label: '作品数', value: fmt(data.value.works) },
  { label: '获赞数', value: fmt(data.value.likes) },
  { label: '30天涨粉', value: fmt(data.value.growth_30d) },
  { label: '30天GMV', value: '¥' + fmt(data.value.gmv_30d) }
])

async function search() {
  if (!q.value.trim()) { ElMessage.warning('请输入抖音号或昵称'); return }
  loading.value = true
  try {
    const r = await integrationApi.douyinAccount({ q: q.value })
    data.value = r.data || {}
    if (!data.value.nickname) ElMessage.info('未找到（演示数据）')
  } catch (e) {} finally { loading.value = false }
}
function openPortal(u) { if (u) window.open(u, '_blank') }
onMounted(() => { q.value = '财税老王'; search() })
</script>

<style scoped>
.dy-search { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.dy-head { display: flex; align-items: center; gap: 14px; background: #fff; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.dy-avatar { width: 56px; height: 56px; border-radius: 50%; background: var(--primary); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 700; }
.dy-head .sub { color: var(--text-sub); margin: 6px 0 0; font-size: 13px; }
.dy-kpis { margin-bottom: 4px; }
.kpi { text-align: center; padding: 6px 0; }
.kpi .num { font-size: 22px; font-weight: 700; color: var(--primary); }
.kpi .lab { color: var(--text-sub); font-size: 12px; margin-top: 4px; }
</style>
