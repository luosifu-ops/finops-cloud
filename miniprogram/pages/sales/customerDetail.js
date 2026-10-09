const app = getApp()

// 客户 360° 画像：客户档案 + 合同 + 跟进记录 + 通话记录
// 说明：后端 sales 模块未配置按 customer 过滤（无 filterset_fields），
//      故取全量后在客户端按 customer 过滤，避免依赖未支持的查询参数。
const TYPE = { ENTERPRISE: '企业', INDIVIDUAL: '个体工商户', PERSONAL: '个人' }
const STATUS = { COOPERATING: '合作中', PAUSED: '暂停', CHURNED: '已流失' }
const STATUS_CLS = { COOPERATING: 'tag-green', PAUSED: 'tag-orange', CHURNED: 'tag-gray' }
const WAY = { PHONE: '电话', WECHAT: '微信', VISIT: '上门', MEETING: '会议', OTHER: '其他' }
const RESULT = { CONNECTED: '已接通', NO_ANSWER: '未接', REJECTED: '拒接', SHUTDOWN: '关机/停机', WRONG: '空号/错号' }
const CST = { PENDING: '待付款', PAID: '已付款', EXECUTING: '服务中', FINISHED: '已完成', REFUNDED: '已退款', CANCELED: '已作废' }
const CST_CLS = { PENDING: 'tag-orange', PAID: 'tag-blue', EXECUTING: 'tag-green', FINISHED: 'tag-gray', REFUNDED: 'tag-gray', CANCELED: 'tag-gray' }
const BIZ = { REGISTER: '公司注册', AGENCY: '代理记账', TAX: '税务申报', CHANGE: '工商变更', CANCEL: '公司注销', ADDRESS: '地址挂靠', SOCIAL: '社保代理', AUDIT: '审计验资', OTHER: '其他' }

function pickByCustomer(arr, id) {
  return (arr || []).filter(function (x) {
    const c = x.customer
    const cid = (c && typeof c === 'object') ? c.id : c
    return String(cid) === String(id)
  })
}
function dt(s) { return s ? String(s).slice(0, 16).replace('T', ' ') : '' }
function money(v) { const n = Number(v || 0); return n.toFixed(2) }
function nameOf(u, fallbackKey, obj) {
  if (u && typeof u === 'object') return u.name || u.username || ''
  if (u) return String(u)
  return obj && obj[fallbackKey] ? String(obj[fallbackKey]) : ''
}

Page({
  data: {
    id: '', c: null,
    typeText: '', statusText: '', statusCls: '',
    base: [],
    contracts: [], contractsTotal: '0.00', contractsReceived: '0.00',
    followups: [], calls: [],
    meta: '', error: ''
  },

  onLoad(q) { this.setData({ id: q.id || '' }) },
  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  call() {
    const p = this.data.c && this.data.c.phone
    if (!p) { wx.showToast({ title: '该客户无电话', icon: 'none' }); return }
    wx.makePhoneCall({ phoneNumber: String(p) })
  },
  copyWx() {
    const w = this.data.c && this.data.c.wechat
    if (!w) { wx.showToast({ title: '该客户无微信', icon: 'none' }); return }
    wx.setClipboardData({ data: String(w) })
  },

  load(done) {
    const id = this.data.id
    if (!id) {
      this.setData({ error: '缺少客户 ID，请从客户列表点进去' })
      done && done()
      return
    }
    this.setData({ error: '', meta: '加载中…' })

    const safe = p => app.request(p).catch(() => null)

    Promise.all([
      app.request('/sales/customers/' + id + '/'),
      safe('/sales/contracts/?page_size=100'),
      safe('/sales/followups/?page_size=100'),
      safe('/sales/call-records/?page_size=100')
    ]).then(res => {
      const raw = res[0] || {}
      const c = (raw && raw.data) ? raw.data : raw
      const cons = pickByCustomer(app.parseList(res[1]).list, id)
      const fols = pickByCustomer(app.parseList(res[2]).list, id)
      const cls = pickByCustomer(app.parseList(res[3]).list, id)

      let ta = 0, tr = 0
      const contracts = cons.map(x => {
        ta += Number(x.amount || 0)
        tr += Number(x.received || 0)
        return {
          id: x.id,
          title: x.title || x.contract_no || '合同',
          no: x.contract_no || '',
          biz: BIZ[x.biz_type] || x.biz_type || '',
          amount: money(x.amount),
          received: money(x.received),
          statusText: CST[x.status] || x.status || '',
          statusCls: CST_CLS[x.status] || 'tag-gray',
          period: x.service_period || '',
          signed: x.signed_date || ''
        }
      })

      const followups = fols.map(x => ({
        id: x.id,
        way: WAY[x.way] || x.way || '',
        content: x.content || '',
        user: nameOf(x.user, 'user_name', x),
        at: dt(x.created_at),
        next: x.next_at ? dt(x.next_at) : '',
        nextAction: x.next_action || ''
      }))

      const calls = cls.map(x => ({
        id: x.id,
        result: RESULT[x.result] || x.result || '',
        phone: x.phone || '',
        dur: (x.duration || 0) + '秒',
        wechat: x.has_wechat ? '已加微' : '',
        summary: x.summary || '',
        at: dt(x.created_at)
      }))

      const base = [
        { k: '简称', v: c.short_name },
        { k: '类型', v: TYPE[c.customer_type] || c.customer_type },
        { k: '联系人', v: c.contact },
        { k: '联系电话', v: c.phone },
        { k: '微信', v: c.wechat },
        { k: '统一社会信用代码', v: c.credit_code },
        { k: '所属行业', v: c.industry },
        { k: '所属区域', v: c.region },
        { k: '地址', v: c.address },
        { k: '来源渠道', v: c.source },
        { k: '归属销售', v: nameOf(c.owner, 'owner_name', c) },
        { k: '主办会计', v: nameOf(c.accountant, 'accountant_name', c) },
        { k: '签约日期', v: c.signed_at || '' },
        { k: '服务到期', v: c.expire_at || '' },
        { k: '备注', v: c.remark }
      ].filter(x => x.v)

      this.setData({
        c: c,
        base: base,
        typeText: TYPE[c.customer_type] || '',
        statusText: STATUS[c.status] || c.status || '',
        statusCls: STATUS_CLS[c.status] || 'tag-gray',
        contracts: contracts,
        contractsTotal: money(ta),
        contractsReceived: money(tr),
        followups: followups,
        calls: calls,
        meta: '✅ 已加载 · 合同 ' + contracts.length + ' 条 · 跟进 ' + followups.length + ' 条 · 通话 ' + calls.length + ' 条'
      })
    }).catch(err => {
      this.setData({ error: (err && err.message) ? String(err.message) : '加载失败' })
    }).then(() => done && done())
  }
})
