const app = getApp()

Page({
  data: { progress: { required_total: 0, finished_count: 0, completion_rate: 0 }, error: '' },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    this.setData({ error: '' })
    app.request('/onboarding/articles/my-progress/')
      .then(d => this.setData({ progress: d || this.data.progress }))
      .catch(err => this.setData({ error: (err && err.message) ? String(err.message) : '加载失败' }))
      .then(() => done && done())
  },

  go(e) { wx.navigateTo({ url: e.currentTarget.dataset.url }) }
})
