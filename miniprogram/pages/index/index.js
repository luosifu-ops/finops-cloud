const app = getApp()

const TAB_PAGES = ['/pages/index/index', '/pages/workbench/workbench', '/pages/report/report', '/pages/mine/mine']

Page({
  data: {
    user: {},
    month: '',
    greeting: '你好',
    perf: { amount: 0, received: 0, completion: 0, orders: 0 },
    depts: [],
    error: '',
    meta: '',
    entries: [
      { label: '写汇报', icon: '📝', color: 'linear-gradient(135deg,#FF6B9D,#FF8FB1)', url: '/pages/report/report' },
      { label: '工作台', icon: '🗂️', color: 'linear-gradient(135deg,#54A0FF,#74B9FF)', url: '/pages/workbench/workbench' },
      { label: '审批', icon: '✅', color: 'linear-gradient(135deg,#1DD1A1,#48DBAF)', url: '/pages/approval/list' },
      { label: '入职培训', icon: '🎓', color: 'linear-gradient(135deg,#A55EEA,#C77DFF)', url: '/pages/onboarding/index' },
      { label: '电销线索', icon: '📞', color: 'linear-gradient(135deg,#FF9F43,#FFB86C)', url: '/pages/sales/list' },
      { label: '客户管理', icon: '🏢', color: 'linear-gradient(135deg,#54A0FF,#74B9FF)', url: '/pages/sales/customers' },
      { label: '合同管理', icon: '📑', color: 'linear-gradient(135deg,#5F7BFF,#8FA0FF)', url: '/pages/sales/contracts' },
      { label: '会计做账', icon: '🧮', color: 'linear-gradient(135deg,#FF6B6B,#FF8E72)', url: '/pages/accounting/index' },
      { label: '纳税申报', icon: '🧾', color: 'linear-gradient(135deg,#FF8E53,#FFB86C)', url: '/pages/accounting/declarations' },
      { label: '运营投放', icon: '📈', color: 'linear-gradient(135deg,#FECA57,#FFB86C)', url: '/pages/ops/index' },
      { label: '会员套餐', icon: '👑', color: 'linear-gradient(135deg,#FECA57,#FFB86C)', url: '/pages/membership/plans' },
      { label: '招商中心', icon: '🤝', color: 'linear-gradient(135deg,#FF6B9D,#FF8FB1)', url: '/pages/investment/index' },
      { label: '我的', icon: '👤', color: 'linear-gradient(135deg,#54A0FF,#A55EEA)', url: '/pages/mine/mine' }
    ]
  },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    this.setData({ error: '', meta: '请求中…' })
    const user = wx.getStorageSync('user') || {}
    const h = new Date().getHours()
    const greeting = h < 11 ? '早上好' : h < 14 ? '中午好' : h < 18 ? '下午好' : '晚上好'
    this.setData({ user, greeting })
    app.request('/dashboard/overview/')
      .then(d => {
        const perf = d.performance || {}
        this.setData({
          month: d.month || '',
          perf: {
            amount: this.fmt(perf.amount),
            received: this.fmt(perf.received),
            completion: perf.completion || 0,
            orders: perf.orders || 0
          },
          depts: d.departments || [],
          meta: '✅ 接口 ' + ((app._diag && app._diag.status) || '') + ' · 部门 ' + (d.departments || []).length + ' 个'
        })
      })
      .catch(err => { this.setData({ error: (err && err.message) ? String(err.message) : '加载失败', meta: '❌ 失败' }) })
      .then(() => done && done())
  },

  fmt(n) {
    n = Number(n) || 0
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  },

  go(e) {
    const url = e.currentTarget.dataset.url
    if (TAB_PAGES.indexOf(url) >= 0) wx.switchTab({ url })
    else wx.navigateTo({ url })
  }
})
