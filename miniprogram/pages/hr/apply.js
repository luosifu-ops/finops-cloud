const app = getApp()

const COMPENSATE = [{ value: 'OFF', label: '调休' }, { value: 'MONEY', label: '加班费' }]
const SEAL = [
  { value: 'CONTRACT', label: '合同章' },
  { value: 'FINANCE', label: '财务章' },
  { value: 'LEGAL', label: '公章' },
  { value: 'INVOICE', label: '发票章' }
]
const TYPES = [
  { key: 'OVERTIME', label: '加班', ep: 'overtimes', owner: 'user' },
  { key: 'TRAVEL', label: '出差', ep: 'travels', owner: 'user' },
  { key: 'PURCHASE', label: '采购', ep: 'purchases', owner: 'applicant' },
  { key: 'SEAL', label: '用印', ep: 'seals', owner: 'applicant' }
]
const DEFAULTS = {
  start_at: '', end_at: '', hours: '', reason: '', compensateIndex: 0,
  destination: '', days: '', budget: '',
  item_name: '', spec: '', quantity: '', amount: '', purpose: '', supplier: '',
  sealIndex: 0, doc_name: '', use_date: ''
}

Page({
  data: {
    types: TYPES, compensate: COMPENSATE, seal: SEAL,
    type: 'OVERTIME', form: Object.assign({}, DEFAULTS), submitting: false
  },

  switchType(e) { this.setData({ type: e.currentTarget.dataset.key }) },

  onStart(e) { this.setData({ 'form.start_at': e.detail.value }) },
  onEnd(e) { this.setData({ 'form.end_at': e.detail.value }) },
  onHours(e) { this.setData({ 'form.hours': e.detail.value }) },
  onReason(e) { this.setData({ 'form.reason': e.detail.value }) },
  onComp(e) { this.setData({ 'form.compensateIndex': Number(e.detail.value) }) },
  onDest(e) { this.setData({ 'form.destination': e.detail.value }) },
  onDays(e) { this.setData({ 'form.days': e.detail.value }) },
  onBudget(e) { this.setData({ 'form.budget': e.detail.value }) },
  onItem(e) { this.setData({ 'form.item_name': e.detail.value }) },
  onSpec(e) { this.setData({ 'form.spec': e.detail.value }) },
  onQty(e) { this.setData({ 'form.quantity': e.detail.value }) },
  onAmount(e) { this.setData({ 'form.amount': e.detail.value }) },
  onPurpose(e) { this.setData({ 'form.purpose': e.detail.value }) },
  onSupplier(e) { this.setData({ 'form.supplier': e.detail.value }) },
  onSeal(e) { this.setData({ 'form.sealIndex': Number(e.detail.value) }) },
  onDoc(e) { this.setData({ 'form.doc_name': e.detail.value }) },
  onUseDate(e) { this.setData({ 'form.use_date': e.detail.value }) },

  submit() {
    const t = this.data.type
    const f = this.data.form
    const uid = (app.globalData.user && app.globalData.user.id) || ''
    let payload = {}, ok = true, msg = ''
    if (t === 'OVERTIME') {
      if (!f.start_at || !f.end_at || !f.hours) { ok = false; msg = '请填齐起止时间与时长' }
      payload = { start_at: f.start_at + ' 09:00:00', end_at: f.end_at + ' 18:00:00', hours: f.hours, reason: f.reason, compensate: COMPENSATE[f.compensateIndex].value, user: uid }
    } else if (t === 'TRAVEL') {
      if (!f.destination || !f.start_at || !f.end_at || !f.days) { ok = false; msg = '请填齐目的地/起止/天数' }
      payload = { destination: f.destination, start_at: f.start_at + ' 09:00:00', end_at: f.end_at + ' 18:00:00', days: f.days, reason: f.reason, budget: f.budget || 0, user: uid }
    } else if (t === 'PURCHASE') {
      if (!f.item_name || !f.amount) { ok = false; msg = '请填齐物品与金额' }
      payload = { item_name: f.item_name, spec: f.spec, quantity: f.quantity || 1, amount: f.amount, purpose: f.purpose, supplier: f.supplier, applicant: uid }
    } else if (t === 'SEAL') {
      if (!f.doc_name || !f.use_date) { ok = false; msg = '请填齐用印文件与日期' }
      payload = { seal_type: SEAL[f.sealIndex].value, doc_name: f.doc_name, reason: f.reason, use_date: f.use_date, applicant: uid }
    }
    if (!ok) { wx.showToast({ title: msg, icon: 'none' }); return }
    const ep = TYPES.find(x => x.key === t).ep
    this.setData({ submitting: true })
    app.request('/hr/' + ep + '/', 'POST', payload)
      .then(() => { wx.showToast({ title: '已提交，待审批', icon: 'success' }); this.setData({ type: t, form: Object.assign({}, DEFAULTS), submitting: false }) })
      .catch(() => { this.setData({ submitting: false }) })
  }
})
