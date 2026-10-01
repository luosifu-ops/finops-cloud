const app = getApp()

Page({
  data: { monthly: null, list: [], loading: true },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/hr/attendance-stats/')
      .then(r => {
        const { list } = app.parseList(r)
        this.setData({ monthly: (list && list.length) ? list[0] : null })
      })
      .catch(() => {})
    app.request('/hr/attendances/')
      .then(r => { const { list } = app.parseList(r); this.setData({ list, loading: false }) })
      .catch(() => this.setData({ list: [], loading: false }))
      .then(() => done && done())
  }
})
