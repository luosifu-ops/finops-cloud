<template>
  <div class="profile-page">
    <h2>个人中心</h2>
    <el-descriptions :column="2" border v-if="user">
      <el-descriptions-item label="姓名">{{ user.display_name || user.username }}</el-descriptions-item>
      <el-descriptions-item label="账号">{{ user.username }}</el-descriptions-item>
      <el-descriptions-item label="部门">{{ user.department_name || '-' }}</el-descriptions-item>
      <el-descriptions-item label="岗位/角色">{{ user.role_name || user.role }}</el-descriptions-item>
      <el-descriptions-item label="手机号">{{ user.phone || '-' }}</el-descriptions-item>
      <el-descriptions-item label="工号">{{ user.employee_no || '-' }}</el-descriptions-item>
      <el-descriptions-item label="在职状态">{{ user.status || '-' }}</el-descriptions-item>
      <el-descriptions-item label="入职日期">{{ user.entry_date || '-' }}</el-descriptions-item>
    </el-descriptions>
    <el-button class="mt" @click="logout">退出登录</el-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'

const router = useRouter()
const store = useUserStore()
const user = computed(() => store.userInfo)

const logout = () => {
  store.logout()
  router.push('/login')
}
</script>

<style scoped>
.profile-page { padding: 8px; }
.profile-page h2 { font-size: 18px; margin: 0 0 16px; }
.mt { margin-top: 16px; }
</style>
