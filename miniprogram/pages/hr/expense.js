const app = getApp()

const CATEGORIES = [
  { value: 'TRAVEL', label: '差旅费' },
  { value: 'MEAL', label: '餐饮费' },
  { value: 'OFFICE', label: '办公用品' },
  { value: 'CLIENT', label: '客户招待' },
  { value: 'AD', label: '推广费' },
  { value: 'OTHER', label: '其他' }
]

Page({
  data: {
    list: [],
    showForm: false,
    cats: CATEGORIES,
    form: { catIndex: 5, happened_at: '', amount: '', reason: '', invoice_no: '' },
    submitting: false
  },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/hr/expenses/')
      .then(r => { const { list } = app.parseList(r); this.setData({ list }) })
      .catch(() => this.setData({ list: [] }))
      .then(() => done && done())
  },

  toggleForm() { this.setData({ showForm: !this.data.showForm }) },

  onCat(e) { this.setData({ 'form.catIndex': Number(e.detail.value) }) },
  onDate(e) { this.setData({ 'form.happened_at': e.detail.value }) },
  onAmount(e) { this.setData({ 'form.amount': e.detail.value }) },
  onReason(e) { this.setData({ 'form.reason': e.detail.value }) },
  onInvoice(e) { this.setData({ 'form.invoice_no': e.detail.value }) },

  submit() {
    const f = this.data.form
    if (!f.happened_at || !f.amount) {
      wx.showToast({ title: '请填齐发生日期与金额', icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    const payload = {
      category: CATEGORIES[f.catIndex].value,
      happened_at: f.happened_at,
      amount: f.amount,
      reason: f.reason,
      invoice_no: f.invoice_no
    }
    app.request('/hr/expenses/', 'POST', payload)
      .then(() => {
        wx.showToast({ title: '已提交，待审批', icon: 'success' })
        this.setData({
          showForm: false,
          form: { catIndex: 5, happened_at: '', amount: '', reason: '', invoice_no: '' }
        })
        this.load()
      })
      .catch(() => {})
      .then(() => this.setData({ submitting: false }))
  }
})
