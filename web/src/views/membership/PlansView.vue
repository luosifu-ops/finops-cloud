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
          <div class="plan-year text-muted">年付 ¥{{ p.price_yearly }}（约省 {{ yearSave(p) }}%）</div>
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
  if (!p.price_monthly || !p.price_yearly) return 0
  return Math.max(0, Math.round((1 - p.price_yearly / (p.price_monthly * 12)) * 100))
}
// 选择套餐后跳转订阅支付页，并预选该套餐（支付方式/微信支付宝跳转在订阅页处理）
const choose = (p) => router.push({ path: '/membership/subscribe', query: { plan: p.id } })
onMounted(async () => {
  try { plans.value = unwrap(await membershipApi.plans({ is_active: true })) } catch (e) { plans.value = [] }
})
</script>

<style scoped>
.plan-card { position: relative; border-radius: 16px; margin-bottom: 16px; }
.plan-card.hot { border: 1px solid var(--primary); }
.hot-tag { position: absolute; top: 12px; right: 12px; }
.plan-name { font-size: 17px; font-weight: 700; }
.plan-price { margin: 10px 0 2px; color: var(--primary); }
.plan-price .cur { font-size: 16px; }
.plan-price .num { font-size: 30px; font-weight: 800; }
.plan-price .per { font-size: 13px; color: var(--text-sub); margin-left: 4px; }
.plan-year { font-size: 12px; margin-bottom: 12px; }
.plan-feats { list-style: none; padding: 0; margin: 0 0 16px; min-height: 120px; }
.plan-feats li { font-size: 13px; color: var(--text-main); padding: 5px 0; display: flex; gap: 8px; }
.tick { color: var(--success); font-weight: 700; }
.plan-btn { width: 100%; }
</style>
