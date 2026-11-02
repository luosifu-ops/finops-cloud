<template>
  <div class="page">
    <h2 class="page-title">会员套餐</h2>
    <p class="text-muted" style="margin-top:-8px">财税企管云面向财税同行企业开放订阅，不同等级开放不同系统功能权限。</p>

    <el-row :gutter="16">
      <el-col v-for="p in plans" :key="p.id" :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="plan-card" :class="{ hot: p.code === 'PRO' }">
          <el-tag v-if="p.code === 'PRO'" type="danger" size="small" effect="dark" class="hot-tag">推荐</el-tag>
          <div class="plan-name">{{ p.name }}</div>
          <div class="plan-price">
            <span class="cur">¥</span><span class="num">{{ p.price_monthly }}</span><span class="per">/月</span>
          </div>
          <div class="plan-year text-muted">
            <template v-if="Number(p.price_monthly) > 0">
              年付 ¥{{ p.price_yearly }}（约省 {{ yearSave(p) }}%）
            </template>
            <template v-else>永久免费 · 不限时长</template>
          </div>
          <ul class="plan-feats">
            <li v-for="(f, i) in (p.features || [])" :key="i"><span class="tick">✓</span>{{ f }}</li>
          </ul>
          <el-button type="primary" round block class="plan-btn" @click="choose(p)">立即订阅</el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { membershipApi } from '@/api'

const plans = ref([])
const router = useRouter()

function unwrap(r) {
  if (!r) return []
  if (Array.isArray(r)) return r
  if (r.results) return r.results
  if (r.data && Array.isArray(r.data.results)) return r.data.results
  if (r.data && Array.isArray(r.data)) return r.data
  return []
}
const yearSave = (p) => {
  const m = Number(p.price_monthly) || 0
  const y = Number(p.price_yearly) || 0
  if (!m || !y) return 0
  return Math.max(0, Math.round((1 - y / (m * 12)) * 100))
}
// 选择套餐后跳转订阅支付页，并预选该套餐（支付方式/微信支付宝跳转在订阅页处理）
const choose = (p) => router.push({ path: '/membership/subscribe', query: { plan: p.id } })
onMounted(async () => {
  try { plans.value = unwrap(await membershipApi.plans({ is_active: true })) } catch (e) { plans.value = [] }
})
</script>

<style scoped>
/* 套餐卡：等高 + 按钮吸底，四张卡底边严格对齐 */
:deep(.el-row) { align-items: stretch; }
:deep(.el-col) { display: flex; }
.plan-card {
  position: relative; border-radius: var(--radius); margin-bottom: 16px;
  width: 100%; display: flex; flex-direction: column;
  transition: box-shadow var(--dur-base) var(--ease-out),
              transform var(--dur-base) var(--ease-out),
              border-color var(--dur-base) var(--ease-out);
}
.plan-card:hover { transform: translateY(-3px); }
.plan-card :deep(.el-card__body) {
  flex: 1; display: flex; flex-direction: column; padding: 24px 22px;
}
.plan-card.hot {
  border: 1px solid var(--primary-200);
  box-shadow: 0 4px 10px -4px rgba(42, 79, 212, 0.14), 0 20px 44px -20px rgba(42, 79, 212, 0.30) !important;
}
.hot-tag {
  position: absolute; top: 18px; right: 18px;
  border-radius: 6px;
  background: linear-gradient(150deg, #4a6ff0, #1d3aa8) !important;
  border: none !important;
  color: #fff !important;
  letter-spacing: 0.06em; font-weight: 650;
  box-shadow: 0 4px 12px -6px rgba(42, 79, 212, 0.6);
}
.plan-name {
  font-size: 16px; font-weight: 650; letter-spacing: -0.2px;
  color: var(--text-main);
}
.plan-price { margin: 14px 0 2px; color: var(--primary-700); display: flex; align-items: baseline; }
.plan-price .cur { font-size: 16px; font-weight: 600; margin-right: 1px; }
.plan-price .num {
  font-size: 32px; font-weight: 750; letter-spacing: -1.2px;
  font-variant-numeric: tabular-nums;
}
.plan-price .per { font-size: 12.5px; color: var(--text-weak); margin-left: 5px; font-weight: 500; }
.plan-year {
  font-size: 11.5px; margin-bottom: 18px;
  padding-bottom: 16px; border-bottom: 1px solid var(--border-soft);
}
.plan-feats { list-style: none; padding: 0; margin: 0 0 18px; flex: 1; }
.plan-feats li {
  font-size: 13px; color: var(--text-sub); padding: 6px 0;
  display: flex; gap: 9px; line-height: 1.5;
}
.tick {
  color: var(--success); font-weight: 700; flex: none;
  font-size: 12px; margin-top: 1px;
}
.plan-btn {
  width: 100%; margin-top: auto; height: 40px;
  border-radius: var(--radius-sm); font-weight: 650; letter-spacing: 0.04em;
}
</style>
