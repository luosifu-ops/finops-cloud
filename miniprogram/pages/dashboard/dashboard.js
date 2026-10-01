const app = getApp()

// 经营看板：对接 /dashboard/overview/（本月业绩+部门业绩）与 /dashboard/todo/（今日待办）
// 后端信封 {code:0,data:{...}} 已被 app.request 解开，故 r 直接是 data 对象；
// 为兼容个别接口仍带 data 嵌套，统一取 r.data || r。
Page({
  data: {
    month: '',
    perf: null, // {amount, received, receivable, orders, target, completion}
    depts: [],  // [{department_id, department_name, amount, orders, target, completion}]
    todo: null  // {pending_approvals, daily_report_submitted, overdue_accounting_tasks, date}
  },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    app.request('/dashboard/overview/')
      .then(r => {
        const d = (r && r.data) ? r.data : r
        this.setData({
          month: d.month || '',
          perf: d.performance || null,
          depts: d.departments || []
        })
      })
      .catch(() => this.setData({ perf: null, depts: [] }))

    app.request('/dashboard/todo/')
      .then(r => { const d = (r && r.data) ? r.data : r; this.setData({ todo: d || null }) })
      .catch(() => this.setData({ todo: null }))
      .then(() => done && done())
  }
})
