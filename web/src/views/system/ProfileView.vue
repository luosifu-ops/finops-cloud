<template>
  <div class="profile-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">个人中心</h2>
        <span class="page-tip">维护个人信息与登录密码；手机号绑定后可用于短信验证码登录</span>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左：头像卡片 -->
      <el-col :span="8">
        <el-card shadow="never">
          <div class="avatar-box">
            <el-upload :show-file-list="false" accept="image/*" :before-upload="onAvatar">
              <el-avatar :size="88" :src="avatarUrl" class="avatar">{{ nameChar }}</el-avatar>
              <div class="avatar-tip">点击头像更换</div>
            </el-upload>
            <div class="uname">{{ user?.display_name || user?.username }}</div>
            <el-tag size="small" type="primary" effect="plain">{{ user?.role_name || user?.role }}</el-tag>
            <div class="dept">{{ user?.department_name || '未分配部门' }}</div>
          </div>
        </el-card>
      </el-col>

      <!-- 右：信息编辑 + 改密码 -->
      <el-col :span="16">
        <el-card shadow="never" style="margin-bottom:16px">
          <template #header><b>基本信息</b></template>
          <el-form :model="form" label-width="90px" style="max-width:480px">
            <el-form-item label="登录账号">
              <el-input :model-value="user?.username" disabled />
            </el-form-item>
            <el-form-item label="显示姓名">
              <el-input v-model="form.display_name" placeholder="用于全站展示的姓名" maxlength="20" />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="form.phone" placeholder="用于短信验证码登录" maxlength="11" />
            </el-form-item>
            <el-form-item label="部门/岗位">
              <el-input :model-value="`${user?.department_name || '-'} / ${user?.position_name || user?.role_name || '-'}`" disabled />
            </el-form-item>
            <el-form-item label="入职日期">
              <el-input :model-value="user?.entry_date || '-'" disabled />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveProfile">保存修改</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never">
          <template #header><b>修改密码</b></template>
          <el-form :model="pwd" label-width="90px" style="max-width:480px">
            <el-form-item label="原密码" required>
              <el-input v-model="pwd.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" required>
              <el-input v-model="pwd.new_password" type="password" show-password placeholder="至少 8 位，含字母和数字" />
            </el-form-item>
            <el-form-item label="确认新密码" required>
              <el-input v-model="pwd.confirm" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="warning" :loading="pwdSaving" @click="savePassword">确认修改</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { authApi } from '@/api'
import { useUserStore } from '@/store/user'

const store = useUserStore()
const user = ref(store.userInfo || null)
const saving = ref(false)
const form = reactive({ display_name: '', phone: '' })
const pwd = reactive({ old_password: '', new_password: '', confirm: '' })
const pwdSaving = ref(false)

const API_BASE = import.meta.env.VITE_API_BASE || ''
const avatarUrl = computed(() => {
  const a = user.value?.avatar || user.value?.wx_avatar
  if (!a) return ''
  return String(a).startsWith('http') ? a : API_BASE + a
})
const nameChar = computed(() => (user.value?.display_name || user.value?.username || '?').charAt(0))

async function loadMe() {
  try {
    const r = await authApi.me()
    user.value = r?.data || r || user.value
    form.display_name = user.value?.display_name || ''
    form.phone = user.value?.phone || ''
  } catch (e) { /* 拦截器已提示 */ }
}

async function saveProfile() {
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('display_name', form.display_name || '')
    fd.append('phone', form.phone || '')
    const r = await authApi.updateMe(fd)
    if (r?.code === 0) {
      user.value = r.data
      if (store.userInfo) Object.assign(store.userInfo, r.data)
      else store.setAuth(localStorage.getItem('token'), r.data)
      localStorage.setItem('user', JSON.stringify(store.userInfo))
      ElMessage.success('已保存')
    } else {
      ElMessage.error(r?.msg || '保存失败')
    }
  } catch (e) { /* 拦截器已提示 */ } finally { saving.value = false }
}

async function onAvatar(file) {
  if (file.size > 3 * 1024 * 1024) { ElMessage.warning('头像不能超过 3MB'); return false }
  const fd = new FormData()
  fd.append('avatar', file)
  saving.value = true
  try {
    const r = await authApi.updateMe(fd)
    if (r?.code === 0) { user.value = r.data; ElMessage.success('头像已更新') }
  } catch (e) { /* 拦截器已提示 */ } finally { saving.value = false }
  return false
}

async function savePassword() {
  if (!pwd.old_password || !pwd.new_password) return ElMessage.warning('请填写原密码和新密码')
  if (pwd.new_password.length < 8) return ElMessage.warning('新密码至少 8 位')
  if (pwd.new_password !== pwd.confirm) return ElMessage.warning('两次输入的新密码不一致')
  pwdSaving.value = true
  try {
    const r = await authApi.changePassword({ old_password: pwd.old_password, new_password: pwd.new_password })
    if (r?.code === 0) {
      ElMessage.success('密码已修改，下次登录请使用新密码')
      pwd.old_password = ''; pwd.new_password = ''; pwd.confirm = ''
    } else {
      ElMessage.error(r?.msg || '修改失败')
    }
  } catch (e) { /* 拦截器已提示 */ } finally { pwdSaving.value = false }
}

onMounted(loadMe)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.page-title { font-size: 18px; margin: 0; }
.page-tip { font-size: 12px; color: var(--text-sub); font-weight: 400; }
.avatar-box { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 8px 0; }
.avatar { cursor: pointer; font-size: 30px; background: var(--primary, #3a7afe); }
.avatar-tip { font-size: 12px; color: var(--text-sub); }
.uname { font-size: 16px; font-weight: 700; margin-top: 4px; }
.dept { font-size: 12px; color: var(--text-sub); }
</style>
