<template>
  <el-container class="layout">
    <!-- 桌面端侧边栏 -->
    <el-aside v-if="!isMobile" :width="collapsed ? '68px' : '232px'" class="aside">
      <div class="logo" :class="{ mini: collapsed }">
        <div class="logo-mark">{{ brand.logoChar }}</div>
        <div v-if="!collapsed" class="logo-text">
          <span class="logo-name">{{ brand.name }}</span>
          <span class="logo-sub">财税 · 企管 · 一体化</span>
        </div>
      </div>
      <el-scrollbar>
        <SideMenu :collapsed="collapsed" />
      </el-scrollbar>
      <div v-if="!collapsed" class="aside-foot">
        <span class="dot"></span>系统运行正常
      </div>
    </el-aside>

    <!-- 移动端抽屉 -->
    <el-drawer v-else v-model="drawer" direction="ltr" size="240px" :with-header="false" class="side-drawer">
      <div class="logo drawer-logo">
        <div class="logo-mark">{{ brand.logoChar }}</div>
        <div class="logo-text">
          <span class="logo-name">{{ brand.name }}</span>
          <span class="logo-sub">财税 · 企管 · 一体化</span>
        </div>
      </div>
      <el-scrollbar>
        <SideMenu :collapsed="false" />
      </el-scrollbar>
    </el-drawer>

    <el-container class="body">
      <el-header class="header">
        <div class="left">
          <div class="toggle" @click="onToggle">
            <el-icon><Expand v-if="collapsed && !isMobile" /><Fold v-else /></el-icon>
          </div>
          <div class="crumb">
            <span v-if="$route.meta.group" class="crumb-group">{{ $route.meta.group }}</span>
            <span v-if="$route.meta.group" class="crumb-sep">/</span>
            <span class="crumb-cur">{{ $route.meta.title || '首页' }}</span>
          </div>
        </div>
        <div class="right">
          <!-- 亮色/暗色模式一键切换（Apple HIG） -->
          <div class="icon-btn" @click="toggleTheme" :title="isDark ? '切换到亮色模式' : '切换到暗色模式'">
            <el-icon :size="18"><Moon v-if="!isDark" /><Sunny v-else /></el-icon>
          </div>

          <!-- 消息中心：站内信（审批结果等）+ 经营待办聚合 -->
          <el-popover placement="bottom-end" :width="360" trigger="click" popper-class="msg-pop">
            <template #reference>
              <div class="icon-btn">
                <el-badge :value="msgCount" :hidden="!msgCount" :max="99">
                  <el-icon :size="18"><Bell /></el-icon>
                </el-badge>
              </div>
            </template>
            <div class="msg-head">
              <span>消息中心</span>
              <el-button v-if="inboxUnread" link type="primary" size="small" @click="markAllRead">全部已读</el-button>
            </div>
            <el-tabs v-model="msgTab" stretch style="margin-top:4px">
              <el-tab-pane :label="`站内信${inboxUnread ? ` (${inboxUnread})` : ''}`" name="inbox">
                <div class="msg-list">
                  <div v-if="!inboxList.length" class="msg-empty">暂无站内消息</div>
                  <div class="msg-item" v-for="m in inboxList" :key="m.id" :class="{ unread: !m.is_read }"
                    @click="openInbox(m)">
                    <span class="msg-icon">{{ inboxIcon(m.category) }}</span>
                    <div class="msg-body">
                      <div class="msg-label">
                        <span v-if="!m.is_read" class="dot-new"></span>{{ m.title }}
                      </div>
                      <div class="msg-sub msg-clip">{{ m.body }}</div>
                      <div class="msg-time">{{ m.created_at }}</div>
                    </div>
                  </div>
                </div>
              </el-tab-pane>
              <el-tab-pane label="经营待办" name="todo">
                <div class="msg-list">
                  <div class="msg-item" v-for="m in msgItems" :key="m.key" :class="'lv-'+m.level" @click="go(m.path)">
                    <span class="msg-icon">{{ m.icon }}</span>
                    <div class="msg-body">
                      <div class="msg-label">{{ m.label }}</div>
                      <div class="msg-sub">{{ m.count ? '共 ' + m.count + ' 项待处理' : '暂无' }}</div>
                    </div>
                    <span class="msg-count" v-if="m.count">{{ m.count }}</span>
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </el-popover>

          <div class="v-divider"></div>

          <el-dropdown @command="handleCommand">
            <span class="user">
              <el-avatar :size="32" class="avatar">{{ userName.charAt(0) }}</el-avatar>
              <span class="u-meta">
                <span class="uname">{{ userName }}</span>
                <span class="urole">{{ roleName }}</span>
              </span>
              <el-icon class="caret"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view :key="$route.fullPath" />
      </el-main>

      <!-- 页脚：备案号（备案通过后由后端 BRAND/ICP_BEIAN/POLICE_BEIAN 注入，留空不显示） -->
      <footer class="site-footer" v-if="brand.icpBeian || brand.policeBeian">
        <template v-if="brand.icpBeian">
          <a class="beian-link" href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">{{ brand.icpBeian }}</a>
        </template>
        <template v-if="brand.policeBeian">
          <span class="beian-sep">·</span>
          <a class="beian-link" :href="policeBeianUrl(brand.policeBeian)" target="_blank" rel="noreferrer">{{ brand.policeBeian }}</a>
        </template>
      </footer>
    </el-container>

    <!-- AI 经营助手浮窗 -->
    <AiAssistant />
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Bell, Expand, Fold, ArrowDown, Moon, Sunny } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { brand, policeBeianUrl } from '@/store/brand'
import { dashApi, salesApi, accApi, commonApi } from '@/api'
import SideMenu from '@/components/SideMenu.vue'
import AiAssistant from '@/components/AiAssistant.vue'

const router = useRouter()
const store = useUserStore()
const collapsed = ref(false)
const drawer = ref(false)
const isMobile = ref(false)

const userName = computed(() => store.name)
const roleName = computed(() => store.roleName)

// —— 亮色 / 暗色模式一键切换（Apple HIG，记忆到 localStorage）——
const isDark = ref(document.documentElement.classList.contains('dark'))
const toggleTheme = () => {
  const root = document.documentElement
  root.classList.add('theme-switching')
  isDark.value = !isDark.value
  root.classList.toggle('dark', isDark.value)
  localStorage.setItem('finops-theme', isDark.value ? 'dark' : 'light')
  setTimeout(() => root.classList.remove('theme-switching'), 320)
}

const msgItems = ref([
  { key: 'approval', level: 'danger', icon: '✅', label: '待我审批', count: 0, path: '/hr/approval' },
  { key: 'overdue', level: 'warning', icon: '⏰', label: '逾期做账', count: 0, path: '/accounting/tasks' },
  { key: 'expireSales', level: 'warning', icon: '📝', label: '合同将到期', count: 0, path: '/sales/customers' },
  { key: 'expireAcc', level: 'warning', icon: '📒', label: '代账将到期', count: 0, path: '/accounting/clients' }
])
const msgCount = computed(() => msgItems.value.reduce((s, m) => s + (m.count || 0), 0) + inboxUnread.value)

// —— 站内信（审批结果通知等）——
const msgTab = ref('inbox')
const inboxList = ref([])
const inboxUnread = ref(0)
const inboxIcon = (c) => ({ APPROVAL: '📋', SYSTEM: '⚙️', WARN: '⚠️' }[c] || '📨')
const loadInbox = async () => {
  try {
    const [list, cnt] = await Promise.all([
      commonApi.inbox({ page_size: 20 }),
      commonApi.inboxUnread()
    ])
    const d = list?.data || list || {}
    inboxList.value = d.results || d || []
    if (!Array.isArray(inboxList.value)) inboxList.value = []
    inboxUnread.value = cnt?.data?.count ?? cnt?.count ?? 0
  } catch (e) { /* 静默 */ }
}
const openInbox = async (m) => {
  if (!m.is_read) {
    try { await commonApi.inboxMarkRead(m.id) } catch (e) {}
    m.is_read = true
    inboxUnread.value = Math.max(0, inboxUnread.value - 1)
  }
  if (m.link) router.push(m.link)
}
const markAllRead = async () => {
  try {
    await commonApi.inboxMarkAll()
    inboxList.value.forEach((m) => (m.is_read = true))
    inboxUnread.value = 0
  } catch (e) {}
}

const asList = (r) => {
  if (!r) return []
  if (Array.isArray(r)) return r
  if (Array.isArray(r.results)) return r.results
  if (r.data) {
    if (Array.isArray(r.data)) return r.data
    if (Array.isArray(r.data.results)) return r.data.results
  }
  return []
}

const mq = window.matchMedia('(max-width: 992px)')
const onResize = () => { isMobile.value = mq.matches }
const onToggle = () => { isMobile.value ? (drawer.value = true) : (collapsed.value = !collapsed.value) }

const go = (path) => router.push(path)
let inboxTimer = null

const handleCommand = (cmd) => {
  if (cmd === 'logout') {
    ElMessageBox.confirm('确认退出登录？', '提示', { type: 'warning' }).then(() => {
      store.logout()
      router.push('/login')
    }).catch(() => {})
  } else if (cmd === 'profile') {
    router.push('/system/profile')
  }
}

const loadMessages = async () => {
  try {
    const todo = await dashApi.todo()
    msgItems.value[0].count = todo.pending_approvals || 0
    msgItems.value[1].count = todo.overdue_accounting_tasks || 0
  } catch (e) {}
  try {
    const sc = await salesApi.expiringCustomers({ days: 30 })
    msgItems.value[2].count = asList(sc).length
    const ac = await accApi.expiringClients({ days: 60 })
    msgItems.value[3].count = asList(ac).length
  } catch (e) {}
}

onMounted(() => {
  onResize()
  mq.addEventListener('change', onResize)
  loadMessages()
  loadInbox()
  inboxTimer = setInterval(loadInbox, 60000)
})
onBeforeUnmount(() => { mq.removeEventListener('change', onResize); if (inboxTimer) clearInterval(inboxTimer) })
</script>

<style scoped>
.layout { height: 100vh; }

/* ---------------- 侧边栏：深空灰蓝，衬托柔和高亮 ---------------- */
.aside {
  background:
    radial-gradient(420px 220px at 50% -8%, rgba(74, 111, 165, 0.30) 0%, rgba(13, 17, 23, 0) 70%),
    linear-gradient(180deg, #151a22 0%, #12161d 52%, #0e1218 100%);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  transition: width 0.24s var(--ease-out);
  display: flex; flex-direction: column;
  position: relative;
}
/* 右侧 1px 渐变描边：顶部蓝、底部微亮 —— 侧栏的「层次」签名 */
.aside::after {
  content: ''; position: absolute; inset: 0 0 0 auto; width: 1px;
  background: linear-gradient(180deg,
    rgba(128, 158, 202, 0.42) 0%,
    rgba(128, 158, 202, 0.10) 34%,
    rgba(128, 158, 202, 0.16) 78%,
    rgba(128, 158, 202, 0.36) 100%);
  pointer-events: none;
}

.logo {
  height: 64px; display: flex; align-items: center; gap: 12px;
  padding: 0 18px; flex-shrink: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
}
.logo::after {
  content: ''; position: absolute; left: 18px; right: 18px; bottom: -1px; height: 1px;
  background: linear-gradient(90deg, rgba(200, 164, 77, 0.42), rgba(200, 164, 77, 0));
}
.logo.mini { justify-content: center; padding: 0; }
.logo-mark {
  width: 36px; height: 36px; border-radius: 11px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 17px; font-weight: 700; color: #fff;
  background: linear-gradient(150deg, #6c93c8 0%, #4a6fa5 52%, #33517d 100%);
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow:
    0 6px 18px -6px rgba(74, 111, 165, 0.8),
    inset 0 1px 0 rgba(255, 255, 255, 0.30),
    0 0 0 3px rgba(255, 255, 255, 0.04);
  position: relative;
}
/* 徽标右上角一颗微光点 */
.logo-mark::after {
  content: ''; position: absolute; top: -2px; right: -2px;
  width: 7px; height: 7px; border-radius: 50%;
  background: linear-gradient(135deg, #bcd0e8, #8babd4);
  box-shadow: 0 0 0 2px #151a22, 0 0 8px rgba(128, 158, 202, 0.8);
}
.logo-text { display: flex; flex-direction: column; min-width: 0; }
.logo-name {
  font-size: 15px; font-weight: 700; color: #fff; letter-spacing: -0.2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.logo-sub {
  font-size: 10px; color: rgba(200, 164, 77, 0.92);
  letter-spacing: 1.6px; margin-top: 3px; font-weight: 500;
}
.drawer-logo { border-bottom: 1px solid rgba(255, 255, 255, 0.07); }

.aside-foot {
  flex-shrink: 0; padding: 13px 20px 15px; font-size: 11px;
  color: rgba(226, 236, 248, 0.38); display: flex; align-items: center; gap: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.055);
  letter-spacing: 0.02em;
}
.aside-foot .dot {
  width: 6px; height: 6px; border-radius: 50%; background: #17a06c;
  box-shadow: 0 0 0 3px rgba(23, 160, 108, 0.16);
  animation: pulse-dot 2.6s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 3px rgba(23, 160, 108, 0.16); }
  50% { box-shadow: 0 0 0 5px rgba(23, 160, 108, 0.06); }
}

/* 侧栏内菜单 */
.aside :deep(.el-menu),
.side-drawer :deep(.el-menu) {
  --el-menu-bg-color: transparent;
  --el-menu-text-color: rgba(226, 236, 248, 0.74);
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.06);
  --el-menu-active-color: #ffffff;
  --el-menu-item-height: 42px;
  --el-menu-sub-item-height: 38px;
  border-right: none;
  padding: 12px 11px 28px;
  background: transparent;
}
.aside :deep(.el-menu-item),
.aside :deep(.el-sub-menu__title),
.side-drawer :deep(.el-menu-item),
.side-drawer :deep(.el-sub-menu__title) {
  position: relative;
  border-radius: 10px; margin: 2px 0; height: 42px; line-height: 42px;
  font-size: 13.5px; font-weight: 500; letter-spacing: 0.02em;
  transition: background var(--dur-base) var(--ease-out),
              color var(--dur-base) var(--ease-out),
              transform 220ms var(--ease-spring);
}
.side-drawer :deep(.el-menu-item),
.side-drawer :deep(.el-sub-menu__title) { height: 40px; line-height: 40px; }

/* 一级分组标题：弱化为「分区标签」，视觉层级立刻清晰 */
.aside :deep(.el-menu > .el-sub-menu > .el-sub-menu__title) {
  font-size: 12.5px;
  color: rgba(226, 236, 248, 0.56);
  letter-spacing: 0.06em;
  font-weight: 600;
}

.aside :deep(.el-menu-item:hover),
.aside :deep(.el-sub-menu__title:hover),
.side-drawer :deep(.el-menu-item:hover),
.side-drawer :deep(.el-sub-menu__title:hover) {
  background: rgba(255, 255, 255, 0.065); color: #fff;
}
.aside :deep(.el-menu-item:active) { transform: scale(0.985); }

/* 激活项：柔和蓝高亮 + 内描边 + 左侧竖条 */
.aside :deep(.el-menu-item.is-active),
.side-drawer :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(108, 147, 200, 0.30), rgba(108, 147, 200, 0.10));
  color: #fff; font-weight: 600;
  box-shadow:
    inset 0 0 0 1px rgba(155, 184, 217, 0.24),
    0 6px 18px -10px rgba(74, 111, 165, 0.6);
}
.aside :deep(.el-menu-item.is-active)::before,
.side-drawer :deep(.el-menu-item.is-active)::before {
  content: ''; position: absolute; left: -1px; top: 50%; transform: translateY(-50%);
  width: 3px; height: 18px; border-radius: 0 3px 3px 0;
  background: linear-gradient(180deg, #b6cbe4, #8babd4);
  box-shadow: 0 0 10px rgba(128, 158, 202, 0.5);
}
.aside :deep(.el-sub-menu.is-active > .el-sub-menu__title),
.side-drawer :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: rgba(255, 255, 255, 0.95);
}
.aside :deep(.el-menu--collapse .el-menu-item),
.aside :deep(.el-menu--collapse .el-sub-menu__title) { justify-content: center; padding: 0 !important; }
.aside :deep(.el-icon) { font-size: 17px; }
.aside :deep(.el-scrollbar) { flex: 1; min-height: 0; }
/* 子菜单箭头更小更轻 */
.aside :deep(.el-sub-menu__icon-arrow) { font-size: 11px; right: 14px; opacity: 0.6; }

/* ---------------- 顶栏 ---------------- */
.body { min-width: 0; }
.header {
  height: 64px; flex-shrink: 0;
  background: var(--header-bg);
  backdrop-filter: saturate(180%) blur(18px);
  -webkit-backdrop-filter: saturate(180%) blur(18px);
  border-bottom: 1px solid var(--border-soft);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.5), 0 4px 18px -18px rgba(15, 31, 51, 0.6);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  position: relative; z-index: 10;
}
html.dark .header { box-shadow: 0 1px 0 rgba(255, 255, 255, 0.03); }
.header .left { display: flex; align-items: center; gap: 16px; min-width: 0; }
.toggle {
  width: 34px; height: 34px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: var(--text-sub);
  transition: all var(--dur-fast) var(--ease-out);
  flex-shrink: 0; font-size: 18px;
  border: 1px solid transparent;
}
.toggle:hover {
  background: var(--card-bg); color: var(--primary);
  border-color: var(--border-soft);
  box-shadow: 0 2px 8px -4px rgba(15, 31, 51, 0.18);
}

.crumb { display: flex; align-items: center; gap: 9px; font-size: 13.5px; min-width: 0; }
.crumb-group {
  color: var(--text-sub); font-weight: 550; white-space: nowrap;
  background: var(--surface-3);
  padding: 3px 10px; border-radius: 20px;
  border: 1px solid var(--border-soft);
  font-size: 12px; letter-spacing: 0.02em;
}
.crumb-sep { color: var(--text-faint); font-size: 12px; }
.crumb-cur {
  color: var(--text-main); font-weight: 650; letter-spacing: -0.15px;
  white-space: nowrap; font-size: 14.5px;
}

.header .right { display: flex; align-items: center; gap: 10px; }
.icon-btn {
  width: 36px; height: 36px; border-radius: 10px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-sub);
  transition: all var(--dur-fast) var(--ease-out);
  border: 1px solid transparent;
}
.icon-btn:hover {
  background: var(--card-bg); color: var(--primary);
  border-color: var(--border-soft);
  box-shadow: 0 2px 8px -4px rgba(15, 31, 51, 0.18);
}
.v-divider { width: 1px; height: 22px; background: var(--border); margin: 0 2px; }

.user {
  display: flex; align-items: center; gap: 10px; cursor: pointer;
  outline: none; padding: 5px 10px 5px 5px; border-radius: 12px;
  transition: all var(--dur-fast) var(--ease-out);
  border: 1px solid transparent;
}
.user:hover {
  background: var(--card-bg); border-color: var(--border-soft);
  box-shadow: 0 2px 10px -5px rgba(15, 31, 51, 0.18);
}
.avatar {
  background: linear-gradient(140deg, #6c93c8, #33517d) !important;
  color: #fff !important; font-weight: 650; font-size: 13px;
  box-shadow: 0 3px 10px -3px rgba(42, 79, 212, 0.62),
              inset 0 1px 0 rgba(255, 255, 255, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.2);
}
.u-meta { display: flex; flex-direction: column; line-height: 1.25; }
.uname { font-size: 13.5px; font-weight: 600; color: var(--text-main); letter-spacing: -0.1px; }
.urole { font-size: 11px; color: var(--text-weak); margin-top: 2px; }
.caret { font-size: 11px; color: var(--text-faint); transition: color var(--dur-fast); }
.user:hover .caret { color: var(--primary); }

.main {
  padding: 0;
  background: var(--page-bg);
  overflow-y: auto;
}
.todo-badge { margin-right: 6px; }

.site-footer {
  background: transparent; border-top: 1px solid var(--border-soft);
  padding: 14px 16px; text-align: center; font-size: 11.5px;
  color: var(--text-faint); letter-spacing: 0.02em;
  display: flex; justify-content: center; align-items: center; gap: 10px; flex-wrap: wrap;
}
.beian-link { color: var(--text-faint); text-decoration: none; transition: color var(--dur-fast); }
.beian-link:hover { color: var(--primary); }
.beian-sep { color: var(--border); }
</style>

<style>
/* 移动端抽屉深色底 */
.side-drawer .el-drawer__body {
  padding: 0;
  background:
    radial-gradient(360px 200px at 50% -6%, rgba(74, 111, 165, 0.28) 0%, rgba(13, 17, 23, 0) 70%),
    linear-gradient(180deg, #151a22, #0e1218);
}

/* 消息中心弹层 */
.msg-pop { padding: 14px 14px 8px !important; }
.msg-pop .msg-head {
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 14px; font-weight: 700; padding: 2px 4px 12px;
  border-bottom: 1px solid var(--border-soft);
  letter-spacing: -0.1px;
}
.msg-pop .msg-head small { font-size: 11px; color: var(--text-weak); font-weight: 400; }
.msg-pop .msg-list { max-height: 340px; overflow-y: auto; margin-top: 8px; }
.msg-empty { text-align: center; color: var(--text-weak); font-size: 13px; padding: 28px 0; }
.msg-item.unread { background: var(--primary-50); }
.msg-item .dot-new {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  background: var(--danger-500); margin-right: 7px; vertical-align: middle;
  box-shadow: 0 0 0 2px rgba(220, 74, 61, 0.14);
}
.msg-item .msg-time { font-size: 11px; color: var(--text-faint); margin-top: 3px; }
.msg-clip { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px; }
.msg-pop .msg-item {
  display: flex; align-items: center; gap: 11px; padding: 10px 9px; cursor: pointer;
  border-radius: 10px; transition: background var(--dur-fast);
}
.msg-pop .msg-item:hover { background: var(--primary-50); }
.msg-pop .msg-icon {
  font-size: 15px; width: 34px; height: 34px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--surface-2); border-radius: 10px;
  border: 1px solid var(--border-soft);
}
.msg-pop .msg-body { flex: 1; min-width: 0; }
.msg-pop .msg-label { font-size: 13px; font-weight: 600; color: var(--text-main); }
.msg-pop .msg-sub { font-size: 11.5px; color: var(--text-weak); margin-top: 2px; }
.msg-pop .msg-count {
  background: var(--danger); color: #fff; font-size: 11px; font-weight: 650;
  min-width: 20px; height: 20px; border-radius: 10px; padding: 0 6px;
  display: flex; align-items: center; justify-content: center;
  font-variant-numeric: tabular-nums;
}
.msg-pop .lv-warning .msg-count { background: var(--warning); }
</style>
