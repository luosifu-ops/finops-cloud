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
        this.bindOpenid()   // 2026-10-02 增量：静默绑定 openid（失败不影响登录）
        setTimeout(() => wx.switchTab({ url: '/pages/index/index' }), 600)
      })
      .catch(() => {})
      .finally(() => this.setData({ loading: false }))
  },

  // 2026-10-02 增量：wx.login 拿 code 换 openid 并绑定到当前账号（用于审批结果推送）
  bindOpenid() {
    if (typeof wx.login !== 'function') return
    wx.login({
      success: res => {
        if (!res.code) return
        app.request('/accounts/auth/wx-bind-openid/', 'POST', { code: res.code })
          .catch(() => {})   // 静默失败：未配置凭证时不影响任何功能
      }
    })
  },

  onWx() {
    wx.showToast({ title: '演示环境请用账号密码登录', icon: 'none' })
  }
})
