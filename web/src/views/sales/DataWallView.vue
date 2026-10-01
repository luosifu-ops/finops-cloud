<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">数据权限墙</h2>
      <div style="display:flex;gap:10px;align-items:center">
        <el-date-picker v-model="month" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width:150px" @change="loadAll" />
      </div>
    </div>

    <el-alert :title="`当前身份：${roleName}｜${roleDesc}`" :type="isBoss ? 'warning' : 'info'"
              :closable="false" show-icon class="role-alert">
      <template #default>
        <span>权限隔离制度：<b>老板/人事</b>看全部部门及成员明细；<b>部门主管/组长</b>看本部门成员明细+其他部门仅合计；<b>员工</b>仅看本部门。</span>
      </template>
    </el-alert>

    <div v-loading="loading" style="margin-top:16px">
      <el-row :gutter="16">
        <el-col :span="12" v-for="d in departments" :key="d.code" style="margin-bottom:16px">
          <el-card shadow="never" class="wall-card">
            <div class="wall-head">
              <span class="wall-name">{{ d.name }}</span>
              <el-tag size="small" :type="d.can_see_members ? 'success' : 'info'">
                {{ d.can_see_members ? '成员明细可见' : '仅合计' }}
              </el-tag>
            </div>

            <!-- 部门合计卡 -->
            <div class="total-row">
              <div class="t-item"><div class="t-label">本月业绩</div><div class="t-value">¥{{ fmt(d.total.amount) }}</div></div>
              <div class="t-item"><div class="t-label">目标</div><div class="t-value">¥{{ fmt(d.total.target) }}</div></div>
              <div class="t-item"><div class="t-label">完成率</div>
                <div class="t-value" :class="d.total.completion >= 100 ? 'ok' : ''">{{ d.total.completion }}%</div></div>
            </div>

            <!-- 成员明细 or 锁定 -->
            <template v-if="d.can_see_members">
              <el-table :data="d.members" size="small" stripe max-height="300" empty-text="暂无成员">
                <el-table-column label="排名" width="64" align="center">
                  <template #default="{row}">
                    <el-tag v-if="row.rank===1" type="danger" size="small">第1名</el-tag>
                    <el-tag v-else-if="row.rank===2" type="warning" size="small">第2名</el-tag>
                    <el-tag v-else-if="row.rank===3" type="success" size="small">第3名</el-tag>
                    <span v-else>{{ row.rank }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="name" label="姓名" width="90" />
                <el-table-column prop="team" label="小组" width="90" />
                <el-table-column prop="role" label="角色" width="90" />
                <el-table-column label="目标" width="110" align="right"><template #default="{row}">¥{{ fmt(row.target) }}</template></el-table-column>
                <el-table-column label="达成" width="110" align="right"><template #default="{row}">¥{{ fmt(row.achieved) }}</template></el-table-column>
                <el-table-column label="完成率" min-width="120">
                  <template #default="{row}">
                    <el-progress :percentage="Math.min(row.completion||0,100)"
                                 :status="row.completion>=100?'success':(row.completion>=60?'':'exception')"
                                 :text-inside="true" :stroke-width="14" />
                  </template>
                </el-table-column>
              </el-table>
              <div class="wall-sum" v-if="d.summary">
                共 {{ d.summary.member_count }} 人 · 目标合计 ¥{{ fmt(d.summary.total_target) }} ·
                已达成 ¥{{ fmt(d.summary.total_achieved) }}（{{ d.summary.completion }}%）
              </div>
            </template>
            <div v-else class="locked">
              <el-icon><Lock /></el-icon>
              <span>您无权查看「{{ d.name }}」成员明细，仅可见部门合计（权限隔离墙）</span>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Lock } from '@element-plus/icons-vue'
import { dashApi } from '@/api'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
const month = ref(new Date().toISOString().slice(0, 7))
const departments = ref([])
const roleName = ref('')
const roleDesc = ref('')
const isBoss = ref(false)

const fmt = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 0 }))

const loadAll = async () => {
  loading.value = true
  try {
    const r = await dashApi.dataWall({ month: month.value })
    const d = r.data || {}
    departments.value = d.departments || []
    roleName.value = d.role || ''
    roleDesc.value = d.role_desc || ''
    isBoss.value = !!d.is_boss
  } finally { loading.value = false }
}

onMounted(loadAll)
</script>

<style scoped>
.role-alert { margin-bottom: 4px; }
.wall-card { border-radius: 10px; border: 1px solid var(--border); min-height: 220px; }
.wall-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.wall-name { font-size: 16px; font-weight: 700; }
.total-row { display: flex; gap: 10px; margin-bottom: 12px; }
.t-item { flex: 1; background: var(--bg-sub, #f6f7f9); border-radius: 8px; padding: 8px 10px; }
.t-label { font-size: 12px; color: var(--text-sub); }
.t-value { font-size: 17px; font-weight: 700; margin-top: 2px; }
.t-value.ok { color: var(--success); }
.wall-sum { margin-top: 10px; font-size: 12px; color: var(--text-sub); }
.locked { display: flex; align-items: center; gap: 8px; color: var(--text-sub); font-size: 13px;
          background: var(--bg-sub, #f6f7f9); border-radius: 8px; padding: 14px; margin-top: 6px; }
</style>
