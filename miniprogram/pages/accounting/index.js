const app = getApp()

Page({
  data: { stat: { total: 0, done: 0, overdue: 0, pending: 0 }, tasks: [], error: '' },
  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    this.setData({ error: '' })
    app.request('/accounting/monthly-tasks/')
      .then(r => {
        const { list } = app.parseList(r)
        const today = new Date().toISOString().slice(0, 10)
        const marked = list.map(x => ({ ...x, is_overdue: x.status !== 'DONE' && x.deadline && x.deadline < today }))
        const done = marked.filter(x => x.status === 'DONE').length
        const overdue = marked.filter(x => x.is_overdue).length
        const pending = marked.filter(x => x.status !== 'DONE' && !x.is_overdue).length
        this.setData({
          tasks: marked,
          stat: { total: marked.length, done, overdue, pending }
        })
      })
      .catch(err => this.setData({ tasks: [], error: (err && err.message) ? String(err.message) : '加载失败', stat: { total: 0, done: 0, overdue: 0, pending: 0 } }))
      .then(() => done && done())
  },

  open(e) { wx.navigateTo({ url: '/pages/accounting/task?id=' + e.currentTarget.dataset.id }) }
})
