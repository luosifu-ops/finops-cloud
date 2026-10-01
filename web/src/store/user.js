import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userInfo: JSON.parse(localStorage.getItem('user') || 'null')
  }),
  getters: {
    isSuper: (s) => !!s.userInfo && !!s.userInfo.is_superuser,
    isBoss: (s) => !!s.userInfo && (s.userInfo.role === 'BOSS' || s.userInfo.is_superuser),
    isManager: (s) => !!s.userInfo && (['BOSS', 'MANAGER'].includes(s.userInfo.role) || s.userInfo.is_superuser),
    isLeader: (s) => !!s.userInfo && (['BOSS', 'MANAGER', 'LEADER'].includes(s.userInfo.role) || s.userInfo.is_superuser),
    isHR: (s) => !!s.userInfo && (['BOSS', 'HR'].includes(s.userInfo.role) || s.userInfo.is_superuser),
    isAdmin: (s) => !!s.userInfo && (['BOSS', 'HR', 'MANAGER'].includes(s.userInfo.role) || s.userInfo.is_superuser),
    deptCode: (s) => (s.userInfo && s.userInfo.department_name) || '',
    deptId: (s) => (s.userInfo && s.userInfo.department) || null,
    name: (s) => (s.userInfo && s.userInfo.display_name) || '未登录',
    roleName: (s) => (s.userInfo && s.userInfo.role_name) || ''
  },
  actions: {
    setAuth(token, userInfo) {
      this.token = token
      this.userInfo = userInfo
      localStorage.setItem('token', token)
      localStorage.setItem('user', JSON.stringify(userInfo))
    },
    logout() {
      this.token = ''
      this.userInfo = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  }
})
