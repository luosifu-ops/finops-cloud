const app = getApp()

Page({
  data: { id: '', task: {}, steps: [] },
  onLoad(q) { this.setData({ id: q.id || '' }) },
  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/accounting/monthly-tasks/' + this.data.id + '/')
      .then(d => this.setData({ task: d || {} }))
      .catch(() => {})
    app.request('/accounting/task-steps/?task=' + this.data.id)
      .then(r => { const { list } = app.parseList(r); this.setData({ steps: list }) })
      .catch(() => this.setData({ steps: [] }))
      .then(() => done && done())
  },

  advance(e) {
    const step = e.currentTarget.dataset.step
    app.request('/accounting/monthly-tasks/' + this.data.id + '/advance/', 'POST', { step, status: 'DONE' })
      .then(() => { wx.showToast({ title: '节点完成', icon: 'success' }); this.load() })
      .catch(() => {})
  }
})
