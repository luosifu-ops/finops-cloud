<template>
  <div class="yzf">
    <el-alert v-if="data.is_demo" type="warning" :closable="false" show-icon title="当前为演示数据"
      description="在后端配置 YUNZHANGFANG_API_KEY 后拉取真实账套与凭证。" style="margin-bottom:12px" />

    <div class="yzf-head">
      <div>
        <h2 style="margin:0">云账房 · 财税数据中心</h2>
        <p class="sub">账号：{{ data.account_name }}</p>
      </div>
      <el-button type="primary" @click="openPortal(data.portal_url)">前往云账房 ›</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="8"><el-card shadow="hover"><div class="kpi"><div class="num">{{ data.books.length }}</div><div class="lab">托管账套</div></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="hover"><div class="kpi"><div class="num">{{ data.pending_vouchers }}</div><div class="lab">待处理凭证</div></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="hover"><div class="kpi"><div class="num">{{ totalVouchers }}</div><div class="lab">凭证总数</div></div></el-card></el-col>
    </el-row>

    <el-card style="margin-top:16px" header="账套列表">
      <el-table :data="data.books" border>
        <el-table-column prop="name" label="账套名称" />
        <el-table-column prop="period" label="会计期间" width="140" />
        <el-table-column prop="vouchers" label="凭证数" width="120" />
      </el-table>
    </el-card>

    <el-card style="margin-top:16px" header="财务报表">
      <el-table :data="data.reports" border>
        <el-table-column prop="name" label="报表" width="160" />
        <el-table-column prop="period" label="期间" width="140" />
        <el-table-column prop="assets" label="资产" />
        <el-table-column prop="liabilities" label="负债" />
        <el-table-column prop="equity" label="所有者权益" />
        <el-table-column prop="revenue" label="营业收入" />
        <el-table-column prop="profit" label="利润" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { integrationApi } from '@/api'

const data = ref({
  books: [], reports: [], account_name: '', pending_vouchers: 0,
  portal_url: 'https://www.yunzhangfang.com', is_demo: true
})
const totalVouchers = computed(() => data.value.books.reduce((s, b) => s + (b.vouchers || 0), 0))

async function load() {
  try { const r = await integrationApi.yunzhangfang(); data.value = r.data || data.value } catch (e) {}
}
function openPortal(url) { if (url) window.open(url, '_blank') }
onMounted(load)
</script>

<style scoped>
.yzf-head { display: flex; align-items: center; justify-content: space-between; background: #fff; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.yzf-head .sub { color: var(--text-sub); margin: 6px 0 0; font-size: 13px; }
.kpi { text-align: center; padding: 8px 0; }
.kpi .num { font-size: 28px; font-weight: 700; color: var(--primary); }
.kpi .lab { color: var(--text-sub); font-size: 13px; margin-top: 4px; }
</style>
