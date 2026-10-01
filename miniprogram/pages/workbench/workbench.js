const app = getApp()

Page({
  data: {
    date: '',
    today: {},
    approvals: [],
    onboardLeft: 0,
    error: ''
  },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    this.setData({ error: '' })
    const d = new Date()
    const week = '日一二三四五六'
    const date = `${d.getMonth() + 1}月${d.getDate()}日 周${week[d.getDay()]}`
    this.setData({ date })

    app.request('/hr/attendances/today-status/')
      .then(r => this.setData({ today: r || {} }))
      .catch(err => this.setData({ error: (err && err.message) ? String(err.message) : '加载失败' }))

    app.request('/hr/approvals/todo/')
      .then(r => {
        const { list } = app.parseList(r)
        this.setData({ approvals: list.slice(0, 10) })
      })
      .catch(err => this.setData({ error: (err && err.message) ? String(err.message) : '加载失败' }))

    app.request('/onboarding/tasks/my-tasks/')
      .then(d => {
        const data = d || {}
        const list = Array.isArray(data.tasks) ? data.tasks : (Array.isArray(data) ? data : [])
        const left = list.filter(x => !x.done).length
        this.setData({ onboardLeft: left })
      })
      .catch(err => this.setData({ error: (err && err.message) ? String(err.message) : '加载失败' }))
      .then(() => done && done())
  },

  checkIn(e) {
    const type = e.currentTarget.dataset.type
    app.request('/hr/attendances/check-' + type.toLowerCase() + '/', 'POST', {})
      .then(() => {
        wx.showToast({ title: '打卡成功', icon: 'success' })
        this.load()
      })
      .catch(() => {})
  },

  openApproval(e) {
    wx.navigateTo({ url: '/pages/approval/detail?id=' + e.currentTarget.dataset.id })
  },

  goReport() { wx.switchTab({ url: '/pages/report/report' }) },
  goOnboard() { wx.navigateTo({ url: '/pages/onboarding/task' }) }
})
