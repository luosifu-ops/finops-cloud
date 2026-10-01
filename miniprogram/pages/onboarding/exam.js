const app = getApp()

Page({
  data: { list: [] },
  onShow() { this.load() },
  load() {
    app.request('/onboarding/exams/')
      .then(r => { const { list } = app.parseList(r); this.setData({ list }) })
      .catch(() => this.setData({ list: [] }))
  },
  open(e) { wx.navigateTo({ url: '/pages/onboarding/examDetail?id=' + e.currentTarget.dataset.id }) }
})
