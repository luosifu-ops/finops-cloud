<template>
  <div class="page">
    <h2 class="page-title">订阅购买</h2>
    <el-card class="sub-card" shadow="never">
      <!-- 套餐选择（切换即同步二维码金额） -->
      <div class="plan-bar">
        <span class="plan-label">选择会员套餐</span>
        <el-select v-model="selectedPlanId" placeholder="请选择套餐" style="width: 240px" @change="onPlanChange">
          <el-option v-for="p in plans" :key="p.id" :label="`${p.name}（¥${p.price_monthly}/月）`" :value="p.id" />
        </el-select>
        <el-tag v-if="selPlan" type="success" effect="plain" class="plan-perm">
          开放：{{ permText || '无' }}
        </el-tag>
      </div>

      <!-- 微信 / 支付宝 并排收款码，打开即见 -->
      <div class="qr-row">
        <div class="qr-card wechat">
          <div class="qr-card-head"><span class="dot" />微信支付</div>
          <div class="qr-box">
            <img v-if="wechatQr" :src="wechatQr" class="qr-img" alt="微信支付二维码" />
            <div v-else class="qr-loading">{{ loading ? '二维码生成中…' : '请选择套餐' }}</div>
          </div>
          <div class="qr-amount">¥{{ amountText }}</div>
          <el-button type="success" size="small" @click="openWechat">打开微信支付</el-button>
          <div class="qr-tip">{{ wechatTip }}</div>
        </div>

        <div class="qr-card alipay">
          <div class="qr-card-head"><span class="dot" />支付宝支付</div>
          <div class="qr-box">
            <img v-if="alipayQr" :src="alipayQr" class="qr-img" alt="支付宝支付二维码" />
            <div v-else class="qr-loading">{{ loading ? '二维码生成中…' : '请选择套餐' }}</div>
          </div>
          <div class="qr-amount">¥{{ amountText }}</div>
          <el-button type="primary" size="small" @click="openAlipay">打开支付宝</el-button>
          <div class="qr-tip">{{ alipayTip }}</div>
        </div>
      </div>

      <!-- 对公转账：作为备用入口独立保留 -->
      <el-collapse class="bank-collapse">
        <el-collapse-item title="对公转账（备用）">
          <el-alert type="info" :closable="false" show-icon
            title="对公转账"
            description="将款项汇入我司对公账户，并备注「企业名称 + 会员套餐」；财务核实到账后由管理员在「会员管理」审核开通。" />
        </el-collapse-item>
      </el-collapse>

      <p class="text-muted" style="font-size:12px">
        说明：页面打开即显示微信 / 支付宝收款码，选择套餐后金额实时同步。微信已配置商户凭证后，扫码直接拉起收银台（无中间页）；
        未配置或支付宝当前为演示模式时，扫码进入系统内置演示支付页完成演示支付。其余功能不受影响。
      </p>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import QRCode from 'qrcode'
import { membershipApi } from '@/api'

const plans = ref([])
const selectedPlanId = ref(null)
const orderId = ref(null)        // 复用的订单（订阅）id：选套餐时自动建/更新，避免重复建单
const wechatQr = ref('')
const alipayQr = ref('')
const wechatInfo = ref(null)
const alipayInfo = ref(null)
const loading = ref(false)

const permMap = {
  dashboard: '经营总览', sales: '电销管理', accounting: '会计交付', hr: '人事考勤',
  ops: '运营投放', onboarding: '入职培训', performance: '业绩中心', reports: '工作汇报',
  ai: 'AI经营助手', investment: '招商板块', membership: '会员管理'
}
const selPlan = computed(() => plans.value.find(p => p.id === selectedPlanId.value) || null)
const amount = computed(() => selPlan.value?.price_monthly || 0)
const amountText = computed(() => Number(amount.value).toFixed(2))
const permText = computed(() =>
  selPlan.value ? ((selPlan.value.permissions || []).map(k => permMap[k] || k).join('、') || '无') : ''
)

// 演示支付页地址：用当前浏览器域名拼接，保证公网可达
function demoPayUrl(method) {
  if (!orderId.value) return ''
  return `${window.location.origin}/membership/pay?order=${orderId.value}&m=${method}&amount=${amount.value}`
}

function unwrap(r) {
  if (!r) return []
  if (Array.isArray(r)) return r
  if (r.results) return r.results
  if (r.data && Array.isArray(r.data.results)) return r.data.results
  if (r.data && Array.isArray(r.data)) return r.data
  return []
}

// 单个方式二维码：真实模式编码 code_url，演示模式编码演示支付页地址
async function genQrFor(method, info, targetRef) {
  if (!info.value) { targetRef.value = ''; return }
  const isReal = info.value.mode === 'real'
  const target = (isReal && info.value.code_url) ? info.value.code_url : demoPayUrl(method)
  if (!target) { targetRef.value = ''; return }
  try {
    targetRef.value = await QRCode.toDataURL(target, { width: 200, margin: 1 })
  } catch (e) {
    targetRef.value = ''
  }
}

const wechatTip = computed(() =>
  wechatInfo.value?.mode === 'real'
    ? '微信「扫一扫」即拉起收银台（真实收款，无中间页）'
    : '微信扫码进入系统演示支付页完成演示支付'
)
const alipayTip = computed(() => '支付宝扫码进入演示支付页（真实收款待接入）')

function openWechat() {
  if (!wechatInfo.value) return ElMessage.warning('二维码生成中')
  const isReal = wechatInfo.value.mode === 'real'
  const url = (isReal && wechatInfo.value.mweb_url) ? wechatInfo.value.mweb_url : demoPayUrl('WECHAT')
  const w = window.open(url, '_blank', 'noopener')
  if (!w) ElMessage.error('浏览器拦截了新窗口，请允许弹出窗口后重试')
}
function openAlipay() {
  if (!alipayInfo.value) return ElMessage.warning('二维码生成中')
  const w = window.open(demoPayUrl('ALIPAY'), '_blank', 'noopener')
  if (!w) ElMessage.error('浏览器拦截了新窗口，请允许弹出窗口后重试')
}

// 确保有一条复用订单（首次自动建、之后仅更新套餐/金额），再拉两个支付码
async function ensureOrder() {
  if (!selPlan.value) return
  try {
    if (!orderId.value) {
      const r = await membershipApi.subscribe({
        plan: selPlan.value.id,
        company_name: '微信支付订单',
        contact_name: '微信用户',
        phone: '13800000000',
        pay_method: 'WECHAT',
        amount: amount.value,
      })
      orderId.value = r?.id ?? r?.data?.id
    } else {
      await membershipApi.updateSubscription(orderId.value, { plan: selPlan.value.id, amount: amount.value })
    }
  } catch (e) {
    ElMessage.error('订单初始化失败')
    return
  }
  await refreshPay()
}

// 拉取微信 + 支付宝支付参数并生成二维码
async function refreshPay() {
  if (!orderId.value) return
  loading.value = true
  try {
    const [w, a] = await Promise.all([
      membershipApi.pay({ subscription_id: orderId.value, method: 'WECHAT' }),
      membershipApi.pay({ subscription_id: orderId.value, method: 'ALIPAY' }),
    ])
    wechatInfo.value = w?.data ?? w
    alipayInfo.value = a?.data ?? a
    await Promise.all([
      genQrFor('WECHAT', wechatInfo, wechatQr),
      genQrFor('ALIPAY', alipayInfo, alipayQr),
    ])
  } catch (e) {
    ElMessage.error('获取支付码失败')
  } finally {
    loading.value = false
  }
}

function onPlanChange() {
  ensureOrder()
}

onMounted(async () => {
  try { plans.value = unwrap(await membershipApi.plans({ is_active: true })) } catch (e) { plans.value = [] }
  const pid = new URLSearchParams(location.search).get('plan')
  if (pid && plans.value.some(p => p.id === Number(pid))) selectedPlanId.value = Number(pid)
  else if (plans.value.length) selectedPlanId.value = plans.value[0].id
  await ensureOrder()
})
</script>

<style scoped>
.sub-card { max-width: 720px; border-radius: 16px; }
.plan-bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.plan-label { font-size: 14px; color: var(--text-main); font-weight: 600; }
.plan-perm { font-size: 12px; }

/* 并排双码 */
.qr-row { display: flex; gap: 20px; flex-wrap: wrap; }
.qr-card {
  flex: 1 1 240px; min-width: 220px; border-radius: 14px; padding: 18px 16px; text-align: center;
  background: #f7f8fa; border: 1px solid var(--border);
}
.qr-card.wechat { background: #f3fbf4; }
.qr-card.alipay { background: #f3f8ff; }
.qr-card-head { font-size: 15px; font-weight: 700; margin-bottom: 14px; display: flex; align-items: center; justify-content: center; gap: 8px; color: var(--text-main); }
.qr-card-head .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.qr-card.wechat .dot { background: #07c160; }
.qr-card.alipay .dot { background: #1677ff; }
.qr-box {
  width: 150px; height: 150px; margin: 0 auto 12px; border-radius: 10px; background: #fff;
  border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; overflow: hidden;
}
.qr-img { width: 140px; height: 140px; display: block; }
.qr-loading { font-size: 12px; color: var(--text-sub); padding: 8px; }
.qr-amount { font-size: 20px; font-weight: 800; color: #fa5151; margin-bottom: 12px; }
.qr-tip { font-size: 11px; color: var(--text-sub); margin-top: 8px; line-height: 1.5; }

.bank-collapse { margin: 18px 0 14px; }
</style>
