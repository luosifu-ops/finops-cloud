const app = getApp()

Page({
  data: { pid: '', platforms: [], list: [] },
  onShow() { this.loadPlatforms() },
  onPullDownRefresh() { this.loadStats(() => wx.stopPullDownRefresh()) },

  loadPlatforms() {
    app.request('/ops/platforms/')
      .then(r => { const { list } = app.parseList(r); this.setData({ platforms: list }, () => this.loadStats()) })
      .catch(() => this.setData({ platforms: [] }))
  },

  filter(e) {
    const pid = e.currentTarget.dataset.p
    this.setData({ pid }, () => this.loadStats())
  },

  loadStats(done) {
    const url = this.data.pid ? '/ops/daily-stats/?platform=' + this.data.pid : '/ops/daily-stats/'
    app.request(url)
      .then(r => { const { list } = app.parseList(r); this.setData({ list: list.slice(0, 50) }) })
      .catch(() => this.setData({ list: [] }))
      .then(() => done && done())
  }
})
