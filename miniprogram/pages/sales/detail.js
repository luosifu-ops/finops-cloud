const app = getApp()

const RESULTS = [
  { value: 'CONNECTED', label: '已接通' },
  { value: 'NO_ANSWER', label: '未接' },
  { value: 'REJECTED', label: '拒接' },
  { value: 'SHUTDOWN', label: '关机/停机' },
  { value: 'WRONG', label: '空号/错号' }
]

Page({
  data: {
    id: '', lead: {}, calls: [],
    results: RESULTS, ri: 0, summary: '', duration: '', hasWechat: false
  },

  onLoad(q) { this.setData({ id: q.id || '' }) },
  onShow() { this.load() },

  load() {
    app.request('/sales/leads/' + this.data.id + '/')
      .then(d => this.setData({ lead: d || {} }))
      .catch(() => {})
    app.request('/sales/call-records/?lead=' + this.data.id)
      .then(r => { const { list } = app.parseList(r); this.setData({ calls: list }) })
      .catch(() => this.setData({ calls: [] }))
  },

  onResult(e) { this.setData({ ri: Number(e.detail.value) }) },
  onSummary(e) { this.setData({ summary: e.detail.value }) },
  onDuration(e) { this.setData({ duration: e.detail.value }) },
  onWechat(e) { this.setData({ hasWechat: e.detail.value }) },

  saveCall() {
    const payload = {
      lead: this.data.id,
      result: this.data.results[this.data.ri].value,
      summary: this.data.summary,
      duration: Number(this.data.duration) || 0,
      has_wechat: this.data.hasWechat
    }
    app.request('/sales/call-records/', 'POST', payload)
      .then(() => {
        wx.showToast({ title: '已保存', icon: 'success' })
        this.setData({ summary: '', duration: '', hasWechat: false })
        this.load()
      })
      .catch(() => {})
  }
})
