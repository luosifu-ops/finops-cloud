const app = getApp()

Page({
  data: { status: '', list: [] },
  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  filter(e) {
    const s = e.currentTarget.dataset.s
    this.setData({ status: s }, () => this.load())
  },

  load(done) {
    const url = this.data.status ? '/sales/leads/?status=' + this.data.status : '/sales/leads/'
    app.request(url)
      .then(r => { const { list } = app.parseList(r); this.setData({ list }) })
      .catch(() => this.setData({ list: [] }))
      .then(() => done && done())
  },

  open(e) { wx.navigateTo({ url: '/pages/sales/detail?id=' + e.currentTarget.dataset.id }) }
})
