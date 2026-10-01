<template>
  <el-container class="layout">
    <!-- 桌面端侧边栏 -->
    <el-aside v-if="!isMobile" :width="collapsed ? '64px' : '216px'" class="aside">
      <div class="logo">
        <span v-if="!collapsed">{{ brand.name }}</span>
        <span v-else>{{ brand.logoChar }}</span>
      </div>
      <el-scrollbar>
        <SideMenu :collapsed="collapsed" />
      </el-scrollbar>
    </el-aside>

    <!-- 移动端抽屉 -->
    <el-drawer v-else v-model="drawer" direction="ltr" size="220px" :with-header="false" class="side-drawer">
      <div class="logo drawer-logo">{{ brand.name }}</div>
      <el-scrollbar>
        <SideMenu :collapsed="false" />
      </el-scrollbar>
    </el-drawer>

    <el-container>
      <el-header class="header">
        <div class="left">
          <el-icon class="toggle" @click="onToggle">
            <Expand v-if="collapsed && !isMobile" /><Fold v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>{{ $route.meta.title || '首页' }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="right">
          <!-- 消息中心 -->
          <el-popover placement="bottom-end" :width="320" trigger="click" popper-class="msg-pop">
            <template #reference>
              <el-badge :value="msgCount" :hidden="!msgCount" class="todo-badge">
                <el-button text :icon="Bell">消息</el-button>
              </el-badge>
            </template>
            <div class="msg-head">
              <span>消息中心</span>
              <small>经营待办聚合</small>
            </div>
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
          </el-popover>

          <el-dropdown @command="handleCommand">
            <span class="user">
              <el-avatar :size="28">{{ userName.charAt(0) }}</el-avatar>
              <span class="uname">{{ userName }}</span>
              <el-tag size="small" type="primary" effect="plain">{{ roleName }}</el-tag>
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

      <!-- 页脚：备案号（备案通过后由后端 BRAND/ICP_BEIAN 注入，留空不显示） -->
      <footer class="site-footer" v-if="brand.icpBeian || brand.policeBeian">
        <template v-if="brand.icpBeian">
          <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener">{{ brand.icpBeian }}</a>
        </template>
        <template v-if="brand.policeBeian">
          <span class="beian-sep">·</span>{{ brand.policeBeian }}
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
import { Bell, Expand, Fold } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import { brand } from '@/store/brand'
import { dashApi, salesApi, accApi } from '@/api'
import SideMenu from '@/components/SideMenu.vue'
import AiAssistant from '@/components/AiAssistant.vue'

const router = useRouter()
const store = useUserStore()
const collapsed = ref(false)
const drawer = ref(false)
const isMobile = ref(false)

const userName = computed(() => store.name)
const roleName = computed(() => store.roleName)

const msgItems = ref([
  { key: 'approval', level: 'danger', icon: '✅', label: '待我审批', count: 0, path: '/hr/approval' },
  { key: 'overdue', level: 'warning', icon: '⏰', label: '逾期做账', count: 0, path: '/accounting/tasks' },
  { key: 'expireSales', level: 'warning', icon: '📝', label: '合同将到期', count: 0, path: '/sales/customers' },
  { key: 'expireAcc', level: 'warning', icon: '📒', label: '代账将到期', count: 0, path: '/accounting/clients' }
])
const msgCount = computed(() => msgItems.value.reduce((s, m) => s + (m.count || 0), 0))

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
})
onBeforeUnmount(() => mq.removeEventListener('change', onResize))
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #fff; border-right: 1px solid var(--border); transition: width .2s; }
.logo {
  height: 56px; display: flex; align-items: center; justify-content: center;
  font-size: 17px; font-weight: 700; color: var(--primary);
  border-bottom: 1px solid var(--border);
}
.drawer-logo { justify-content: flex-start; padding-left: 18px; }
.el-menu { border-right: none; }
.header {
  height: 56px; background: #fff; border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between; padding: 0 18px;
}
.header .left { display: flex; align-items: center; gap: 14px; }
.toggle { font-size: 20px; cursor: pointer; color: var(--text-sub); }
.header .right { display: flex; align-items: center; gap: 16px; }
.user { display: flex; align-items: center; gap: 8px; cursor: pointer; outline: none; }
.uname { font-size: 14px; }
.main { padding: 0; background: var(--page-bg); overflow-y: auto; }
.todo-badge { margin-right: 6px; }
</style>

<style>
.msg-pop .msg-head {
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 14px; font-weight: 700; padding: 4px 4px 10px; border-bottom: 1px solid var(--border);
}
.msg-pop .msg-head small { font-size: 11px; color: var(--text-sub); font-weight: 400; }
.msg-pop .msg-list { max-height: 320px; overflow-y: auto; margin-top: 6px; }
.msg-pop .msg-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 6px; cursor: pointer;
  border-radius: 8px; transition: background .15s;
}
.msg-pop .msg-item:hover { background: var(--primary-50); }
.msg-pop .msg-icon { font-size: 18px; width: 30px; text-align: center; }
.msg-pop .msg-body { flex: 1; }
.msg-pop .msg-label { font-size: 13px; font-weight: 600; }
.msg-pop .msg-sub { font-size: 11px; color: var(--text-sub); margin-top: 2px; }
.msg-pop .msg-count {
  background: var(--danger); color: #fff; font-size: 11px; min-width: 18px; height: 18px;
  border-radius: 9px; padding: 0 5px; display: flex; align-items: center; justify-content: center;
}
.msg-pop .lv-warning .msg-count { background: var(--warning); }
</style>
