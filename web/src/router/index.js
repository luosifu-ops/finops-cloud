import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  // 入职申请公开页：未登录访客自助提交（Boss 2026-10-28 指示全员申请注册账号）
  { path: '/apply', name: 'public-apply', component: () => import('@/views/hr/EntryApplyView.vue'), meta: { public: true, title: '申请入职' } },
  // 会员支付页：脱离登录布局，微信/支付宝内扫码可直接打开（无需登录）
  { path: '/membership/pay', name: 'membership-pay', component: () => import('@/views/membership/MembershipPayView.vue'), meta: { public: true, title: '支付' } },

  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue'), meta: { title: '经营总览', icon: 'DataLine' } },
      { path: 'about', name: 'about', component: () => import('@/views/AboutView.vue'), meta: { title: '关于我们', icon: 'OfficeBuilding' } },
      { path: 'department/:code', name: 'department', component: () => import('@/views/DepartmentView.vue'), meta: { title: '部门看板', hidden: true } },
      // 2026-10-29 新增：部门业绩核算与统计（各部门业绩自动向上汇总到老板/总经理）
      { path: 'performance/dept', name: 'dept-performance', component: () => import('@/views/DeptPerformanceSummaryView.vue'), meta: { title: '部门业绩核算', icon: 'TrendCharts', leader: true } },

      // ========== 第一梯队：入职与成长（新人时间线：了解公司 → 懂制度 → 办手续 → 学业务 → 考试 → 上岗）==========
      { path: 'onboarding/culture/intro', name: 'culture-intro', component: () => import('@/views/onboarding/culture/IntroView.vue'), meta: { title: '公司简介', group: '入职与成长', parent: '企业文化', icon: 'OfficeBuilding' } },
      { path: 'onboarding/culture/vision', name: 'culture-vision', component: () => import('@/views/onboarding/culture/VisionView.vue'), meta: { title: '愿景使命', group: '入职与成长', parent: '企业文化', icon: 'Sunny' } },
      { path: 'onboarding/culture/history', name: 'culture-history', component: () => import('@/views/onboarding/culture/HistoryView.vue'), meta: { title: '发展历程', group: '入职与成长', parent: '企业文化', icon: 'Histogram' } },
      { path: 'onboarding/culture/story', name: 'culture-story', component: () => import('@/views/onboarding/culture/StoryView.vue'), meta: { title: '团队故事', group: '入职与成长', parent: '企业文化', icon: 'ChatDotRound' } },
      { path: 'onboarding/culture/manage', name: 'culture-manage', component: () => import('@/views/onboarding/culture/ManageView.vue'), meta: { title: '管理理念', group: '入职与成长', parent: '企业文化', icon: 'Medal' } },
      { path: 'onboarding/regulation/attendance', name: 'regulation-attendance', component: () => import('@/views/onboarding/regulation/CategoryView.vue'), meta: { title: '考勤制度', group: '入职与成长', parent: '公司制度', icon: 'Calendar' }, props: () => ({ category: 'ATTENDANCE', title: '考勤制度' }) },
      { path: 'onboarding/regulation/salary', name: 'regulation-salary', component: () => import('@/views/onboarding/regulation/CategoryView.vue'), meta: { title: '薪酬绩效', group: '入职与成长', parent: '公司制度', icon: 'Money' }, props: () => ({ category: 'SALARY', title: '薪酬绩效' }) },
      { path: 'onboarding/regulation/reward', name: 'regulation-reward', component: () => import('@/views/onboarding/regulation/CategoryView.vue'), meta: { title: '奖惩制度', group: '入职与成长', parent: '公司制度', icon: 'Trophy' }, props: () => ({ category: 'REWARD', title: '奖惩制度' }) },
      { path: 'onboarding/regulation/secret', name: 'regulation-secret', component: () => import('@/views/onboarding/regulation/CategoryView.vue'), meta: { title: '保密与合规', group: '入职与成长', parent: '公司制度', icon: 'Lock' }, props: () => ({ category: 'SECRET', title: '保密与合规' }) },
      { path: 'onboarding/regulation/expense', name: 'regulation-expense', component: () => import('@/views/onboarding/regulation/CategoryView.vue'), meta: { title: '费用报销', group: '入职与成长', parent: '公司制度', icon: 'Receipt' }, props: () => ({ category: 'EXPENSE', title: '费用报销' }) },
      { path: 'onboarding/regulation/behavior', name: 'regulation-behavior', component: () => import('@/views/onboarding/regulation/CategoryView.vue'), meta: { title: '行为规范', group: '入职与成长', parent: '公司制度', icon: 'Stamp' }, props: () => ({ category: 'BEHAVIOR', title: '行为规范' }) },
      { path: 'onboarding/regulation/manage', name: 'regulation-manage', component: () => import('@/views/onboarding/regulation/ManageView.vue'), meta: { title: '制度管理', group: '入职与成长', parent: '公司制度', icon: 'Setting' } },
      { path: 'onboarding/profile', name: 'onboarding-profile', component: () => import('@/views/onboarding/ProfileView.vue'), meta: { title: '入职资料', group: '入职与成长', icon: 'Postcard' } },
      { path: 'onboarding/tasks', name: 'onboarding-tasks', component: () => import('@/views/onboarding/TaskView.vue'), meta: { title: '我的入职任务', group: '入职与成长', icon: 'Finished' } },
      { path: 'onboarding/knowledge/agency', name: 'knowledge-agency', component: () => import('@/views/onboarding/knowledge/CategoryView.vue'), meta: { title: '代理记账基础', group: '入职与成长', parent: '专业基础知识', icon: 'OfficeBuilding' }, props: () => ({ category: 'AGENCY', title: '代理记账基础' }) },
      { path: 'onboarding/knowledge/tax', name: 'knowledge-tax', component: () => import('@/views/onboarding/knowledge/CategoryView.vue'), meta: { title: '税务知识', group: '入职与成长', parent: '专业基础知识', icon: 'Tax' }, props: () => ({ category: 'TAX', title: '税务知识' }) },
      { path: 'onboarding/knowledge/invoice', name: 'knowledge-invoice', component: () => import('@/views/onboarding/knowledge/CategoryView.vue'), meta: { title: '发票管理', group: '入职与成长', parent: '专业基础知识', icon: 'Ticket' }, props: () => ({ category: 'INVOICE', title: '发票管理' }) },
      { path: 'onboarding/knowledge/business', name: 'knowledge-business', component: () => import('@/views/onboarding/knowledge/CategoryView.vue'), meta: { title: '工商知识', group: '入职与成长', parent: '专业基础知识', icon: 'Briefcase' }, props: () => ({ category: 'BUSINESS', title: '工商知识' }) },
      { path: 'onboarding/knowledge/social', name: 'knowledge-social', component: () => import('@/views/onboarding/knowledge/CategoryView.vue'), meta: { title: '社保公积金', group: '入职与成长', parent: '专业基础知识', icon: 'Umbrella' }, props: () => ({ category: 'SOCIAL', title: '社保公积金' }) },
      { path: 'onboarding/knowledge/law', name: 'knowledge-law', component: () => import('@/views/onboarding/knowledge/CategoryView.vue'), meta: { title: '财税法规', group: '入职与成长', parent: '专业基础知识', icon: 'Scale' }, props: () => ({ category: 'LAW', title: '财税法规' }) },
      { path: 'onboarding/knowledge/software', name: 'knowledge-software', component: () => import('@/views/onboarding/knowledge/CategoryView.vue'), meta: { title: '软件操作', group: '入职与成长', parent: '专业基础知识', icon: 'Monitor' }, props: () => ({ category: 'SOFTWARE', title: '软件操作' }) },
      { path: 'onboarding/knowledge/sale', name: 'knowledge-sale', component: () => import('@/views/onboarding/knowledge/CategoryView.vue'), meta: { title: '销售话术', group: '入职与成长', parent: '专业基础知识', icon: 'ChatLineSquare' }, props: () => ({ category: 'SALE', title: '销售话术' }) },
      { path: 'training/video', name: 'training-video', component: () => import('@/views/training/VideoView.vue'), meta: { title: '视频学习', group: '入职与成长', parent: '专业基础知识', icon: 'VideoCamera' } },
      { path: 'onboarding/exam', name: 'exam', component: () => import('@/views/onboarding/ExamView.vue'), meta: { title: '在线考试', group: '入职与成长', parent: '专业基础知识', icon: 'EditPen' } },
      // 2026-10-30 Boss 指示：知识库管理从「运营部」分组移入「入职与成长」（紧随专业基础知识之后）
      { path: 'ops/knowledge-manage', name: 'ops-knowledge-manage', component: () => import('@/views/onboarding/knowledge/ManageView.vue'), meta: { title: '知识库管理', group: '入职与成长', icon: 'Setting' } },
      { path: 'onboarding/business', name: 'onboarding-business', component: () => import('@/views/onboarding/BusinessView.vue'), meta: { title: '业务全流程', group: '入职与成长', icon: 'Briefcase' } },

      // ========== 第二梯队：业务部门（增长中台配渠道 → 运营投放 → 电销成交 → 会计交付 → 人事支撑）==========
      { path: 'growth/channels', name: 'growth-channels', component: () => import('@/views/growth/ChannelManageView.vue'), meta: { title: '渠道管理', group: '增长中心', icon: 'SetUp', manager_only: true } },
      { path: 'growth/roles', name: 'growth-roles', component: () => import('@/views/growth/RoleManageView.vue'), meta: { title: '角色分配', group: '增长中心', icon: 'UserFilled', manager_only: true } },
      { path: 'growth/lead-entry', name: 'growth-lead-entry', component: () => import('@/views/growth/LeadEntryView.vue'), meta: { title: '线索转化看板', group: '增长中心', icon: 'Promotion' } },
      { path: 'growth/leads', name: 'growth-leads', component: () => import('@/views/growth/LeadWorkbenchView.vue'), meta: { title: '线索工作台', group: '增长中心', icon: 'Connection' } },
      { path: 'growth/pool', name: 'growth-pool', component: () => import('@/views/growth/PoolView.vue'), meta: { title: '线索公海', group: '增长中心', icon: 'Goblet' } },
      // 2026-10-30 Boss 指示：外勤 / 增值业务 从「增长中心」拆出，独立为一级部门菜单（见下方外勤部 / 增值业务部）
      { path: 'contracts/sales', name: 'contracts-sales', component: () => import('@/views/contracts/ContractsView.vue'), meta: { title: '电销部合同', group: '增长中心', parent: '合同订单名录', icon: 'Document' }, props: () => ({ dept: 'SALES' }) },
      { path: 'contracts/ops', name: 'contracts-ops', component: () => import('@/views/contracts/ContractsView.vue'), meta: { title: '运营部合同', group: '增长中心', parent: '合同订单名录', icon: 'Document' }, props: () => ({ dept: 'OPS' }) },
      { path: 'growth/contracts', name: 'growth-contracts', component: () => import('@/views/sales/ContractView.vue'), meta: { title: '全部合同(管理)', group: '增长中心', parent: '合同订单名录', icon: 'Document', manager_only: true } },
      { path: 'growth/stats', name: 'growth-stats', component: () => import('@/views/growth/StatsPanelView.vue'), meta: { title: '投放统计面板', group: '增长中心', icon: 'DataAnalysis' } },
      { path: 'ops/dashboard', name: 'ops-dashboard', component: () => import('@/views/ops/OpsDashboardView.vue'), meta: { title: '投放总览', group: '运营部', icon: 'DataBoard', dept: 'OPS' } },
      { path: 'ops/budget', name: 'ops-budget', component: () => import('@/views/ops/BudgetView.vue'), meta: { title: '预算管理', group: '运营部', icon: 'Money', dept: 'OPS' } },
      { path: 'ops/input', name: 'ops-input', component: () => import('@/views/ops/DataInputView.vue'), meta: { title: '数据录入', group: '运营部', icon: 'Upload', dept: 'OPS' } },
      // 2026-10-30 Boss 指示：线索池 移到 数据录入 之后
      { path: 'ops/leads', name: 'ops-leads', component: () => import('@/views/growth/LeadWorkbenchView.vue'), meta: { title: '线索池', group: '运营部', icon: 'Connection', dept: 'OPS' } },
      { path: 'ops/compare', name: 'ops-compare', component: () => import('@/views/ops/CompareView.vue'), meta: { title: '平台对比', group: '运营部', icon: 'Histogram', dept: 'OPS' } },
      { path: 'ops/funnel', name: 'ops-funnel', component: () => import('@/views/ops/FunnelView.vue'), meta: { title: '转化漏斗', group: '运营部', icon: 'Filter', dept: 'OPS' } },
      { path: 'ops/content', name: 'ops-content', component: () => import('@/views/ops/ContentView.vue'), meta: { title: '内容运营', group: '运营部', icon: 'Picture', dept: 'OPS' } },
      { path: 'ops/anchors', name: 'ops-anchors', component: () => import('@/views/ops/AnchorView.vue'), meta: { title: '主播管理', group: '运营部', icon: 'Microphone', dept: 'OPS' } },
      { path: 'ops/benchmark', name: 'ops-benchmark', component: () => import('@/views/ops/BenchmarkView.vue'), meta: { title: '对标账号搜索', group: '运营部', icon: 'VideoCamera', dept: 'OPS' } },
      { path: 'ops/contracts', name: 'ops-contracts', component: () => import('@/views/sales/ContractView.vue'), meta: { title: '合同订单', group: '运营部', icon: 'Document', dept: 'OPS' } },
      { path: 'ops/performance', name: 'ops-overview', component: () => import('@/views/DepartmentPerformanceView.vue'), meta: { title: '业绩核算', group: '运营部', icon: 'DataBoard', dept: 'OPS', leader: true }, props: () => ({ code: 'OPS', title: '运营部业绩核算' }) },
      { path: 'ops/target', name: 'ops-target', component: () => import('@/views/EmployeeTargetView.vue'), meta: { title: '员工业绩目标', group: '运营部', icon: 'Aim', dept: 'OPS', hidden: true }, props: () => ({ code: 'OPS', title: '运营部' }) },
      { path: 'sales/tools', name: 'sales-tools', component: () => import('@/views/sales/ToolsView.vue'), meta: { title: '获客工具', group: '电销部', icon: 'Link', dept: 'SALES' } },
      // 2026-10-30 Boss 指示：意向用户池 移到 线索跟进 上方
      { path: 'sales/intention', name: 'intention', component: () => import('@/views/sales/IntentionView.vue'), meta: { title: '意向用户池', group: '电销部', icon: 'Star', dept: 'SALES' } },
      { path: 'sales/followup', name: 'followup', component: () => import('@/views/sales/FollowUpView.vue'), meta: { title: '线索跟进', group: '电销部', icon: 'Connection', dept: 'SALES' } },
      { path: 'sales/enterprise', name: 'enterprise', component: () => import('@/views/sales/EnterpriseView.vue'), meta: { title: '企业查询', group: '电销部', icon: 'Search', dept: 'SALES' } },
      { path: 'sales/contracts', name: 'contracts', component: () => import('@/views/sales/ContractView.vue'), meta: { title: '合同订单', group: '电销部', icon: 'Document', dept: ['SALES', 'OPS'] } },
      { path: 'sales/customers', name: 'customers', component: () => import('@/views/sales/CustomerView.vue'), meta: { title: '客户档案', group: '电销部', icon: 'Avatar', dept: 'SALES' } },
      { path: 'sales/renewal', name: 'renewal', component: () => import('@/views/sales/RenewalView.vue'), meta: { title: '续费预警', group: '电销部', icon: 'AlarmClock', dept: 'SALES' } },
      { path: 'sales/performance', name: 'performance', component: () => import('@/views/sales/PerformanceView.vue'), meta: { title: '业绩排行', group: '电销部', icon: 'TrendCharts', dept: 'SALES', hidden: true } },
      { path: 'sales/overview', name: 'sales-overview', component: () => import('@/views/DepartmentPerformanceView.vue'), meta: { title: '业绩核算', group: '电销部', icon: 'TrendCharts', dept: 'SALES', leader: true }, props: () => ({ code: 'SALES', title: '电销部业绩核算' }) },
      { path: 'sales/target', name: 'sales-target', component: () => import('@/views/EmployeeTargetView.vue'), meta: { title: '员工业绩目标', group: '电销部', icon: 'Aim', dept: 'SALES', hidden: true }, props: () => ({ code: 'SALES', title: '电销部' }) },
      { path: 'accounting/clients', name: 'acc-clients', component: () => import('@/views/accounting/ClientView.vue'), meta: { title: '代账客户', group: '会计部', icon: 'OfficeBuilding', dept: 'ACCOUNT' } },
      // 2026-11-02 上线：服务费收款台账 + 到期提醒中心（2026-10-30 Boss 专项，对标成熟代账系统）
      { path: 'accounting/payments', name: 'acc-payments', component: () => import('@/views/accounting/ClientPaymentView.vue'), meta: { title: '服务费收款', group: '会计部', icon: 'Money', dept: 'ACCOUNT' } },
      { path: 'accounting/reminders', name: 'acc-reminders', component: () => import('@/views/accounting/ReminderCenterView.vue'), meta: { title: '到期提醒中心', group: '会计部', icon: 'AlarmClock', dept: 'ACCOUNT' } },
      { path: 'accounting/yunzhangfang', name: 'yunzhangfang', component: () => import('@/views/accounting/YunzhangfangView.vue'), meta: { title: '云账房', group: '会计部', icon: 'Coin', dept: 'ACCOUNT' } },
      { path: 'accounting/tasks', name: 'acc-tasks', component: () => import('@/views/accounting/TaskView.vue'), meta: { title: '做账任务', group: '会计部', icon: 'Tickets', dept: 'ACCOUNT' } },
      { path: 'accounting/declaration', name: 'acc-declaration', component: () => import('@/views/accounting/DeclarationView.vue'), meta: { title: '纳税申报', group: '会计部', icon: 'Stamp', dept: 'ACCOUNT' } },
      { path: 'accounting/business', name: 'acc-business', component: () => import('@/views/accounting/BusinessView.vue'), meta: { title: '工商事项', group: '会计部', icon: 'Briefcase', dept: 'ACCOUNT' } },
      { path: 'accounting/overview', name: 'acc-overview', component: () => import('@/views/DepartmentPerformanceView.vue'), meta: { title: '业绩核算', group: '会计部', icon: 'OfficeBuilding', dept: 'ACCOUNT', leader: true }, props: () => ({ code: 'ACCOUNT', title: '会计部业绩核算' }) },
      { path: 'accounting/target', name: 'acc-target', component: () => import('@/views/EmployeeTargetView.vue'), meta: { title: '员工业绩目标', group: '会计部', icon: 'Aim', dept: 'ACCOUNT', hidden: true }, props: () => ({ code: 'ACCOUNT', title: '会计部' }) },

      // ========== 独立部门：外勤部（原「增长中心 → 外勤」拆分，2026-10-30 Boss 指示）==========
      { path: 'growth/field-tasks', name: 'growth-field-tasks', component: () => import('@/views/growth/FieldTaskView.vue'), meta: { title: '外勤任务池', group: '外勤部', icon: 'Van' } },

      // ========== 独立部门：增值业务部（原「增长中心 → 增值业务」拆分，2026-10-30 Boss 指示）==========
      { path: 'growth/value-added', name: 'growth-value-added', component: () => import('@/views/growth/ValueAddedView.vue'), meta: { title: '增值业务部', group: '增值业务部', icon: 'Goods' } },

      // 2026-10-30 Boss 指示：员工管理 / 部门与小组 从「系统管理」移入「行政人事部」（分组内一级入口）
      { path: 'system/users', name: 'users', component: () => import('@/views/system/UserView.vue'), meta: { title: '员工管理', group: '行政人事部', icon: 'User', admin: true } },
      { path: 'system/departments', name: 'departments', component: () => import('@/views/system/DepartmentView.vue'), meta: { title: '部门与小组', group: '行政人事部', icon: 'Grid', admin: true } },
      { path: 'hr/org', name: 'hr-org', component: () => import('@/views/hr/OrgTreeView.vue'), meta: { title: '组织架构', group: '行政人事部', parent: '组织与人员', icon: 'Share', admin: true } },
      { path: 'hr/job-levels', name: 'hr-job-levels', component: () => import('@/views/hr/JobLevelView.vue'), meta: { title: '岗位职级库', group: '行政人事部', parent: '组织与人员', icon: 'Medal' } },
      { path: 'hr/archive', name: 'hr-archive', component: () => import('@/views/hr/EmployeeArchiveView.vue'), meta: { title: '员工档案', group: '行政人事部', parent: '组织与人员', icon: 'Postcard' } },
      { path: 'hr/external-contacts', name: 'hr-external-contacts', component: () => import('@/views/hr/ExternalContactView.vue'), meta: { title: '外部联系人', group: '行政人事部', parent: '组织与人员', icon: 'Connection' } },
      { path: 'hr/user-attachments', name: 'hr-user-attachments', component: () => import('@/views/hr/UserAttachmentView.vue'), meta: { title: '员工证件附件', group: '行政人事部', parent: '组织与人员', icon: 'Paperclip' } },
      { path: 'hr/change-logs', name: 'hr-change-logs', component: () => import('@/views/hr/ChangeLogView.vue'), meta: { title: '档案变更日志', group: '行政人事部', parent: '组织与人员', icon: 'Histogram' } },
      { path: 'hr/entry-apply', name: 'hr-entry-apply', component: () => import('@/views/hr/EntryApplyView.vue'), meta: { title: '入职申请', group: '行政人事部', parent: '入转调离', icon: 'Postcard' } },
      { path: 'hr/onboard', name: 'hr-onboard', component: () => import('@/views/hr/OnboardOffboardView.vue'), meta: { title: '入职与离职管理', group: '行政人事部', parent: '入转调离', icon: 'UserFilled', admin: true } },
      { path: 'hr/entry-review', name: 'hr-entry-review', component: () => import('@/views/hr/EntryReviewView.vue'), meta: { title: '入职审核', group: '行政人事部', parent: '入转调离', icon: 'Checked', admin: true } },
      { path: 'hr/lifecycle', name: 'hr-lifecycle', component: () => import('@/views/hr/LifecycleView.vue'), meta: { title: '入转调离管理', group: '行政人事部', parent: '入转调离', icon: 'Switch' } },
      { path: 'hr/labor-contracts', name: 'hr-labor-contracts', component: () => import('@/views/hr/LaborContractView.vue'), meta: { title: '劳动合同台账', group: '行政人事部', parent: '入转调离', icon: 'Document' } },
      { path: 'hr/attendance-extra', name: 'hr-attendance-extra', component: () => import('@/views/hr/AttendanceExtraView.vue'), meta: { title: '考勤组与排班', group: '行政人事部', parent: '考勤与审批', icon: 'AlarmClock' } },
      { path: 'hr/attendance', name: 'attendance', component: () => import('@/views/hr/AttendanceView.vue'), meta: { title: '考勤打卡', group: '行政人事部', parent: '考勤与审批', icon: 'Clock' } },
      { path: 'hr/leave', name: 'leave', component: () => import('@/views/hr/LeaveView.vue'), meta: { title: '请假加班', group: '行政人事部', parent: '考勤与审批', icon: 'Calendar' } },
      { path: 'hr/approval', name: 'approval', component: () => import('@/views/hr/ApprovalView.vue'), meta: { title: '审批中心', group: '行政人事部', parent: '考勤与审批', icon: 'Checked' } },
      { path: 'hr/purchase-seal', name: 'hr-purchase-seal', component: () => import('@/views/hr/PurchaseSealView.vue'), meta: { title: '采购用印审批', group: '行政人事部', parent: '考勤与审批', icon: 'ShoppingCart' } },
      { path: 'hr/stat', name: 'attendance-stat', component: () => import('@/views/hr/AttendanceStatView.vue'), meta: { title: '考勤统计', group: '行政人事部', parent: '考勤与审批', icon: 'DataAnalysis', leader: true } },
      { path: 'hr/salary/rules', name: 'hr-salary-rules', component: () => import('@/views/hr/CommissionRuleView.vue'), meta: { title: '提成规则', group: '行政人事部', parent: '薪酬绩效', icon: 'Coin', leader: true } },
      { path: 'hr/salary', name: 'hr-salary', component: () => import('@/views/hr/SalaryView.vue'), meta: { title: '薪酬核算', group: '行政人事部', parent: '薪酬绩效', icon: 'Money', leader: true } },
      { path: 'hr/performance', name: 'hr-performance', component: () => import('@/views/hr/PerformanceView.vue'), meta: { title: '绩效考核', group: '行政人事部', parent: '薪酬绩效', icon: 'Trophy' } },
      { path: 'hr/dingtalk', name: 'hr-dingtalk', component: () => import('@/views/hr/DingTalkSyncView.vue'), meta: { title: '钉钉同步', group: '行政人事部', icon: 'Link', admin: true } },
      { path: 'hr/permission', name: 'hr-permission', component: () => import('@/views/hr/PermissionView.vue'), meta: { title: '权限管控', group: '行政人事部', icon: 'Lock', admin: true } },
      { path: 'hr/performance-stat', name: 'hr-performance-stat', component: () => import('@/views/hr/PerformanceStatView.vue'), meta: { title: '人事业绩统计', group: '行政人事部', icon: 'TrendCharts', leader: true, hidden: true } },

      // ========== 第三梯队：汇报 → 通知 → 对外产品 → 系统管理 ==========
      { path: 'reports/daily', name: 'daily', component: () => import('@/views/reports/DailyView.vue'), meta: { title: '工作日报', group: '工作汇报', icon: 'Notebook' } },
      { path: 'reports/weekly', name: 'weekly', component: () => import('@/views/reports/WeeklyView.vue'), meta: { title: '工作周报', group: '工作汇报', icon: 'Tickets' } },
      { path: 'reports/monthly', name: 'monthly', component: () => import('@/views/reports/MonthlyView.vue'), meta: { title: '工作月报', group: '工作汇报', icon: 'Files' } },
      { path: 'reports/review', name: 'review', component: () => import('@/views/reports/ReviewView.vue'), meta: { title: '专项复盘', group: '工作汇报', icon: 'RefreshLeft' } },
      { path: 'reports/team', name: 'team-report', component: () => import('@/views/reports/TeamReportView.vue'), meta: { title: '团队汇报', group: '工作汇报', icon: 'UserFilled', leader: true } },
      { path: 'notices', name: 'notices', component: () => import('@/views/notices/AnnouncementView.vue'), meta: { title: '通知公告', group: '公司通知', icon: 'Bell' } },
      { path: 'membership/plans', name: 'membership-plans', component: () => import('@/views/membership/PlansView.vue'), meta: { title: '会员套餐', group: '会员体系', icon: 'Goods' } },
      { path: 'membership/subscribe', name: 'membership-subscribe', component: () => import('@/views/membership/SubscribeView.vue'), meta: { title: '订阅购买', group: '会员体系', icon: 'ShoppingCart' } },
      { path: 'membership/members', name: 'membership-members', component: () => import('@/views/membership/MembersView.vue'), meta: { title: '会员管理', group: '会员体系', icon: 'UserFilled', admin: true } },
      { path: 'investment/policy', name: 'investment-policy', component: () => import('@/views/investment/PolicyView.vue'), meta: { title: '合作政策', group: '招商合作', icon: 'Document' } },
      { path: 'investment/materials', name: 'investment-materials', component: () => import('@/views/investment/MaterialsView.vue'), meta: { title: '招商资料', group: '招商合作', icon: 'Files' } },
      { path: 'investment/inquiry', name: 'investment-inquiry', component: () => import('@/views/investment/InquiryView.vue'), meta: { title: '合作咨询', group: '招商合作', icon: 'ChatDotRound' } },
      // 2026-10-30 Boss 指示：数据权限墙 从电销部移入 系统管理（路径同步调整，旧路径做重定向兼容）
      { path: 'sales/data-wall', redirect: '/system/data-wall' },
      { path: 'system/data-wall', name: 'data-wall', component: () => import('@/views/sales/DataWallView.vue'), meta: { title: '数据权限墙', group: '系统管理', icon: 'Lock', admin: true } },
      { path: 'system/third-party-api', name: 'third-party-api', component: () => import('@/views/system/ThirdPartyApiView.vue'), meta: { title: '第三方API配置', group: '系统管理', icon: 'Key', admin: true } },
      { path: 'system/op-logs', name: 'op-logs', component: () => import('@/views/system/OpLogView.vue'), meta: { title: '操作日志', group: '系统管理', icon: 'Document', admin: true } },
      { path: 'system/storage', name: 'storage', component: () => import('@/views/system/DataStorageView.vue'), meta: { title: '数据储存', group: '系统管理', icon: 'Coin', admin: true } },
      { path: 'system/integration', name: 'system-integration', component: () => import('@/views/integration/SysIntegView.vue'), meta: { title: '云资源对接', group: '系统管理', icon: 'Link', manager_only: true } },
      { path: 'system/profile', name: 'profile', component: () => import('@/views/system/ProfileView.vue'), meta: { title: '个人中心', group: '系统管理', icon: 'Setting' } },
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) {
    next('/login')
    return
  }
  if (to.path === '/login' && token) {
    next('/dashboard')
    return
  }
  // 部门越权拦截（防御纵深，Boss 2026-09-14 安全加固）
  // 带 meta.dept 的页面：非 BOSS/HR 且部门不符则拦回首页，避免手动输入 URL 越权进入
  const dept = to.meta?.dept
  if (dept && token) {
    try {
      const u = JSON.parse(localStorage.getItem('user') || 'null')
      const myDept = u?.department_name || ''
      const map = { SALES: '电销部', ACCOUNT: '会计部', OPS: '运营部' }
      const allowed = (Array.isArray(dept) ? dept : [dept]).map(d => map[d]).filter(Boolean)
      const isBossOrHR = !!(u && (u.role === 'BOSS' || u.role === 'HR' || u.is_superuser))
      if (!isBossOrHR && !allowed.includes(myDept)) {
        next('/dashboard')
        return
      }
    } catch (e) {
      // 解析失败不拦截，交由后端权限兜底
    }
  }
  next()
})

export default router
