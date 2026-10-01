const app = getApp()

Page({
  data: { list: [], unread: 0 },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/notices/')
      .then(r => {
        const { list } = app.parseList(r)
        this.setData({ list, unread: list.filter(it => !it.is_read).length })
      })
      .catch(() => this.setData({ list: [], unread: 0 }))
      .then(() => done && done())
  },

  open(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.list.find(it => it.id === id)
    if (!item) return
    if (!item.is_read) {
      app.request('/notices/' + id + '/mark_read/', 'POST', {})
        .then(() => {
          const list = this.data.list.map(it => it.id === id ? Object.assign({}, it, { is_read: true }) : it)
          this.setData({ list, unread: list.filter(it => !it.is_read).length })
        })
        .catch(() => {})
    }
    if (item.content) {
      wx.showModal({ title: item.title, content: item.content, showCancel: false, confirmText: '知道了' })
    }
  }
})
