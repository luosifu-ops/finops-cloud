<template>
  <router-view />
</template>

<script setup>
// 2026-11-03 Boss 指示：应用启动时自动刷新当前用户信息。
// 背景：用户信息（含单点权限 can_assign_leads 等）缓存在 localStorage，
// 后端权限调整后老登录态刷新页面拿不到新字段，必须退出重登才生效。
// 现在启动时若有 token，自动调 /accounts/auth/me/ 同步一次，无需重登。
import { onMounted } from 'vue'
import { authApi } from '@/api'
import { useUserStore } from '@/store/user'

const store = useUserStore()

onMounted(async () => {
  if (!store.token) return
  try {
    const r = await authApi.me()
    if (r && r.code === 0 && r.data && r.data.id) {
      const merged = { ...(store.userInfo || {}), ...r.data }
      store.setAuth(store.token, merged)
    }
  } catch (e) { /* 静默：网络/登录态异常时保留本地缓存，由拦截器统一处理 401 */ }
})
</script>
