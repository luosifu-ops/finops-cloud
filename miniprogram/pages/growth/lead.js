const app = getApp()

Page({
  data: { list: [] },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/growth/leads/')
      .then(r => { const { list } = app.parseList(r); this.setData({ list }) })
      .catch(() => this.setData({ list: [] }))
      .then(() => done && done())
  },

  call(e) {
    const phone = e.currentTarget.dataset.phone
    if (phone) wx.makePhoneCall({ phoneNumber: phone, fail: () => {} })
  },

  open(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.list.find(it => it.id === id)
    if (item) this.setData({ detail: item })
  },

  closeDetail() { this.setData({ detail: null }) }
})
