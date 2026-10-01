<template>
  <div class="page">
    <h2 class="page-title">会员管理 / 权限管控</h2>
    <div v-if="!isAdmin">
      <el-empty description="仅管理员可查看会员管理" />
      <p class="text-muted" style="text-align:center">您当前的会员等级：<b>{{ perm.level || 'FREE' }}</b></p>
    </div>
    <template v-else>
      <el-row :gutter="14" class="stat-row">
        <el-col :span="6"><div class="stat-card"><div class="label">订阅总数</div><div class="value">{{ stats.total }}</div></div></el-col>
        <el-col :span="6"><div class="stat-card"><div class="label">待开通</div><div class="value" style="color:var(--warning)">{{ stats.pending }}</div></div></el-col>
        <el-col :span="6"><div class="stat-card"><div class="label">已开通</div><div class="value" style="color:var(--success)">{{ stats.active }}</div></div></el-col>
        <el-col :span="6"><div class="stat-card"><div class="label">已过期</div><div class="value" style="color:var(--danger)">{{ stats.expired }}</div></div></el-col>
      </el-row>

      <div class="card">
        <div class="card-title">订阅列表</div>
        <div class="table-wrap">
          <el-table :data="subs" stripe>
            <el-table-column prop="company_name" label="企业" min-width="140" />
            <el-table-column prop="contact_name" label="联系人" width="100" />
            <el-table-column prop="phone" label="手机" width="130" />
            <el-table-column prop="plan_name" label="套餐" width="100" />
            <el-table-column prop="amount" label="金额" width="100" align="right" />
            <el-table-column label="支付方式" width="110">
              <template #default="{ row }"><el-tag size="small" :type="payTag(row.pay_method)">{{ payMap[row.pay_method] || '—' }}</el-tag></template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }"><el-tag :type="tagType(row.status)" size="small">{{ row.status_display }}</el-tag></template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.status === 'PENDING'" link type="success" @click="setStatus(row, 'ACTIVE')">通过</el-button>
                <el-button v-if="row.status === 'PENDING'" link type="danger" @click="setStatus(row, 'CANCELLED')">拒绝</el-button>
                <el-button v-if="row.status === 'ACTIVE'" link type="warning" @click="setStatus(row, 'EXPIRED')">标记过期</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div class="card">
        <div class="card-title">套餐权限对照</div>
        <div class="table-wrap">
          <el-table :data="plans" stripe>
            <el-table-column prop="name" label="套餐" width="120" />
            <el-table-column prop="code" label="等级" width="100" />
            <el-table-column label="开放权限">
              <template #default="{ row }">
                <el-tag v-for="k in (row.permissions || [])" :key="k" size="small" class="perm-tag">{{ permMap[k] || k }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { membershipApi } from '@/api'
import { useUserStore } from '@/store/user'

const store = useUserStore()
const isAdmin = computed(() => store.isAdmin)
const perm = ref({ level: 'FREE' })
const plans = ref([])
const subs = ref([])
const permMap = {
  dashboard: '经营总览', sales: '电销管理', accounting: '会计交付', hr: '人事考勤',
  ops: '运营投放', onboarding: '入职培训', performance: '业绩中心', reports: '工作汇报',
  ai: 'AI经营助手', investment: '招商板块', membership: '会员管理'
}
const stats = computed(() => {
  const s = { total: subs.value.length, pending: 0, active: 0, expired: 0 }
  subs.value.forEach(x => { if (x.status === 'PENDING') s.pending++; else if (x.status === 'ACTIVE') s.active++; else if (x.status === 'EXPIRED') s.expired++ })
  return s
})
function unwrap(r) {
  if (!r) return []
  if (Array.isArray(r)) return r
  if (r.results) return r.results
  if (r.data && Array.isArray(r.data.results)) return r.data.results
  if (r.data && Array.isArray(r.data)) return r.data
  return []
}
const tagType = (s) => ({ PENDING: 'warning', ACTIVE: 'success', EXPIRED: 'danger', CANCELLED: 'info' }[s] || 'info')
const payMap = { WECHAT: '微信支付', ALIPAY: '支付宝支付', BANK: '对公转账', OTHER: '其他', '': '—' }
const payTag = (m) => ({ WECHAT: 'success', ALIPAY: 'primary', BANK: 'warning', OTHER: 'info', '': 'info' }[m] || 'info')
const setStatus = async (row, st) => {
  try { await membershipApi.setStatus(row.id, { status: st }); ElMessage.success('已更新'); load() } catch (e) { ElMessage.error('操作失败') }
}
const load = async () => {
  try {
    plans.value = unwrap(await membershipApi.plans())
    subs.value = unwrap(await membershipApi.subscriptions({ page_size: 500 }))
    perm.value = await membershipApi.permissions()
  } catch (e) {}
}
onMounted(load)
</script>

<style scoped>
.stat-row { margin-bottom: 16px; }
.perm-tag { margin: 2px 4px 2px 0; }
</style>
