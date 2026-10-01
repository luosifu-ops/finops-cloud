const app = getApp()

Page({
  data: { id: '', a: { steps: [] }, remark: '' },
  onLoad(q) { this.setData({ id: q.id || '' }) },
  onShow() { this.load() },

  load() {
    app.request('/hr/approvals/' + this.data.id + '/')
      .then(d => this.setData({ a: d || { steps: [] } }))
      .catch(() => this.setData({ a: { steps: [] } }))
  },

  onRemark(e) { this.setData({ remark: e.detail.value }) },

  handle(e) {
    const act = e.currentTarget.dataset.act
    app.request('/hr/approvals/' + this.data.id + '/handle/', 'POST', { action: act, remark: this.data.remark })
      .then(() => {
        wx.showToast({ title: act === 'approve' ? '已同意' : '已驳回', icon: 'success' })
        this.load()
        // 刷新上级列表
        const pages = getCurrentPages()
        const prev = pages[pages.length - 2]
        if (prev && prev.load) setTimeout(() => prev.load(), 400)
      })
      .catch(() => {})
  }
})
