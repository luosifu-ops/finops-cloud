const app = getApp()

Page({
  data: {
    username: 'admin',
    password: 'admin123',
    loading: false
  },

  onUser(e) { this.setData({ username: e.detail.value }) },
  onPwd(e) { this.setData({ password: e.detail.value }) },

  onLogin() {
    const { username, password } = this.data
    if (!username || !password) {
      wx.showToast({ title: '请输入账号密码', icon: 'none' })
      return
    }
    this.setData({ loading: true })
    app.request('/accounts/auth/login/', 'POST', { username, password })
      .then(d => {
        app.setAuth(d.access, d.user)
        wx.showToast({ title: '登录成功', icon: 'success' })
        setTimeout(() => wx.switchTab({ url: '/pages/index/index' }), 600)
      })
      .catch(() => {})
      .finally(() => this.setData({ loading: false }))
  },

  onWx() {
    wx.showToast({ title: '演示环境请用账号密码登录', icon: 'none' })
  }
})
