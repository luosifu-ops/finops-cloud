<template>
  <div class="login-page">
    <div class="login-box">
      <!-- 品牌侧 -->
      <div class="brand">
        <div class="brand-deco deco-1"></div>
        <div class="brand-deco deco-2"></div>
        <div class="brand-inner">
          <div class="logo">
            <div class="logo-mark">{{ brand.logoChar }}</div>
            <div class="logo-text">{{ brand.name }}</div>
          </div>
          <h1 class="brand-slogan">{{ brand.subtitle }}</h1>
          <p class="brand-desc">打通「人 / 财 / 事 / 客」全链路，让老板一屏掌控经营，让团队高效协同。</p>

          <ul class="features">
            <li><span class="dot dot-blue"></span><b>人</b> · 入职培训 / 考勤审批 / 绩效排行</li>
            <li><span class="dot dot-green"></span><b>财</b> · 业绩回款 / 做账进度 / 投放 ROI</li>
            <li><span class="dot dot-orange"></span><b>事</b> · 工作汇报 / 审批流 / 任务闭环</li>
            <li><span class="dot dot-purple"></span><b>客</b> · 线索到成交 / 续费预警 / 流失管控</li>
          </ul>

          <div class="brand-foot">AI 时代 · 财税服务机构的数字驾驶舱</div>
        </div>
      </div>

      <!-- 表单侧：单框两方式 -->
      <div class="form-side">
        <h2 class="form-title">欢迎登录{{ brand.name }}</h2>

        <!-- 方式一：手机号 + 密码（合并为一个表单） -->
        <el-form ref="loginRef" :model="login" :rules="loginRules" size="large" @keyup.enter="onLogin">
          <el-form-item prop="account">
            <el-input v-model="login.account" placeholder="手机号 / 账号" :prefix-icon="User" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="login.password" type="password" placeholder="请输入密码" :prefix-icon="Lock" show-password />
          </el-form-item>
          <el-button type="primary" size="large" class="btn" :loading="loading" @click="onLogin">登 录</el-button>
        </el-form>

        <el-divider>或</el-divider>

        <!-- 方式二：微信扫码（同框内按钮，点击展开二维码） -->
        <div class="wx-inline">
          <el-button class="wx-btn" :loading="wxLoading" @click="onWxClick">
            <span class="wx-ico">💬</span> 微信扫码登录
          </el-button>
          <div v-if="showWx" class="wx-area">
            <div v-if="wxMock" class="wx-qr-mock">
              <div class="wx-qr-img">📱</div>
              <p>当前为「模拟扫码」演示模式</p>
              <el-button type="success" :loading="wxLoading" @click="doMockScan">模拟扫码（演示）</el-button>
              <p class="wx-tip">配置微信开放平台网站应用凭证后，此处将显示真实二维码</p>
            </div>
            <template v-else>
              <iframe v-if="wxUrl" :src="wxUrl" class="wx-iframe" frameborder="0" />
              <p class="wx-tip">请用微信扫描上方二维码完成登录</p>
            </template>
          </div>
        </div>

        <div class="tips">
          <p>演示账号（密码见右侧）</p>
          <div class="accounts">
            <div><span>老板</span><code>boss</code><code>admin123</code></div>
            <div><span>销售经理</span><code>sales_mgr</code><code>123456</code></div>
            <div><span>会计经理</span><code>acc_mgr</code><code>123456</code></div>
            <div><span>运营经理</span><code>ops_mgr</code><code>123456</code></div>
            <div><span>人事</span><code>hr</code><code>123456</code></div>
            <div><span>员工</span><code>sales1</code><code>123456</code></div>
          </div>
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
const login = reactive({ account: 'boss', password: 'admin123' })
const loginRules = {
  account: [{ required: true, message: '请输入手机号或账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}
const onLogin = async () => {
  await loginRef.value.validate()
  loading.value = true
  try {
    const res = await authApi.login({ username: login.account, password: login.password })
    if (res.code === 0) {
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
      wxMock.value = res.data.mock
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
onMounted(() => openWxScan())
onBeforeUnmount(() => { stopWxPoll() })
</script>

<style scoped>
.login-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  padding: 36px 16px; box-sizing: border-box;
  background: radial-gradient(1200px 600px at 70% -10%, #e8f0ff 0%, #f4f6fb 55%), linear-gradient(135deg, #eef3ff 0%, #f7f8fa 100%);
}
.login-box {
  width: 920px; min-height: 560px; background: #fff; border-radius: 18px;
  box-shadow: 0 18px 60px rgba(31, 35, 41, .10);
  display: grid; grid-template-columns: 1fr 1fr; overflow: hidden;
}
/* 品牌侧 */
.brand {
  position: relative; overflow: hidden;
  background: linear-gradient(160deg, #3a7afe 0%, #2f6fed 55%, #1e4fd0 100%);
  color: #fff; padding: 44px 40px;
  display: flex; align-items: center;
}
.brand-deco { position: absolute; border-radius: 50%; filter: blur(8px); opacity: .35; }
.deco-1 { width: 220px; height: 220px; background: #7aa6f8; top: -70px; right: -50px; }
.deco-2 { width: 160px; height: 160px; background: #1b3fa8; bottom: -60px; left: -40px; }
.brand-inner { position: relative; z-index: 1; width: 100%; }
.logo { display: flex; align-items: center; gap: 12px; margin-bottom: 26px; }
.logo-mark {
  width: 46px; height: 46px; border-radius: 13px; background: rgba(255,255,255,.18);
  border: 1px solid rgba(255,255,255,.35);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 800; backdrop-filter: blur(4px);
}
.logo-text { font-size: 22px; font-weight: 800; letter-spacing: .5px; }
.brand-slogan { font-size: 22px; font-weight: 700; margin: 0 0 10px; line-height: 1.4; }
.brand-desc { font-size: 13.5px; opacity: .92; line-height: 1.8; margin: 0 0 24px; }
.features { list-style: none; padding: 0; margin: 0 0 28px; display: grid; gap: 12px; }
.features li { font-size: 14px; opacity: .95; display: flex; align-items: center; gap: 10px; }
.features b { font-weight: 700; }
.dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.dot-blue { background: #8ab4f8; } .dot-green { background: #5fd0a0; }
.dot-orange { background: #ffc07a; } .dot-purple { background: #c4a7ff; }
.brand-foot {
  font-size: 12px; opacity: .8; padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,.18);
}
/* 表单侧 */
.form-side { padding: 40px 44px 12px; display: flex; flex-direction: column; }
.form-title { font-size: 22px; font-weight: 800; margin: 0 0 20px; color: #1f2329; }
.btn { width: 100%; }
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
.tips { padding: 18px 0 28px; margin-top: auto; }
.tips p { font-size: 12px; color: var(--text-sub); margin: 0 0 10px; }
.accounts { display: grid; grid-template-columns: 1fr; gap: 6px; }
.accounts div { display: grid; grid-template-columns: 60px 1fr 70px; gap: 6px; font-size: 12px; align-items: center; }
.accounts span { color: var(--text-sub); }
.accounts code {
  background: #f2f4f7; padding: 2px 6px; border-radius: 4px;
  font-family: Menlo, monospace; font-size: 11px; color: #2f6fed;
}
</style>
