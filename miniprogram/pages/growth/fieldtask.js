const app = getApp()

Page({
  data: { list: [] },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/growth/field-tasks/')
      .then(r => { const { list } = app.parseList(r); this.setData({ list }) })
      .catch(() => this.setData({ list: [] }))
      .then(() => done && done())
  }
})
