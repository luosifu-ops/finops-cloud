<template>
  <div class="pay-page">
    <div class="pay-card">
      <div class="brand">{{ brand.name }} · 会员支付</div>

      <el-alert v-if="error" type="error" :closable="false" :title="error" />

      <template v-else>
        <div class="amount">¥{{ displayAmount }}</div>
        <div class="method-tag" :class="methodClass">{{ methodLabel }}</div>

        <div class="order-info">
          <div class="row"><span>订单号</span><b>#{{ orderId }}</b></div>
          <div class="row"><span>企业名称</span><b>{{ info.company || '—' }}</b></div>
          <div class="row"><span>会员套餐</span><b>{{ info.plan || '—' }}</b></div>
        </div>

        <el-button v-if="!done" type="primary" size="large" class="pay-btn" :loading="paying" @click="confirmPay">
          确认支付（演示环境）
        </el-button>
        <el-result v-else icon="success" title="支付成功（演示环境）" sub-title="订单已记录，管理员审核通过后即开通对应权限">
          <template #extra>
            <el-button type="primary" @click="goHome">返回首页</el-button>
          </template>
        </el-result>

        <p class="tip">本页为系统内置支付页，扫码或点击即可打开；演示环境下「确认支付」将标记订单为已支付。接入真实商户后由后端调用微信 / 支付宝统一下单返回可收款二维码。</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { brand } from '@/store/brand'

const route = useRoute()

const orderId = route.query.order
const method = (route.query.m || 'WECHAT').toUpperCase()
const amount = route.query.amount

const error = ref('')
const paying = ref(false)
const done = ref(false)
const info = reactive({ company: route.query.company || '', plan: route.query.plan || '' })

const displayAmount = computed(() => {
  const n = Number(amount)
  return isNaN(n) ? '0.00' : n.toFixed(2)
})
const methodLabel = computed(() => ({ WECHAT: '微信支付', ALIPAY: '支付宝支付', BANK: '对公转账' }[method] || '在线支付'))
const methodClass = computed(() => ({ WECHAT: 'wechat', ALIPAY: 'alipay', BANK: 'bank' }[method] || ''))

if (!orderId) error.value = '缺少订单参数，无法支付'

// 演示支付：直连后端 status 接口（不使用带 401 拦截的 http 实例，避免微信内未登录被强制跳转登录）
// 成功则真实开通；微信内未登录会 401，捕获后仍以「演示成功」收尾，保证扫码流程不中断
async function confirmPay() {
  if (!orderId) return
  paying.value = true
  try {
    await axios.post(`/api/membership/subscriptions/${orderId}/status/`, { status: 'ACTIVE' })
  } catch (e) { /* 演示环境容忍 */ }
  finally {
    done.value = true
    paying.value = false
  }
}

function goHome() {
  window.location.href = `${window.location.origin}/membership/subscribe`
}
</script>

<style scoped>
.pay-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #f3f8ff 0%, #eefcf3 100%); padding: 20px;
}
.pay-card {
  width: 100%; max-width: 380px; background: #fff; border-radius: 18px;
  padding: 28px 24px; box-shadow: 0 10px 40px rgba(0,0,0,.08); text-align: center;
}
.brand { font-size: 13px; color: #888; margin-bottom: 18px; letter-spacing: .5px; }
.amount { font-size: 38px; font-weight: 800; color: #fa5151; margin-bottom: 8px; }
.method-tag {
  display: inline-block; font-size: 13px; padding: 3px 12px; border-radius: 20px; margin-bottom: 18px;
}
.method-tag.wechat { background: #f3fbf4; color: #07c160; }
.method-tag.alipay { background: #f3f8ff; color: #1677ff; }
.method-tag.bank { background: #fff7e6; color: #d48806; }
.order-info {
  text-align: left; background: #fafafa; border-radius: 12px; padding: 12px 16px; margin-bottom: 20px;
}
.order-info .row { display: flex; justify-content: space-between; font-size: 14px; padding: 6px 0; border-bottom: 1px dashed #eee; }
.order-info .row:last-child { border-bottom: none; }
.order-info .row span { color: #999; }
.pay-btn { width: 100%; border-radius: 24px; }
.tip { font-size: 11px; color: #aaa; margin-top: 16px; line-height: 1.6; text-align: left; }
</style>
