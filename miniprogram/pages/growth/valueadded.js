const app = getApp()

Page({
  data: { list: [], totalProfit: '0.00' },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/growth/value-added/')
      .then(r => {
        const { list } = app.parseList(r)
        let sum = 0
        list.forEach(it => { sum += Number(it.profit || 0) })
        this.setData({ list, totalProfit: sum.toFixed(2) })
      })
      .catch(() => this.setData({ list: [], totalProfit: '0.00' }))
      .then(() => done && done())
  }
})
