const app = getApp()

Page({
  data: { list: [] },
  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    // 入职须知确认清单（后端 regulations 有真实数据）
    app.request('/onboarding/regulations/')
      .then(r => { const { list } = app.parseList(r); this.setData({ list: list.map(x => ({ ...x, acked: false })) }) })
      .catch(() => this.setData({ list: [] }))
      .then(() => done && done())
  },

  ack(e) {
    const id = e.currentTarget.dataset.id
    app.request('/onboarding/regulations/' + id + '/ack/', 'POST', {})
      .then(() => {
        const list = this.data.list.map(x => x.id === id ? { ...x, acked: true } : x)
        this.setData({ list })
        wx.showToast({ title: '已确认', icon: 'success' })
      })
      .catch(() => {})
  }
})
