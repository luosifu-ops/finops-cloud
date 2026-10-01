const app = getApp()

const LEAVE_TYPES = [
  { value: 'PERSONAL', label: '事假' }, { value: 'SICK', label: '病假' },
  { value: 'ANNUAL', label: '年假' }, { value: 'OFF', label: '调休' },
  { value: 'MARRIAGE', label: '婚假' }, { value: 'MATERNITY', label: '产假' },
  { value: 'FUNERAL', label: '丧假' }, { value: 'OTHER', label: '其他' }
]
const CATEGORIES = [
  { value: 'TRAVEL', label: '差旅费' }, { value: 'MEAL', label: '餐饮费' },
  { value: 'OFFICE', label: '办公用品' }, { value: 'CLIENT', label: '客户招待' },
  { value: 'AD', label: '推广费' }, { value: 'OTHER', label: '其他' }
]
const TYPE_LABEL = { LEAVE: '请假', OVERTIME: '加班', TRAVEL: '出差', EXPENSE: '报销' }
const EP = { LEAVE: '/hr/leaves/', OVERTIME: '/hr/overtimes/', TRAVEL: '/hr/travels/', EXPENSE: '/hr/expenses/' }

Page({
  data: {
    type: 'LEAVE',
    leaveTypes: LEAVE_TYPES, leaveIdx: 0,
    categories: CATEGORIES, catIdx: 0,
    startAt: '', endAt: '', days: '', hours: '', destination: '', amount: '', reason: ''
  },

  switchType(e) { this.setData({ type: e.currentTarget.dataset.t }) },

  onLeaveType(e) { this.setData({ leaveIdx: Number(e.detail.value) }) },
  onCategory(e) { this.setData({ catIdx: Number(e.detail.value) }) },
  onStart(e) { this.setData({ startAt: e.detail.value }) },
  onEnd(e) { this.setData({ endAt: e.detail.value }) },
  onDays(e) { this.setData({ days: e.detail.value }) },
  onHours(e) { this.setData({ hours: e.detail.value }) },
  onDest(e) { this.setData({ destination: e.detail.value }) },
  onAmount(e) { this.setData({ amount: e.detail.value }) },
  onReason(e) { this.setData({ reason: e.detail.value }) },

  submit() {
    const d = this.data
    const payload = { status: 'PENDING', reason: d.reason }
    if (d.type === 'LEAVE') {
      payload.leave_type = d.leaveTypes[d.leaveIdx].value
      payload.start_at = d.startAt; payload.end_at = d.endAt; payload.days = Number(d.days) || 0
    } else if (d.type === 'OVERTIME') {
      payload.start_at = d.startAt; payload.end_at = d.endAt; payload.hours = Number(d.hours) || 0
    } else if (d.type === 'TRAVEL') {
      payload.start_at = d.startAt; payload.end_at = d.endAt; payload.days = Number(d.days) || 0; payload.destination = d.destination
    } else if (d.type === 'EXPENSE') {
      payload.category = d.categories[d.catIdx].value; payload.amount = Number(d.amount) || 0
    }

    if ((d.type !== 'EXPENSE') && (!d.startAt || !d.endAt)) {
      wx.showToast({ title: '请选择起止日期', icon: 'none' }); return
    }
    if (d.type === 'EXPENSE' && !d.amount) {
      wx.showToast({ title: '请填写金额', icon: 'none' }); return
    }

    const user = wx.getStorageSync('user') || {}
    const title = (user.display_name || '我') + ' 的' + TYPE_LABEL[d.type] + '申请'

    app.request(EP[d.type], 'POST', payload)
      .then(rec => {
        // 关联创建通用审批单，进入审批流
        return app.request('/hr/approvals/', 'POST', {
          biz_type: d.type, biz_id: rec.id, title, content: d.reason
        })
      })
      .then(() => {
        wx.showToast({ title: '已提交审批', icon: 'success' })
        setTimeout(() => wx.navigateBack(), 600)
      })
      .catch(() => {})
  }
})
