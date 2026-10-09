const app = getApp()

const LEAVE_TYPES = [
  { value: 'PERSONAL', label: '事假' },
  { value: 'SICK', label: '病假' },
  { value: 'ANNUAL', label: '年假' },
  { value: 'OFF', label: '调休' },
  { value: 'MARRIAGE', label: '婚假' },
  { value: 'MATERNITY', label: '产假' },
  { value: 'FUNERAL', label: '丧假' },
  { value: 'OTHER', label: '其他' }
]

Page({
  data: {
    list: [],
    showForm: false,
    types: LEAVE_TYPES,
    form: { typeIndex: 0, start_at: '', end_at: '', days: '', reason: '' },
    submitting: false
  },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/hr/leaves/')
      .then(r => { const { list } = app.parseList(r); this.setData({ list }) })
      .catch(() => this.setData({ list: [] }))
      .then(() => done && done())
  },

  toggleForm() { this.setData({ showForm: !this.data.showForm }) },

  onType(e) { this.setData({ 'form.typeIndex': Number(e.detail.value) }) },
  onStart(e) { this.setData({ 'form.start_at': e.detail.value }) },
  onEnd(e) { this.setData({ 'form.end_at': e.detail.value }) },
  onDays(e) { this.setData({ 'form.days': e.detail.value }) },
  onReason(e) { this.setData({ 'form.reason': e.detail.value }) },

  submit() {
    const f = this.data.form
    if (!f.start_at || !f.end_at || !f.days) {
      wx.showToast({ title: '请填齐起止时间与天数', icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    // 2026-10-02 增量：提交前申请一次性订阅授权（用于审批结果推送）；未填模板 ID 则静默跳过
    app.askSubscribe()
    const payload = {
      leave_type: LEAVE_TYPES[f.typeIndex].value,
      start_at: f.start_at + ' 09:00:00',
      end_at: f.end_at + ' 18:00:00',
      days: f.days,
      reason: f.reason
    }
    app.request('/hr/leaves/', 'POST', payload)
      .then(() => {
        wx.showToast({ title: '已提交，待审批', icon: 'success' })
        this.setData({
          showForm: false,
          form: { typeIndex: 0, start_at: '', end_at: '', days: '', reason: '' }
        })
        this.load()
      })
      .catch(() => {})
      .then(() => this.setData({ submitting: false }))
  }
})
