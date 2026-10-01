const app = getApp()

Page({
  data: { tab: 'todo', list: [] },
  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ tab }, () => this.load())
  },

  load(done) {
    const url = this.data.tab === 'todo' ? '/hr/approvals/todo/' : '/hr/approvals/my/'
    app.request(url)
      .then(d => {
        const list = (d && d.data) ? d.data : (Array.isArray(d) ? d : [])
        this.setData({ list })
      })
      .catch(() => this.setData({ list: [] }))
      .then(() => done && done())
  },

  open(e) { wx.navigateTo({ url: '/pages/approval/detail?id=' + e.currentTarget.dataset.id }) },

  goCreate() { wx.navigateTo({ url: '/pages/approval/create' }) }
})
