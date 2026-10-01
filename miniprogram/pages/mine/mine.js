const app = getApp()

const ROLE_MAP = { BOSS: '老板', MANAGER: '经理', HR: '人事', LEADER: '主管', STAFF: '员工' }

Page({
  data: {
    user: {},
    roleName: '',
    approvalCount: 0,
    entries: [
      { label: '审批', icon: '✅', color: 'linear-gradient(135deg,#1DD1A1,#48DBAF)', url: '/pages/approval/list' },
      { label: '入职培训', icon: '🎓', color: 'linear-gradient(135deg,#A55EEA,#C77DFF)', url: '/pages/onboarding/index' },
      { label: '电销线索', icon: '📞', color: 'linear-gradient(135deg,#FF9F43,#FFB86C)', url: '/pages/sales/list' },
      { label: '客户管理', icon: '🏢', color: 'linear-gradient(135deg,#54A0FF,#74B9FF)', url: '/pages/sales/customers' },
      { label: '合同管理', icon: '📑', color: 'linear-gradient(135deg,#5F7BFF,#8FA0FF)', url: '/pages/sales/contracts' },
      { label: '会计做账', icon: '🧮', color: 'linear-gradient(135deg,#FF6B6B,#FF8E72)', url: '/pages/accounting/index' },
      { label: '纳税申报', icon: '🧾', color: 'linear-gradient(135deg,#FF8E53,#FFB86C)', url: '/pages/accounting/declarations' },
      { label: '运营投放', icon: '📈', color: 'linear-gradient(135deg,#FECA57,#FFB86C)', url: '/pages/ops/index' },
      { label: '我的工资条', icon: '💰', color: 'linear-gradient(135deg,#1DD1A1,#48DBAF)', url: '/pages/salary/salary' },
      { label: '企业通讯录', icon: '📇', color: 'linear-gradient(135deg,#54A0FF,#74B9FF)', url: '/pages/directory/directory' },
      { label: '工作台', icon: '🗂️', color: 'linear-gradient(135deg,#54A0FF,#74B9FF)', url: '/pages/workbench/workbench' },
      { label: '考勤打卡', icon: '🕐', color: 'linear-gradient(135deg,#1DD1A1,#48DBAF)', url: '/pages/hr/attendance' },
      { label: '我的请假', icon: '🌴', color: 'linear-gradient(135deg,#FF9F43,#FFB86C)', url: '/pages/hr/leave' },
      { label: '劳动合同', icon: '📄', color: 'linear-gradient(135deg,#A55EEA,#C77DFF)', url: '/pages/hr/contract' },
      { label: '线索公海', icon: '🌊', color: 'linear-gradient(135deg,#54A0FF,#74B9FF)', url: '/pages/growth/pool' },
      { label: '外勤任务', icon: '🚗', color: 'linear-gradient(135deg,#FF9F43,#FFB86C)', url: '/pages/growth/fieldtask' },
      { label: '增值业务', icon: '💎', color: 'linear-gradient(135deg,#A55EEA,#C77DFF)', url: '/pages/growth/valueadded' },
      { label: '公告通知', icon: '📢', color: 'linear-gradient(135deg,#FF6B6B,#FF8E72)', url: '/pages/notices/notices' },
      { label: '报销申请', icon: '🧾', color: 'linear-gradient(135deg,#A55EEA,#C77DFF)', url: '/pages/hr/expense' },
      { label: '我的线索', icon: '🎯', color: 'linear-gradient(135deg,#54A0FF,#74B9FF)', url: '/pages/growth/lead' },
      { label: '经营看板', icon: '📊', color: 'linear-gradient(135deg,#A55EEA,#C77DFF)', url: '/pages/dashboard/dashboard' },
      { label: '审批发起', icon: '📝', color: 'linear-gradient(135deg,#FF9F43,#FFB86C)', url: '/pages/hr/apply' },
      { label: '企业查询', icon: '🔍', color: 'linear-gradient(135deg,#54A0FF,#74B9FF)', url: '/pages/enterprise/enterprise' },
      { label: '会员套餐', icon: '👑', color: 'linear-gradient(135deg,#FECA57,#FFB86C)', url: '/pages/membership/plans' },
      { label: '招商中心', icon: '🤝', color: 'linear-gradient(135deg,#FF6B9D,#FF8FB1)', url: '/pages/investment/index' },
      { label: '工作汇报', icon: '📝', color: 'linear-gradient(135deg,#48DBAF,#1DD1A1)', url: '/pages/report/list' }
    ]
  },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    const user = wx.getStorageSync('user') || {}
    this.setData({
      user,
      roleName: ROLE_MAP[user.role] || (user.is_superuser ? '超级管理员' : '员工')
    })
    app.request('/hr/approvals/todo/')
      .then(d => {
        const list = (d && d.data) ? d.data : (Array.isArray(d) ? d : [])
        this.setData({ approvalCount: list.length })
      })
      .catch(() => {})
      .then(() => done && done())
  },

  go(e) {
    const url = e.currentTarget.dataset.url
    if (url.indexOf('/pages/approval') === 0 || url.indexOf('/pages/onboarding') === 0 ||
        url.indexOf('/pages/sales') === 0 || url.indexOf('/pages/accounting') === 0 ||
        url.indexOf('/pages/ops') === 0 || url.indexOf('/pages/salary') === 0 ||
        url.indexOf('/pages/contacts') === 0 || url.indexOf('/pages/hr') === 0 ||
        url.indexOf('/pages/growth') === 0 || url.indexOf('/pages/notices') === 0 ||
        url.indexOf('/pages/dashboard') === 0 || url.indexOf('/pages/enterprise') === 0 ||
        url.indexOf('/pages/membership') === 0 || url.indexOf('/pages/investment') === 0 ||
        url.indexOf('/pages/report') === 0 || url.indexOf('/pages/directory') === 0) {
      wx.navigateTo({ url })
    } else {
      wx.switchTab({ url })
    }
  },

  logout() {
    wx.showModal({
      title: '确认退出', content: '退出后需重新登录', confirmColor: '#FF5C8A',
      success: (r) => {
        if (r.confirm) {
          app.logout()
          wx.reLaunch({ url: '/pages/login/login' })
        }
      }
    })
  }
})
