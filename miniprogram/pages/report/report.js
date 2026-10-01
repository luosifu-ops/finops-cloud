const app = getApp()

const EMPTY = {
  today_done: '', today_data: '', problems: '', tomorrow_plan: '', need_help: '', remark: '',
  start_date: '', end_date: '', summary: '', data: '', next_plan: '',
  performance: '', target: '', self_review: ''
}

Page({
  data: {
    tab: 'daily',
    tabName: '日报',
    form: { ...EMPTY },
    list: []
  },

  onShow() { this.loadList() },
  onPullDownRefresh() { this.loadList(() => wx.stopPullDownRefresh()) },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    const name = { daily: '日报', weekly: '周报', monthly: '月报' }[tab]
    this.setData({ tab, tabName: name, form: { ...EMPTY } }, () => this.loadList())
  },

  onInput(e) {
    const k = e.currentTarget.dataset.k
    this.setData({ ['form.' + k]: e.detail.value })
  },

  loadList(done) {
    const map = {
      daily: '/reports/daily-reports/my/',
      weekly: '/reports/weekly-reports/my/',
      monthly: '/reports/monthly-reports/my/'
    }
    app.request(map[this.data.tab])
      .then(d => this.setData({ list: (d && d.data) ? d.data : (Array.isArray(d) ? d : []) }))
      .catch(() => this.setData({ list: [] }))
      .then(() => done && done())
  },

  saveDraft() { this.post('DRAFT') },
  submitReport() { this.post('SUBMITTED') },

  post(status) {
    const tab = this.data.tab
    const base = {
      daily: '/reports/daily-reports/save-or-update/',
      weekly: '/reports/weekly-reports/save-or-update/',
      monthly: '/reports/monthly-reports/save-or-update/'
    }[tab]
    const form = { ...this.data.form, status }
    // 清理空值，避免后端报错
    Object.keys(form).forEach(k => { if (form[k] === '') delete form[k] })
    app.request(base, 'POST', form)
      .then(() => {
        wx.showToast({ title: status === 'SUBMITTED' ? '已提交' : '已保存', icon: 'success' })
        this.setData({ form: { ...EMPTY } })
        this.loadList()
      })
      .catch(() => {})
  }
})
