<template>
  <div class="login-page">
    <div class="login-box">
      <!-- 品牌侧 -->
      <div class="brand">
        <div class="brand-inner">
          <div class="logo">
            <div class="logo-mark">{{ brand.logoChar }}</div>
            <div class="logo-text">{{ brand.name }}</div>
          </div>
          <div class="brand-eyebrow">FINOPS · ENTERPRISE SUITE</div>
          <h1 class="brand-slogan">{{ brand.subtitle }}</h1>
          <p class="brand-desc">打通「人 / 财 / 事 / 客」全链路，让老板一屏掌控经营，让团队高效协同。</p>

          <ul class="features">
            <li><span class="dot dot-blue"></span><b>人</b> · 入职培训 / 考勤审批 / 绩效排行</li>
            <li><span class="dot dot-green"></span><b>财</b> · 业绩回款 / 做账进度 / 投放 ROI</li>
            <li><span class="dot dot-orange"></span><b>事</b> · 工作汇报 / 审批流 / 任务闭环</li>
            <li><span class="dot dot-purple"></span><b>客</b> · 线索到成交 / 续费预警 / 流失管控</li>
          </ul>

          <div class="brand-foot">
            <span class="foot-line"></span>
            <span>AI 时代 · 财税服务机构的数字驾驶舱</span>
          </div>
        </div>
      </div>

      <!-- 表单侧：单框两方式 -->
      <div class="form-side">
        <div class="form-inner">
          <div class="form-eyebrow">ACCOUNT ACCESS</div>
          <h2 class="form-title">欢迎登录{{ brand.name }}</h2>
          <p class="form-sub">请使用员工账号或绑定手机号登录管理后台</p>

          <el-tabs v-model="loginTab" stretch>
            <!-- 方式一：账号密码 -->
            <el-tab-pane label="账号密码" name="pwd">
              <el-form ref="loginRef" :model="login" :rules="loginRules" size="large" @keyup.enter="onLogin">
                <el-form-item prop="account">
                  <el-input v-model="login.account" placeholder="手机号 / 账号" :prefix-icon="User" />
                </el-form-item>
                <el-form-item prop="password">
                  <el-input v-model="login.password" type="password" placeholder="请输入密码" :prefix-icon="Lock" show-password />
                </el-form-item>
                <el-form-item prop="captcha">
                  <div class="captcha-row">
                    <el-input v-model="login.captcha" placeholder="验证码（不区分大小写）" />
                    <canvas ref="captchaRef" width="110" height="40" class="captcha-img" title="点击刷新" @click="makeCaptcha"></canvas>
                  </div>
                </el-form-item>
                <div class="login-meta">
                  <el-checkbox v-model="rememberMe">记住账号</el-checkbox>
                  <el-button link type="primary" @click="loginTab = 'sms'">忘记密码？用短信验证码登录</el-button>
                </div>
                <el-button type="primary" size="large" class="btn" :loading="loading" @click="onLogin">登 录</el-button>
              </el-form>
            </el-tab-pane>

            <!-- 方式二：短信验证码登录（忘记密码走这里） -->
            <el-tab-pane label="短信验证码" name="sms">
              <el-form size="large" @keyup.enter="onSmsLogin">
                <el-form-item>
                  <el-input v-model="sms.phone" placeholder="请输入员工绑定的手机号" :prefix-icon="User" maxlength="11" />
                </el-form-item>
                <el-form-item>
                  <div class="sms-row">
                    <el-input v-model="sms.code" placeholder="6 位短信验证码" maxlength="6" />
                    <el-button :disabled="smsCooldown > 0" @click="sendSms">
                      {{ smsCooldown > 0 ? `${smsCooldown}s 后重发` : '获取验证码' }}
                    </el-button>
                  </div>
                </el-form-item>
                <el-alert v-if="smsDemoTip" type="info" :closable="false" :title="smsDemoTip" style="margin-bottom:12px" />
                <el-button type="primary" size="large" class="btn" :loading="smsLoading" @click="onSmsLogin">验证码登录</el-button>
                <div class="sms-tip">验证码发送到员工档案中登记的手机号；手机号未绑定时请先用账号密码登录后在「个人中心」绑定。</div>
              </el-form>
            </el-tab-pane>
          </el-tabs>

          <!-- 自助入职：全员先提交申请，人事审核通过自动建账号（Boss 2026-10-28 指示） -->
          <div class="apply-entry">
            <span class="apply-hint">还没有账号？</span>
            <el-button link type="primary" @click="$router.push('/apply')">申请入职，创建账号 →</el-button>
          </div>

          <!-- 微信扫码登录暂未开放（待微信开放平台网站应用凭证，配置后恢复此区块） -->
        </div>

        <div class="form-foot">
          <span>© {{ new Date().getFullYear() }} {{ brand.name }}</span>
          <span class="foot-dot"></span>
          <span>企业级财税 · 人事一体化平台</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { authApi } from '@/api'
import { useUserStore } from '@/store/user'
import { brand } from '@/store/brand'

const router = useRouter()
const store = useUserStore()

// ---------- 方式一：手机号 / 账号 + 密码 ----------
const loginRef = ref()
const loading = ref(false)
const loginTab = ref('pwd')
const login = reactive({ account: '', password: '', captcha: '' })
const rememberMe = ref(localStorage.getItem('remember_account') === '1')
if (rememberMe.value) login.account = localStorage.getItem('saved_account') || ''
const loginRules = {
  account: [{ required: true, message: '请输入手机号或账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// —— 图形防刷验证码（前端生成，防止脚本批量撞库）——
const captchaRef = ref(null)
let captchaText = ''
function makeCaptcha() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  captchaText = Array.from({ length: 4 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
  const cv = captchaRef.value
  if (!cv) return
  const ctx = cv.getContext('2d')
  ctx.clearRect(0, 0, cv.width, cv.height)
  ctx.fillStyle = '#f0f3f8'
  ctx.fillRect(0, 0, cv.width, cv.height)
  for (let i = 0; i < 4; i++) {
    ctx.save()
    ctx.font = `bold ${20 + Math.random() * 6}px sans-serif`
    ctx.fillStyle = ['#3a7afe', '#2f9e6e', '#e08a2e', '#8a56d6'][i % 4]
    ctx.translate(14 + i * 24, 26)
    ctx.rotate((Math.random() - 0.5) * 0.5)
    ctx.fillText(captchaText[i], -8, 0)
    ctx.restore()
  }
  for (let i = 0; i < 4; i++) {
    ctx.strokeStyle = 'rgba(60,80,120,.25)'
    ctx.beginPath()
    ctx.moveTo(Math.random() * cv.width, Math.random() * cv.height)
    ctx.lineTo(Math.random() * cv.width, Math.random() * cv.height)
    ctx.stroke()
  }
}
const onLogin = async () => {
  if (login.captcha.trim().toUpperCase() !== captchaText) {
    ElMessage.error('验证码不正确，请重新输入')
    login.captcha = ''
    makeCaptcha()
    return
  }
  await loginRef.value.validate()
  loading.value = true
  try {
    const res = await authApi.login({ username: login.account, password: login.password })
    if (res.code === 0) {
      if (rememberMe.value) {
        localStorage.setItem('remember_account', '1')
        localStorage.setItem('saved_account', login.account)
      } else {
        localStorage.removeItem('remember_account')
        localStorage.removeItem('saved_account')
      }
      store.setAuth(res.data.access, res.data.user)
      ElMessage.success(`欢迎回来，${res.data.user.display_name}`)
      router.push('/dashboard')
    } else {
      ElMessage.error(res.msg || '登录失败')
    }
  } finally {
    loading.value = false
  }
}

// ---------- 方式二：短信验证码登录（忘记密码走这里） ----------
const sms = reactive({ phone: '', code: '' })
const smsLoading = ref(false)
const smsCooldown = ref(0)
const smsDemoTip = ref('')
let smsTimer = null
const sendSms = async () => {
  if (!/^1[3-9]\d{9}$/.test(sms.phone)) return ElMessage.warning('请输入正确的 11 位手机号')
  try {
    const res = await authApi.sendSmsCode({ phone: sms.phone, scene: 'LOGIN' })
    if (res.code === 0) {
      smsCooldown.value = res.data?.resend_interval || 60
      smsTimer = setInterval(() => {
        if (--smsCooldown.value <= 0) clearInterval(smsTimer)
      }, 1000)
      if (res.data?.demo && res.data?.debug_code) {
        smsDemoTip.value = `未配置短信网关（演示模式），验证码：${res.data.debug_code}`
        sms.code = res.data.debug_code
      } else {
        smsDemoTip.value = ''
        ElMessage.success('验证码已发送')
      }
    } else {
      ElMessage.error(res.msg || '发送失败')
    }
  } catch (e) { /* 拦截器已提示 */ }
}
const onSmsLogin = async () => {
  if (!/^1[3-9]\d{9}$/.test(sms.phone)) return ElMessage.warning('请输入正确的 11 位手机号')
  if (!/^\d{6}$/.test(sms.code)) return ElMessage.warning('请输入 6 位验证码')
  smsLoading.value = true
  try {
    const res = await authApi.smsLogin({ phone: sms.phone, code: sms.code })
    if (res.code === 0) {
      store.setAuth(res.data.access, res.data.user)
      ElMessage.success(`欢迎回来，${res.data.user.display_name}`)
      router.push('/dashboard')
    } else if (res.code === 2) {
      ElMessage.warning(res.msg || '该手机号未绑定员工账号')
    } else {
      ElMessage.error(res.msg || '登录失败')
    }
  } finally { smsLoading.value = false }
}

// ---------- 方式二：微信扫码（同框展开） ----------
const wxLoading = ref(false)
const wxMock = ref(true)
const wxUrl = ref('')
const showWx = ref(false)
let wxTimer = null
let wxScene = ''
const openWxScan = async () => {
  try {
    const res = await authApi.wxScanUrl()
    if (res.code === 0) {
      wxMock.value = res.data.mock || !res.data.url
      wxUrl.value = res.data.url || ''
      if (!wxMock.value) startWxPoll()
    }
  } catch (e) { /* 拦截器已提示 */ }
}
const onWxClick = () => {
  showWx.value = true
  if (!wxUrl.value && wxMock.value) openWxScan()
  else if (!wxMock.value && !wxTimer) startWxPoll()
}
const startWxPoll = () => {
  stopWxPoll()
  wxTimer = setInterval(async () => {
    try {
      const res = await authApi.wxScanStatus({ scene: wxScene })
      if (res.code === 0 && res.data?.status === 'SUCCESS') {
        stopWxPoll()
        const payload = res.data
        store.setAuth(payload.access, payload.user)
        ElMessage.success('微信扫码登录成功')
        router.push('/dashboard')
      } else if (res.code === 0 && res.data?.status === 'EXPIRED') {
        stopWxPoll()
        ElMessage.warning('二维码已过期，请刷新')
      }
    } catch (e) { /* ignore */ }
  }, 2000)
}
const stopWxPoll = () => { if (wxTimer) { clearInterval(wxTimer); wxTimer = null } }
const doMockScan = async () => {
  wxLoading.value = true
  try {
    const res = await authApi.wxScanMock({ username: login.account || 'admin' })
    if (res.code === 0) {
      store.setAuth(res.data.access, res.data.user)
      ElMessage.success('微信扫码登录成功')
      router.push('/dashboard')
    } else {
      ElMessage.error(res.msg || '扫码登录失败')
    }
  } finally {
    wxLoading.value = false
  }
}
// 微信扫码登录暂未开放（凭证配置后恢复此行）：onMounted(() => openWxScan())
onMounted(() => { makeCaptcha() })
onBeforeUnmount(() => { stopWxPoll(); if (smsTimer) clearInterval(smsTimer) })
</script>

<style scoped>
/* ============================================================================
   登录页 · Apple HIG —— 简洁干净 · 居中布局 · 品牌文字突出 · 明暗自适应
   ========================================================================== */
.login-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  padding: 40px 20px; box-sizing: border-box;
  background:
    radial-gradient(900px 520px at 50% -10%, var(--primary-50) 0%, rgba(0, 0, 0, 0) 62%),
    var(--page-bg);
  transition: background 240ms var(--ease-out);
}

.login-box {
  position: relative; z-index: 1;
  width: 920px; min-height: 560px; background: var(--card-bg); border-radius: 24px;
  border: 1px solid var(--border-soft);
  box-shadow:
    0 1px 2px rgba(16, 24, 40, 0.04),
    0 24px 72px -28px rgba(16, 24, 40, 0.22);
  display: grid; grid-template-columns: 1fr 1.08fr; overflow: hidden;
  animation: login-in 560ms var(--ease-out);
}
@keyframes login-in {
  from { opacity: 0; transform: translateY(16px) scale(0.99); }
  to { opacity: 1; transform: none; }
}

/* ---------------- 品牌侧：留白干净，文字层级突出 ---------------- */
.brand {
  position: relative; overflow: hidden;
  background: var(--brand-gradient);
  color: #fff; padding: 48px 44px;
  display: flex; align-items: center;
}
.brand-inner { position: relative; z-index: 1; width: 100%; }

.logo { display: flex; align-items: center; gap: 13px; margin-bottom: 34px; }
.logo-mark {
  width: 48px; height: 48px; border-radius: 14px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.22);
  display: flex; align-items: center; justify-content: center;
  font-size: 23px; font-weight: 800; color: #fff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.28);
  position: relative;
}
.logo-mark::after {
  content: ''; position: absolute; top: -2px; right: -2px;
  width: 8px; height: 8px; border-radius: 50%;
  background: #bcd0e8;
  box-shadow: 0 0 0 2px rgba(13, 17, 23, 0.35);
}
.logo-text { font-size: 21px; font-weight: 750; letter-spacing: 0.3px; color: #fff; }

.brand-eyebrow {
  font-size: 10px; font-weight: 650; letter-spacing: 0.20em;
  color: rgba(255, 255, 255, 0.55); margin-bottom: 12px;
  display: flex; align-items: center; gap: 9px;
}
.brand-eyebrow::before {
  content: ''; width: 22px; height: 1px; background: rgba(255, 255, 255, 0.4);
}

.brand-slogan {
  font-size: 26px; font-weight: 700; margin: 0 0 14px;
  line-height: 1.4; letter-spacing: -0.45px; color: #fff;
}
.brand-slogan::after {
  content: ''; display: block; width: 44px; height: 2.5px; border-radius: 2px; margin-top: 18px;
  background: rgba(255, 255, 255, 0.55);
}
.brand-desc {
  font-size: 13.5px; color: rgba(255, 255, 255, 0.72);
  line-height: 1.85; margin: 0 0 28px; letter-spacing: 0.01em;
}

.features { list-style: none; padding: 0; margin: 0 0 32px; display: grid; gap: 13px; }
.features li {
  font-size: 13px; color: rgba(255, 255, 255, 0.85);
  display: flex; align-items: center; gap: 11px; letter-spacing: 0.01em;
}
.features b { font-weight: 700; color: #fff; }
.dot {
  width: 7px; height: 7px; border-radius: 50%; flex: none;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.08);
}
.dot-blue { background: #bcd0e8; }
.dot-green { background: #8fd8b8; }
.dot-orange { background: #e8cba0; }
.dot-purple { background: #b6cbe4; }

.brand-foot {
  font-size: 11.5px; color: rgba(255, 255, 255, 0.45);
  padding-top: 18px; border-top: 1px solid rgba(255, 255, 255, 0.10);
  display: flex; align-items: center; gap: 10px; letter-spacing: 0.04em;
}
.foot-line {
  width: 16px; height: 1px; background: rgba(255, 255, 255, 0.4); flex: none;
}

/* ---------------- 表单侧：苹果控件 ---------------- */
.form-side {
  padding: 46px 48px 26px; display: flex; flex-direction: column;
  background: var(--card-bg);
  transition: background 240ms var(--ease-out);
}
.form-inner { flex: 1; display: flex; flex-direction: column; justify-content: center; }

.form-eyebrow {
  font-size: 10px; font-weight: 650; letter-spacing: 0.18em;
  color: var(--text-faint); margin-bottom: 10px;
}
.form-title {
  font-size: 24px; font-weight: 750; margin: 0 0 8px;
  color: var(--text-main); letter-spacing: -0.5px; line-height: 1.3;
}
.form-sub {
  font-size: 12.5px; color: var(--text-weak); margin: 0 0 24px; line-height: 1.6;
}

.form-side :deep(.el-tabs__header) { margin-bottom: 22px; }
.form-side :deep(.el-tabs__item) { font-size: 13.5px; height: 40px; }

.btn {
  width: 100%; height: 46px; font-size: 15px; font-weight: 650;
  letter-spacing: 0.10em; border-radius: 12px;
  background-image: none !important;
  box-shadow: 0 1px 2px rgba(60, 93, 140, 0.24) !important;
  transition: all 220ms var(--ease-spring) !important;
}
.btn:hover { transform: translateY(-1px); box-shadow: 0 4px 14px -2px rgba(74, 111, 165, 0.42) !important; }
.btn:active { transform: translateY(0) scale(0.985); }

.apply-entry {
  margin-top: 20px; text-align: center; font-size: 12.5px;
  color: var(--text-weak); display: flex; align-items: center;
  justify-content: center; gap: 1px;
}
.apply-hint { color: var(--text-weak); }

.login-meta {
  display: flex; justify-content: space-between; align-items: center;
  margin: -4px 0 16px;
}
.login-meta :deep(.el-checkbox__label) { font-size: 12.5px; color: var(--text-sub); }
.login-meta :deep(.el-button.is-link) { font-size: 12.5px; }

.captcha-row { display: flex; gap: 10px; width: 100%; align-items: center; }
.captcha-row .el-input { flex: 1; }
.captcha-img {
  width: 110px; height: 40px; border-radius: 10px; cursor: pointer;
  border: 1px solid var(--border); flex: none;
  transition: border-color 200ms var(--ease-out), transform 220ms var(--ease-spring);
}
.captcha-img:hover { border-color: var(--primary-300); transform: scale(1.02); }
.sms-row { display: flex; gap: 10px; width: 100%; }
.sms-row .el-input { flex: 1; }
.sms-tip {
  font-size: 11.5px; color: var(--text-weak);
  margin-top: 10px; line-height: 1.65;
}

.form-foot {
  display: flex; align-items: center; justify-content: center; gap: 9px;
  font-size: 11px; color: var(--text-faint); letter-spacing: 0.03em;
  padding-top: 18px; border-top: 1px solid var(--border-soft); margin-top: 20px;
}
.foot-dot { width: 3px; height: 3px; border-radius: 50%; background: var(--border-strong); }

/* 苹果风格输入控件：44px 高 · 12px 圆角 · 柔和聚焦光环 */
.form-side :deep(.el-input__wrapper) {
  padding: 1px 14px; min-height: 44px; border-radius: 12px;
  background: var(--surface-2);
  box-shadow: 0 0 0 1px var(--border) inset;
  transition: box-shadow 200ms var(--ease-out), background 200ms var(--ease-out);
}
.form-side :deep(.el-input__wrapper.is-focused) {
  background: var(--card-bg);
  box-shadow: 0 0 0 1px var(--primary) inset, 0 0 0 4px rgba(74, 111, 165, 0.12);
}
.form-side :deep(.el-form-item) { margin-bottom: 16px; }

.wx-inline { text-align: center; }
.wx-btn {
  width: 100%; border-color: #07c160; color: #07c160;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}
.wx-btn:hover { background: rgba(7,193,96,.06); }
.wx-ico { font-size: 16px; }
.wx-area { text-align: center; padding: 16px 0 6px; min-height: 170px; display: flex; align-items: center; justify-content: center; }
.wx-qr-mock .wx-qr-img { font-size: 56px; margin: 12px 0; }
.wx-qr-mock p { color: var(--text-sub); font-size: 14px; margin: 8px 0; }
.wx-iframe { width: 100%; height: 320px; border: none; }
.wx-tip { color: var(--text-sub); font-size: 12px; margin-top: 10px; }

@media (max-width: 900px) {
  .login-box { width: 100%; max-width: 460px; grid-template-columns: 1fr; min-height: auto; }
  .brand { display: none; }
  .form-side { padding: 36px 26px 22px; }
  .login-page { padding: 24px 14px; }
}
</style>