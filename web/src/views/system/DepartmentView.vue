<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">部门与小组</h2>
      <span class="page-tip">公司下设 运营部 / 电销部 / 会计部 三大业务线</span>
    </div>

    <el-row :gutter="16" v-loading="loading">
      <el-col :span="8" v-for="d in bizDepts" :key="d.code">
        <el-card shadow="never" class="dept-block">
          <div class="db-head">
            <el-icon :size="22"><component :is="d.icon" /></el-icon>
            <span class="db-name">{{ d.name }}</span>
            <el-tag size="small" type="info" effect="plain">{{ d.memberCount }} 人</el-tag>
          </div>
          <div class="db-desc">{{ d.description || '—' }}</div>
          <div class="db-teams">
            <div class="db-teams-title">小组（{{ d.teams.length }}）</div>
            <div class="team-item" v-for="t in d.teams" :key="t.id">
              <span class="ti-name">{{ t.name }}</span>
              <span class="ti-meta">
                <template v-if="t.leader_name">组长 {{ t.leader_name }} · </template>
                目标 ¥{{ fmt(t.month_target) }}
              </span>
            </div>
            <el-empty v-if="!d.teams.length" description="暂无小组" :image-size="40" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { orgApi } from '@/api'

const loading = ref(false)
const departments = ref([])
const teams = ref([])
const users = ref([])

const ICONS = { OPS: 'DataBoard', SALES: 'Phone', ACCOUNT: 'Tickets' }
const ORDER = ['OPS', 'SALES', 'ACCOUNT']

const fmt = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))
const deptIdOf = (u) => {
  const d = u.department
  if (d == null) return null
  return typeof d === 'object' ? d.id : d
}

const bizDepts = ref([])

const load = async () => {
  loading.value = true
  try {
    const [dRes, tRes, uRes] = await Promise.all([
      orgApi.departments({ page_size: 50 }),
      orgApi.teams({ page_size: 200 }),
      orgApi.users({ page_size: 500 }),
    ])
    departments.value = dRes.results || dRes.data?.results || []
    teams.value = tRes.results || tRes.data?.results || []
    users.value = uRes.results || uRes.data?.results || []

    bizDepts.value = ORDER.map(code => {
      const d = departments.value.find(x => x.code === code) || {}
      const dId = d.id
      const dTeams = teams.value.filter(t => (typeof t.department === 'object' ? t.department?.id : t.department) === dId)
      const memberCount = users.value.filter(u => deptIdOf(u) === dId).length
      return {
        code, name: d.name || code, description: d.description,
        icon: ICONS[code] || 'OfficeBuilding',
        teams: dTeams.map(t => ({
          id: t.id, name: t.name,
          leader_name: t.leader_name || (t.leader && (t.leader.name || t.leader.display_name)) || '',
          month_target: t.month_target || 0,
        })),
        memberCount,
      }
    })
  } finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.page-tip { font-size: 12px; color: var(--text-sub); font-weight: 400; }
.dept-block { border-radius: 10px; border: 1px solid var(--border); min-height: 260px; }
.db-head { display: flex; align-items: center; gap: 10px; }
.db-name { font-size: 17px; font-weight: 700; flex: 1; }
.db-desc { font-size: 12.5px; color: var(--text-sub); line-height: 1.6; margin: 12px 0; min-height: 40px; }
.db-teams-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--text-main); }
.team-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; border: 1px solid var(--border-soft); border-radius: 8px; margin-bottom: 8px; }
.ti-name { font-weight: 500; font-size: 13px; }
.ti-meta { font-size: 12px; color: var(--text-sub); }
</style>
