const app = getApp()

Page({
  data: { cost: 0, leads: 0, platforms: [], campaigns: [] },
  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/ops/platforms/')
      .then(r => { const { list } = app.parseList(r); this.setData({ platforms: list }) })
      .catch(() => this.setData({ platforms: [] }))

    app.request('/ops/campaigns/')
      .then(r => { const { list } = app.parseList(r); this.setData({ campaigns: list.slice(0, 20) }) })
      .catch(() => this.setData({ campaigns: [] }))

    app.request('/ops/daily-stats/')
      .then(r => {
        const { list } = app.parseList(r)
        let cost = 0, leads = 0
        list.forEach(x => { cost += Number(x.cost) || 0; leads += Number(x.lead_count) || 0 })
        this.setData({ cost: Math.round(cost).toLocaleString(), leads })
      })
      .catch(() => this.setData({ cost: 0, leads: 0 }))
      .then(() => done && done())
  },

  goStats() { wx.navigateTo({ url: '/pages/ops/stats' }) }
})
