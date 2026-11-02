import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000
})

http.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = 'Bearer ' + token
  return config
})

// 常见字段中文名：后端只返回英文字段名，直接弹给用户看不懂
const FIELD_LABELS = {
  name: '名称', code: '编码', username: '登录账号', password: '密码', phone: '手机号',
  email: '邮箱', title: '标题', content: '内容', amount: '金额', total_amount: '合同金额',
  customer: '客户', contract: '合同', department: '部门', team: '团队', position: '岗位',
  leader: '负责人', owner: '负责人', date: '日期', start_date: '开始日期', end_date: '结束日期',
  status: '状态', remark: '备注', description: '描述', order: '排序', parent: '上级',
  credit_code: '统一社会信用代码', contact: '联系人', wechat: '微信号', address: '地址',
  industry: '行业', region: '地区', source: '来源', level: '等级', id_card: '身份证号',
  entry_date: '入职日期', leave_date: '离职日期', salary: '薪资', base_salary: '底薪',
  non_field_errors: '提交内容', detail: '详情'
}

// 把后端各种错误结构（业务 msg / DRF detail / 字段级数组）统一翻成人话
function extractErrorMessage(err) {
  const res = err.response
  if (!res) {
    if (err.code === 'ECONNABORTED') return '请求超时，请检查网络后重试'
    return '网络连接失败，请检查网络或稍后再试'
  }
  const data = res.data
  if (data == null || data === '') return `请求失败（${res.status}）`
  if (typeof data === 'string') {
    return res.status >= 500 ? `服务器异常（${res.status}），请截图联系管理员` : data.slice(0, 120)
  }
  if (data.msg) return data.msg
  if (data.message) return data.message
  if (typeof data.detail === 'string') return data.detail
  // DRF 字段级校验：{ phone: ['该字段是必填项。'], name: ['...'] }
  const parts = []
  for (const [key, val] of Object.entries(data)) {
    const label = FIELD_LABELS[key] || key
    if (Array.isArray(val)) parts.push(`${label}：${val.join('；')}`)
    else if (typeof val === 'string') parts.push(`${label}：${val}`)
    else if (val && typeof val === 'object') parts.push(`${label}：${JSON.stringify(val).slice(0, 80)}`)
  }
  if (parts.length) return parts.slice(0, 3).join(' | ')
  return `请求失败（${res.status}）`
}

http.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else {
      // 调用方可设 config.silentError = true 自行处理错误，避免重复弹窗
      if (!err.config?.silentError) {
        ElMessage({ type: 'error', message: extractErrorMessage(err), duration: 5000, showClose: true })
      }
    }
    return Promise.reject(err)
  }
)

// ---------- 认证 ----------
export const authApi = {
  login: (data) => http.post('/accounts/auth/login/', data),
  me: () => http.get('/accounts/auth/me/'),
  updateMe: (data) => http.patch('/accounts/auth/me/', data, {
    headers: { 'Content-Type': 'multipart/form-data' }, timeout: 60000
  }),
  changePassword: (data) => http.post('/accounts/auth/change-password/', data),
  // 手机号验证码登录
  sendSmsCode: (data) => http.post('/accounts/auth/sms/send/', data),
  smsLogin: (data) => http.post('/accounts/auth/sms/login/', data),
  // 微信扫码登录（网站应用）
  wxScanUrl: () => http.get('/accounts/auth/wx-scan/url/'),
  wxScanStatus: (params) => http.get('/accounts/auth/wx-scan/status/', { params }),
  wxScanMock: (data) => http.post('/accounts/auth/wx-scan/mock/', data || {}),
  wxBind: (data) => http.post('/accounts/auth/wx-bind/', data)
}

// ---------- 组织 ----------
export const orgApi = {
  departments: (params) => http.get('/accounts/departments/', { params }),
  createDepartment: (data) => http.post('/accounts/departments/', data),
  updateDepartment: (id, data) => http.patch(`/accounts/departments/${id}/`, data),
  deleteDepartment: (id) => http.delete(`/accounts/departments/${id}/`),
  teams: (params) => http.get('/accounts/teams/', { params }),
  createTeam: (data) => http.post('/accounts/teams/', data),
  updateTeam: (id, data) => http.patch(`/accounts/teams/${id}/`, data),
  deleteTeam: (id) => http.delete(`/accounts/teams/${id}/`),
  positions: (params) => http.get('/accounts/positions/', { params }),
  createPosition: (data) => http.post('/accounts/positions/', data),
  updatePosition: (id, data) => http.patch(`/accounts/positions/${id}/`, data),
  deletePosition: (id) => http.delete(`/accounts/positions/${id}/`),
  users: (params) => http.get('/accounts/users/', { params }),
  user: (id) => http.get(`/accounts/users/${id}/`),
  createUser: (data) => http.post('/accounts/users/', data),
  updateUser: (id, data) => http.patch(`/accounts/users/${id}/`, data),
  teammates: () => http.get('/accounts/users/teammates/'),
  // 部门 / 岗位独立制度（考勤 / 考核）
  deptRules: (params) => http.get('/accounts/dept-rules/', { params }),
  createDeptRule: (data) => http.post('/accounts/dept-rules/', data),
  updateDeptRule: (id, data) => http.patch(`/accounts/dept-rules/${id}/`, data),
  deleteDeptRule: (id) => http.delete(`/accounts/dept-rules/${id}/`),
  // 入职申请
  entries: (params) => http.get('/accounts/entries/', { params }),
  createEntry: (data) => http.post('/accounts/entries/', data),
  updateEntry: (id, data) => http.patch(`/accounts/entries/${id}/`, data),
  deleteEntry: (id) => http.delete(`/accounts/entries/${id}/`),
  approveEntry: (id, data) => http.post(`/accounts/entries/${id}/approve/`, data || {}),
  rejectEntry: (id, data) => http.post(`/accounts/entries/${id}/reject/`, data || {})
}

// ---------- 入职培训 ----------
export const onboardingApi = {
  cultures: (params) => http.get('/onboarding/cultures/', { params }),
  regulations: (params) => http.get('/onboarding/regulations/', { params }),
  ack: (id) => http.post(`/onboarding/regulations/${id}/ack/`),
  myAcks: () => http.get('/onboarding/regulations/my-acks/'),
  articles: (params) => http.get('/onboarding/articles/', { params }),
  learn: (id, data) => http.post(`/onboarding/articles/${id}/learn/`, data),
  progress: () => http.get('/onboarding/articles/my-progress/'),
  // 题库
  questionBanks: (params) => http.get('/onboarding/question-banks/', { params }),
  createBank: (data) => http.post('/onboarding/question-banks/', data),
  updateBank: (id, data) => http.patch(`/onboarding/question-banks/${id}/`, data),
  deleteBank: (id) => http.delete(`/onboarding/question-banks/${id}/`),
  questions: (params) => http.get('/onboarding/questions/', { params }),
  createQuestion: (data) => http.post('/onboarding/questions/', data),
  updateQuestion: (id, data) => http.patch(`/onboarding/questions/${id}/`, data),
  deleteQuestion: (id) => http.delete(`/onboarding/questions/${id}/`),
  // 考试
  exams: (params) => http.get('/onboarding/exams/', { params }),
  createExam: (data) => http.post('/onboarding/exams/', data),
  updateExam: (id, data) => http.patch(`/onboarding/exams/${id}/`, data),
  deleteExam: (id) => http.delete(`/onboarding/exams/${id}/`),
  startExam: (id) => http.post(`/onboarding/exams/${id}/start/`),
  submitExam: (id, data) => http.post(`/onboarding/exams/${id}/submit/`, data),
  myExamRecords: (params) => http.get('/onboarding/exams/my-records/', { params }),
  examRank: (id) => http.get(`/onboarding/exams/${id}/rank/`),
  // 答卷详情 / 错题本
  examRecordDetail: (recordId) => http.get(`/onboarding/exams/records/${recordId}/`),
  myWrongBook: (params) => http.get('/onboarding/exams/my-wrong-book/', { params }),
  examWrongQuestions: (id) => http.get(`/onboarding/exams/${id}/wrong-questions/`),
  // 入职资料
  profiles: (params) => http.get('/onboarding/profiles/', { params }),
  myProfile: () => http.get('/onboarding/profiles/my/'),
  submitProfile: (data) => http.post('/onboarding/profiles/submit/', data),
  reviewProfile: (id, data) => http.post(`/onboarding/profiles/${id}/review/`, data),
  // 入职任务
  myTasks: () => http.get('/onboarding/tasks/my-tasks/'),
  completeTask: (id) => http.post(`/onboarding/tasks/${id}/complete/`),
  taskStat: (params) => http.get('/onboarding/tasks/stat/', { params })
}

// ---------- 人事 ----------
export const hrApi = {
  rules: (params) => http.get('/hr/rules/', { params }),
  attendances: (params) => http.get('/hr/attendances/', { params }),
  checkIn: (data) => http.post('/hr/attendances/check-in/', data),
  checkOut: (data) => http.post('/hr/attendances/check-out/', data),
  todayStatus: () => http.get('/hr/attendances/today-status/'),
  myAttendance: (params) => http.get('/hr/attendances/my/', { params }),
  teamStat: (params) => http.get('/hr/attendances/team-stat/', { params }),
  leaveTypes: () => [],
  leaves: (params) => http.get('/hr/leaves/', { params }),
  createLeave: (data) => http.post('/hr/leaves/', data),
  approveLeave: (id, data) => http.post(`/hr/leaves/${id}/approve/`, data),
  myLeaves: () => http.get('/hr/leaves/my/'),
  pendingLeaves: () => http.get('/hr/leaves/pending/'),
  overtimes: (params) => http.get('/hr/overtimes/', { params }),
  approveOvertime: (id, data) => http.post(`/hr/overtimes/${id}/approve/`, data),
  travels: (params) => http.get('/hr/travels/', { params }),
  expenses: (params) => http.get('/hr/expenses/', { params }),
  approveExpense: (id, data) => http.post(`/hr/expenses/${id}/approve/`, data),
  approvals: (params) => http.get('/hr/approvals/', { params }),
  createApproval: (data) => http.post('/hr/approvals/', data),
  handleApproval: (id, data) => http.post(`/hr/approvals/${id}/handle/`, data),
  todoApprovals: () => http.get('/hr/approvals/todo/'),
  myApprovals: () => http.get('/hr/approvals/my/'),
  doneApprovals: () => http.get('/hr/approvals/done/'),
  // 薪酬绩效（全公司全员核算）
  salaries: (params) => http.get('/hr/salaries/', { params }),
  salaryCalc: (data) => http.post('/hr/salaries/calc/', data),
  salaryBatchCalc: (data) => http.post('/hr/salaries/batch-calc/', data),
  salarySave: (data) => http.post('/hr/salaries/', data),
  salaryUpdate: (id, data) => http.patch(`/hr/salaries/${id}/`, data),
  salaryDelete: (id) => http.delete(`/hr/salaries/${id}/`),
  salarySummary: (params) => http.get('/hr/salaries/summary/', { params }),
  mySalary: (params) => http.get('/hr/salaries/my/', { params }),
  // 人事业绩统计
  performanceStat: (params) => http.get('/hr/performance/stat/', { params })
}

// ---------- 汇报 ----------
export const reportApi = {
  templates: (params) => http.get('/reports/report-templates/', { params }),
  dailies: (params) => http.get('/reports/daily-reports/', { params }),
  saveDaily: (data) => http.post('/reports/daily-reports/save-or-update/', data),
  myDailies: (params) => http.get('/reports/daily-reports/my/', { params }),
  teamDailies: (params) => http.get('/reports/daily-reports/team/', { params }),
  scoreDaily: (id, data) => http.post(`/reports/daily-reports/${id}/score/`, data),
  weeklies: (params) => http.get('/reports/weekly-reports/', { params }),
  saveWeekly: (data) => http.post('/reports/weekly-reports/save-or-update/', data),
  myWeeklies: () => http.get('/reports/weekly-reports/my/'),
  monthlies: (params) => http.get('/reports/monthly-reports/', { params }),
  saveMonthly: (data) => http.post('/reports/monthly-reports/save-or-update/', data),
  myMonthlies: () => http.get('/reports/monthly-reports/my/'),
  reviews: (params) => http.get('/reports/review-reports/', { params }),
  createReview: (data) => http.post('/reports/review-reports/', data),
  myReviews: () => http.get('/reports/review-reports/my/'),
  comments: (params) => http.get('/reports/report-comments/', { params }),
  commentList: (params) => http.get('/reports/report-comments/list-by/', { params }),
  addComment: (data) => http.post('/reports/report-comments/', data)
}

// ---------- 电销 ----------
export const salesApi = {
  leads: (params) => http.get('/sales/leads/', { params }),
  createLead: (data) => http.post('/sales/leads/', data),
  updateLead: (id, data) => http.patch(`/sales/leads/${id}/`, data),
  assignLeads: (data) => http.post('/sales/leads/assign/', data),
  takeLead: (id) => http.post(`/sales/leads/${id}/take/`),
  dealLead: (id, data) => http.post(`/sales/leads/${id}/deal/`, data),
  lostLead: (id, data) => http.post(`/sales/leads/${id}/lost/`, data),
  myLeads: (params) => http.get('/sales/leads/my/', { params }),
  leadFunnel: () => http.get('/sales/leads/funnel/'),
  leadSourceStat: (params) => http.get('/sales/leads/source-stat/', { params }),
  customers: (params) => http.get('/sales/customers/', { params }),
  createCustomer: (data) => http.post('/sales/customers/', data),
  updateCustomer: (id, data) => http.patch(`/sales/customers/${id}/`, data),
  myCustomers: () => http.get('/sales/customers/my/'),
  expiringCustomers: (params) => http.get('/sales/customers/expiring/', { params }),
  contracts: (params) => http.get('/sales/contracts/', { params }),
  createContract: (data) => http.post('/sales/contracts/', data),
  payment: (id, data) => http.post(`/sales/contracts/${id}/payment/`, data),
  // 合同扫描件上传（multipart/form-data，单文件 ≤ 20MB）
  uploadContractAttachment: (id, file) => {
    const fd = new FormData()
    fd.append('attachment', file)
    return http.post(`/sales/contracts/${id}/upload_attachment/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  // 客户付款截图上传（增量功能，multipart/form-data，单文件 ≤ 20MB）
  uploadContractPaymentScreenshot: (id, file) => {
    const fd = new FormData()
    fd.append('payment_screenshot', file)
    return http.post(`/sales/contracts/${id}/upload_payment_screenshot/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  myContracts: (params) => http.get('/sales/contracts/my/', { params }),
  performance: (params) => http.get('/sales/contracts/performance/', { params }),
  rank: (params) => http.get('/sales/contracts/rank/', { params }),
  callRecords: (params) => http.get('/sales/call-records/', { params }),
  createCall: (data) => http.post('/sales/call-records/', data),
  myCallStat: (params) => http.get('/sales/call-records/my-stat/', { params }),
  followups: (params) => http.get('/sales/followups/', { params }),
  leadTimeline: (id) => http.get(`/sales/leads/${id}/timeline/`),
  createFollowup: (data) => http.post('/sales/followups/', data),
  updateFollowup: (id, data) => http.patch(`/sales/followups/${id}/`, data),
  deleteFollowup: (id) => http.delete(`/sales/followups/${id}/`),
  upcoming: () => http.get('/sales/followups/upcoming/'),
  targets: (params) => http.get('/sales/targets/', { params }),
  batchSetTarget: (data) => http.post('/sales/targets/batch-set/', data),
  commissionRules: (params) => http.get('/sales/commission-rules/', { params }),
  salaryCalc: (data) => http.post('/sales/salary/calc/', data),
  salaryList: (params) => http.get('/sales/salary/', { params }),
  salarySave: (data) => http.post('/sales/salary/', data),
  streamers: (params) => http.get('/sales/streamers/', { params }),
  createStreamer: (data) => http.post('/sales/streamers/', data),
  updateStreamer: (id, data) => http.patch(`/sales/streamers/${id}/`, data),
  deleteStreamer: (id) => http.delete(`/sales/streamers/${id}/`)
}

// ---------- 会计 ----------
export const accApi = {
  taxTypes: (params) => http.get('/accounting/tax-types/', { params }),
  bookSets: (params) => http.get('/accounting/book-sets/', { params }),
  createBookSet: (data) => http.post('/accounting/book-sets/', data),
  updateBookSet: (id, data) => http.patch(`/accounting/book-sets/${id}/`, data),
  deleteBookSet: (id) => http.delete(`/accounting/book-sets/${id}/`),
  bookSetSummary: () => http.get('/accounting/book-sets/summary/'),
  clients: (params) => http.get('/accounting/clients/', { params }),
  createClient: (data) => http.post('/accounting/clients/', data),
  updateClient: (id, data) => http.patch(`/accounting/clients/${id}/`, data),
  myClients: () => http.get('/accounting/clients/my/'),
  expiringClients: (params) => http.get('/accounting/clients/expiring/', { params }),
  accOverview: () => http.get('/accounting/clients/overview/'),
  tasks: (params) => http.get('/accounting/monthly-tasks/', { params }),
  batchCreateTasks: (data) => http.post('/accounting/monthly-tasks/batch-create/', data, { params: data }),
  advanceTask: (id, data) => http.post(`/accounting/monthly-tasks/${id}/advance/`, data),
  taskBoard: (params) => http.get('/accounting/monthly-tasks/board/', { params }),
  myTasks: (params) => http.get('/accounting/monthly-tasks/my-tasks/', { params }),
  taskProgress: (params) => http.get('/accounting/monthly-tasks/progress/', { params }),
  steps: (params) => http.get('/accounting/task-steps/', { params }),
  vouchers: (params) => http.get('/accounting/vouchers/', { params }),
  batchCreateVouchers: (data) => http.post('/accounting/vouchers/batch-create/', data),
  invoices: (params) => http.get('/accounting/invoices/', { params }),
  batchImportInvoices: (data) => http.post('/accounting/invoices/batch-import/', data),
  bankStatements: (params) => http.get('/accounting/bank-statements/', { params }),
  declarations: (params) => http.get('/accounting/tax-declarations/', { params }),
  declare: (id) => http.post(`/accounting/tax-declarations/${id}/declare/`),
  deadline: (params) => http.get('/accounting/tax-declarations/deadline/', { params }),
  socials: (params) => http.get('/accounting/social-insurances/', { params }),
  annualReports: (params) => http.get('/accounting/annual-reports/', { params }),
  businessItems: (params) => http.get('/accounting/business-items/', { params }),
  createBusinessItem: (data) => http.post('/accounting/business-items/', data),
  finishBusinessItem: (id) => http.post(`/accounting/business-items/${id}/finish/`),
  myBusinessItems: () => http.get('/accounting/business-items/my/'),
  documents: (params) => http.get('/accounting/client-documents/', { params }),
  handovers: (params) => http.get('/accounting/handovers/', { params })
}

// ---------- 运营 ----------
export const opsApi = {
  platforms: (params) => http.get('/ops/platforms/', { params }),
  createPlatform: (data) => http.post('/ops/platforms/', data),
  accounts: (params) => http.get('/ops/accounts/', { params }),
  campaigns: (params) => http.get('/ops/campaigns/', { params }),
  dailyStats: (params) => http.get('/ops/daily-stats/', { params }),
  batchInput: (data) => http.post('/ops/daily-stats/batch-input/', data),
  summary: (params) => http.get('/ops/daily-stats/summary/', { params }),
  platformCompare: (params) => http.get('/ops/daily-stats/platform-compare/', { params }),
  trend: (params) => http.get('/ops/daily-stats/trend/', { params }),
  funnel: (params) => http.get('/ops/daily-stats/funnel/', { params }),
  budgetVsActual: (params) => http.get('/ops/daily-stats/budget-vs-actual/', { params }),
  creatives: (params) => http.get('/ops/creatives/', { params }),
  posts: (params) => http.get('/ops/posts/', { params }),
  createPost: (data) => http.post('/ops/posts/', data),
  myPosts: () => http.get('/ops/posts/my/'),
  postStatSummary: (params) => http.get('/ops/posts/stat-summary/', { params }),
  contentStats: (params) => http.get('/ops/content-stats/', { params }),
  budgets: (params) => http.get('/ops/budgets/', { params }),
  batchSetBudget: (data) => http.post('/ops/budgets/batch-set/', data),
  dailyReports: (params) => http.get('/ops/daily-reports/', { params }),
  saveDailyReport: (data) => http.post('/ops/daily-reports/save-or-update/', data)
}

// ---------- 看板 ----------
export const dashApi = {
  overview: (params) => http.get('/dashboard/overview/', { params }),
  rank: (params) => http.get('/dashboard/rank/', { params }),
  trend: (params) => http.get('/dashboard/trend/', { params }),
  todo: () => http.get('/dashboard/todo/'),
  department: (code, params) => http.get(`/dashboard/department/${code}/`, { params }),
  departmentMembers: (code, params) => http.get(`/dashboard/department/${code}/members/`, { params }),
  dataWall: (params) => http.get('/dashboard/data-wall/', { params }),
  companyPerformance: (params) => http.get('/dashboard/company-performance/', { params })
}

// ---------- AI 经营助手 ----------
export const aiApi = {
  chat: (data) => http.post('/dashboard/ai/chat/', data)
}

// ---------- 外部能力集成（企业查询/电子营业执照/电子税务局/抖音对标/云账房/视频学习）----------
export const integrationApi = {
  // 企业工商查询（企查查/天眼查类）
  enterpriseSearch: (params) => http.get('/integrations/enterprise/search/', { params }),
  enterpriseDetail: (code) => http.get(`/integrations/enterprise/${code}/`),
  // 抖音对标账号
  douyinAccount: (params) => http.get('/integrations/douyin/account/', { params }),
  // 云账房
  yunzhangfang: (params) => http.get('/integrations/yunzhangfang/overview/', { params }),
  // 视频学习库
  trainingVideos: (params) => http.get('/integrations/training/videos/', { params }),
  createTrainingVideo: (data) => http.post('/integrations/training/videos/', data),
  updateTrainingVideo: (id, data) => http.patch(`/integrations/training/videos/${id}/`, data),
  deleteTrainingVideo: (id) => http.delete(`/integrations/training/videos/${id}/`),
  // 对标账号搜索（多平台：抖音/快手/小红书/视频号）
  benchmarkPlatforms: () => http.get('/integrations/benchmark/platforms/'),
  benchmarkSearch: (params) => http.get('/integrations/benchmark/search/', { params }),
  // 对标账号库（2026-11-02：全员可录入，库内优先检索）
  benchmarkAccounts: (params) => http.get('/integrations/benchmark-accounts/', { params }),
  createBenchmarkAccount: (data) => http.post('/integrations/benchmark-accounts/', data),
  updateBenchmarkAccount: (id, data) => http.patch(`/integrations/benchmark-accounts/${id}/`, data),
  deleteBenchmarkAccount: (id) => http.delete(`/integrations/benchmark-accounts/${id}/`),
  // 钉钉通讯录同步（仅老板/人事）
  dingtalkStatus: () => http.get('/integrations/dingtalk/status/'),
  dingtalkSync: (data) => http.post('/integrations/dingtalk/sync/', data || {})
}

// ---------- 公司介绍 ----------
export const companyApi = {
  get: () => http.get('/accounts/company/'),
  save: (data) => http.post('/accounts/company/', data)
}

// ---------- 会员体系（付费订阅）----------
export const membershipApi = {
  plans: (params) => http.get('/membership/plans/', { params }),
  createPlan: (data) => http.post('/membership/plans/', data),
  updatePlan: (id, data) => http.patch(`/membership/plans/${id}/`, data),
  deletePlan: (id) => http.delete(`/membership/plans/${id}/`),
  subscriptions: (params) => http.get('/membership/subscriptions/', { params }),
  subscribe: (data) => http.post('/membership/subscriptions/', data),
  updateSubscription: (id, data) => http.patch(`/membership/subscriptions/${id}/`, data),
  pay: (data) => http.post('/membership/pay/', data),
  mySubscription: () => http.get('/membership/subscriptions/my/'),
  setStatus: (id, data) => http.post(`/membership/subscriptions/${id}/status/`, data),
  permissions: () => http.get('/membership/permissions/')
}

// ---------- 招商板块 ----------
export const investmentApi = {
  policies: (params) => http.get('/investment/policies/', { params }),
  createPolicy: (data) => http.post('/investment/policies/', data),
  materials: (params) => http.get('/investment/materials/', { params }),
  createMaterial: (data) => http.post('/investment/materials/', data),
  inquiries: (params) => http.get('/investment/inquiries/', { params }),
  submitInquiry: (data) => http.post('/investment/inquiries/', data),
  handleInquiry: (id, data) => http.post(`/investment/inquiries/${id}/handle/`, data)
}

// ---------- 公司通知公告 ----------
export const noticeApi = {
  list: (params) => http.get('/notices/', { params }),
  create: (data) => http.post('/notices/', data),
  update: (id, data) => http.patch(`/notices/${id}/`, data),
  destroy: (id) => http.delete(`/notices/${id}/`),
  uploadFile: (id, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post(`/notices/${id}/upload_file/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  markRead: (id) => http.post(`/notices/${id}/mark_read/`),
  unreadCount: () => http.get('/notices/unread_count/')
}

// ---------- 品牌（白标，无需登录）----------
export const brandingApi = {
  get: () => http.get('/branding/')
}

export default http

// ---------- 全局基础能力（2026-10-29）：操作日志 / 站内消息 / 系统配置 ----------
export const commonApi = {
  opLogs: (params) => http.get('/common/op-logs/', { params }),
  inbox: (params) => http.get('/common/inbox/', { params }),
  inboxUnread: () => http.get('/common/inbox/unread-count/'),
  inboxMarkRead: (id) => http.post(`/common/inbox/${id}/mark-read/`),
  inboxMarkAll: () => http.post('/common/inbox/mark-all-read/'),
  sysConfig: () => http.get('/common/sys-config/'),
  saveSysConfig: (data) => http.put('/common/sys-config/', data),
}
