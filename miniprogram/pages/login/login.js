const app = getApp()

Page({
  data: {
    // 2026-10-31：移除预填演示账号（提审红线：不得出现演示账号/弱口令），员工用真实账号登录
    username: '',
    password: '',
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

  // 2026-10-31 增量：微信一键登录真实现
  // 已绑定用户：wx.login 拿 code → 后端换 openid → 直接登录进首页
  // 未绑定/未配置凭证：引导先用账号密码登录（登录成功后自动静默绑定）
  onWx() {
    if (typeof wx.login !== 'function') {
      wx.showToast({ title: '请使用账号密码登录', icon: 'none' })
      return
    }
    wx.login({
      success: res => {
        if (!res.code) {
          wx.showToast({ title: '微信登录失败，请用账号密码', icon: 'none' })
          return
        }
        this.setData({ loading: true })
        app.request('/accounts/auth/wx-login/', 'POST', { code: res.code })
          .then(d => {
            if (d && d.access) {
              app.setAuth(d.access, d.user)
              wx.showToast({ title: '登录成功', icon: 'success' })
              setTimeout(() => wx.switchTab({ url: '/pages/index/index' }), 600)
            } else if (d && d.code === 2) {
              wx.showToast({ title: '首次使用请先用账号密码登录', icon: 'none', duration: 2500 })
            } else {
              wx.showToast({ title: (d && d.msg) || '微信登录暂不可用，请用账号密码', icon: 'none', duration: 2500 })
            }
          })
          .catch(() => {})
          .finally(() => this.setData({ loading: false }))
      },
      fail: () => wx.showToast({ title: '请使用账号密码登录', icon: 'none' })
    })
  }
})
