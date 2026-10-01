<template>
  <div class="growth-page">
    <!-- 顶部指标 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">待领取（公海）</div>
          <div class="mini-value warn">{{ waiting }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">已领取</div>
          <div class="mini-value ok">{{ claimed }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">退回次数总计</div>
          <div class="mini-value">{{ totalReturnCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">我的角色</div>
          <div class="mini-value small">{{ roleLabel }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="main-card">
      <template #header>
        <div class="card-header">
          <span>公海 · 待领取 / 已领取 线索池</span>
          <div>
            <el-radio-group v-model="statusFilter" @change="loadData">
              <el-radio-button label="WAITING">待领取</el-radio-button>
              <el-radio-button label="CLAIMED">已领取</el-radio-button>
              <el-radio-button label="">全部</el-radio-button>
            </el-radio-group>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" size="default" class="filter-bar">
        <el-form-item label="平台">
          <el-select v-model="filters.channel" placeholder="全部" clearable style="width:140px">
            <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" plain @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="list" v-loading="loading" border stripe size="default">
        <el-table-column prop="lead_name" label="客户" min-width="120" />
        <el-table-column prop="lead_phone" label="电话" width="130" />
        <el-table-column label="来源平台" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ row.channel_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'WAITING' ? 'warning' : 'success'">
              {{ row.status_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="returned_by_name" label="退回人" width="100" />
        <el-table-column label="退回原因" min-width="160">
          <template #default="{ row }">
            <span v-if="row.returned_reason">{{ row.returned_reason }}</span>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="领取次数" width="90">
          <template #default="{ row }">{{ row.claim_count || 0 }}</template>
        </el-table-column>
        <el-table-column prop="claimed_by_name" label="领取人" width="100" />
        <el-table-column label="退回时间" width="160">
          <template #default="{ row }">
            <span class="muted">{{ fmt(row.returned_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'WAITING' && canClaim" link type="primary" @click="doClaim(row)">领取</el-button>
            <el-button v-if="canViewAll" link @click="openClaimedBy(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && !list.length" description="暂无数据" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { growthApi } from '@/api/growth'

const list = ref([])
const channels = ref([])
const loading = ref(false)
const statusFilter = ref('WAITING')
const roleLabel = ref('未配置')
const canClaim = ref(false)
const canViewAll = ref(false)

const filters = reactive({ channel: '' })

const waiting = computed(() => list.value.filter(r => r.status === 'WAITING').length)
const claimed = computed(() => list.value.filter(r => r.status === 'CLAIMED').length)
const totalReturnCount = computed(() => list.value.reduce((s, r) => s + (r.claim_count || 0), 0))

function fmt(t) { return t ? String(t).slice(0, 19).replace('T', ' ') : '' }

async function loadChannels() {
  try {
    const res = await growthApi.channels()
    channels.value = Array.isArray(res) ? res : (res.results || [])
  } catch (e) {}
}

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (filters.channel) params.channel = filters.channel
    const res = await growthApi.pool(params)
    list.value = Array.isArray(res) ? res : (res.results || [])
  } finally {
    loading.value = false
  }
}

async function loadRole() {
  try {
    const r = await growthApi.myRole()
    if (!r) { roleLabel.value = '未配置'; canClaim.value = false; canViewAll.value = false; return }
    roleLabel.value = r.has_role ? r.role_label : (r.can_view_all ? '超级总账号' : '未配置')
    canClaim.value = !!(r.has_role && r.role === 'CLOSER') || r.can_view_all
    canViewAll.value = !!r.can_view_all
  } catch (e) {}
}

async function doClaim(row) {
  try {
    await growthApi.claimLead(row.lead_ext)
    ElMessage.success('已领取到我的线索池')
    loadData()
  } catch (e) {}
}

function openClaimedBy(row) {
  ElMessage.info(`退回人：${row.returned_by_name || '-'} / 领取人：${row.claimed_by_name || '-'}`)
}

onMounted(() => {
  loadChannels()
  loadRole()
  loadData()
})
</script>

<style scoped>
.growth-page { padding: 4px; }
.stat-row { margin-bottom: 14px; }
.mini-card { text-align: center; }
.mini-label { font-size: 13px; color: #909399; }
.mini-value { font-size: 24px; font-weight: 600; margin-top: 6px; color: #303133; }
.mini-value.warn { color: #e6a23c; }
.mini-value.ok { color: #67c23a; }
.mini-value.small { font-size: 16px; }
.muted { color: #909399; font-size: 12px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { margin-bottom: 8px; }
</style>
