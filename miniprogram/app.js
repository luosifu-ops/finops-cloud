// 财税企管云 · 小程序全局逻辑
//
// ⚠️【2026-09-25 修复】公网 WorkBuddy 托管网关对微信小程序 UA(MicroMessenger/MiniProgram) 一律返 403 HTML「请在浏览器中打开」，
//    导致登录与所有数据请求全 403 → 全空白（蓝条实测「接口 403 · 取到 0 条」）。微信 wx.request 的 UA 不可自定义，客户端无解。
//    现联调期改用本机 Django 后端 127.0.0.1:8000 绕过（IDE 模拟器已配 urlCheck:false + touristappid 可直连本机）。
//
// 🔁 切换规则（优先级从高到低）：
//   1) 本地缓存 api_base 优先（在控制台执行 wx.setStorageSync('api_base','https://yuncaishuitong.com/api') 即可切回公网）
//   2) 默认本机 127.0.0.1:8000（联调）
//   3) 生产环境请改成你自己的【已备案 HTTPS 域名】（如 https://yuncaishuitong.com/api），
//      并在「微信公众平台 → 开发管理 → 开发设置 → 服务器域名」把 request 合法域名配成该 HTTPS 域名。
const PROD_BASE_URL = 'https://finops-cloud-94765.app.workbuddy.host/api' // 公网/生产域名（审核发布用）
const LOCAL_BASE_URL = 'http://127.0.0.1:8000/api'                          // 本机 Django（联调绕 403 用）
const BASE_URL = wx.getStorageSync('api_base') || LOCAL_BASE_URL

App({
  globalData: {
    baseUrl: BASE_URL,
    token: '',
    user: null,
    // 2026-10-02 增量：一次性订阅消息模板 ID（mp 后台「订阅消息 → 我的模板」复制）
    // 留空数组 = 不弹授权、不影响任何提交流程；填入后提交时会自动申请授权。
    wxTmplIds: []
  },

  onLaunch() {
    this.globalData.token = wx.getStorageSync('token') || ''
    this.globalData.user = wx.getStorageSync('user') || null
  },

  // 通用请求封装：自动带 token；兼容「信封 {code,data}」与「裸 DRF 分页 {results,count}」
  // ⚠️ 鉴权双发：公网后端（WorkBuddy 托管）网关会剥离 Authorization 头，鉴权回退 Cookie（finops_access），
  //    故同时携带 Bearer 与 Cookie，本地(127.0.0.1)与公网网关两种环境都能通过。
  request(path, method = 'GET', data = {}) {
    return new Promise((resolve, reject) => {
      const header = { 'Content-Type': 'application/json' }
      const token = wx.getStorageSync('token')
      if (token) {
        header['Authorization'] = 'Bearer ' + token
        header['Cookie'] = 'finops_access=' + token
      }
      wx.request({
        url: BASE_URL + path,
        method,
        data,
        header,
        success: (res) => {
          // ⚠️ 关键修复：微信 wx.request 在某些网关/Content-Type 下不会自动 JSON.parse，
          // 会返回字符串。若不解，登录会把 undefined 存成 token、列表页解析出空数组 → 全空白。
          let body = res.data
          if (typeof body === 'string') {
            try { body = JSON.parse(body) } catch (e) { console.error('[request] JSON 解析失败', path, body.slice(0, 120)) }
          }
          this._diag = { path, status: res.statusCode, hasToken: !!token, bodyType: typeof body, rawBody: (typeof res.data === 'string' ? res.data.slice(0, 80) : '') }
          if (res.statusCode === 401) {
            this._diag.note = '401 未鉴权（token 可能为空/未发出）'
            wx.removeStorageSync('token')
            wx.removeStorageSync('user')
            this.globalData.token = ''
            this.globalData.user = null
            reject(new Error('登录已过期（接口 401，请重新登录）'))
            return
          }
          if (body && typeof body === 'object' && 'code' in body) {
            if (body.code === 0) resolve(body.data)
            else {
              wx.showToast({ title: body.msg || '请求失败', icon: 'none' })
              reject(new Error(body.msg || 'fail'))
            }
          } else {
            // 裸 DRF 分页 / 裸数组 / 裸对象
            resolve(body)
          }
        },
        fail: (err) => {
          this._diag = { path, status: 0, fail: true, err: (err && err.errMsg) || err }
          console.error('[request fail]', path, err)
          wx.showToast({ title: '网络异常', icon: 'none' })
          reject(new Error('network'))
        }
      })
    })
  },

  // 把列表结果统一成 { list, total }，兼容信封+DRF分页 / 裸数组
  parseList(r) {
    if (!r) return { list: [], total: 0 }
    if (r.results) return { list: r.results, total: r.count || r.results.length }
    if (Array.isArray(r)) return { list: r, total: r.length }
    return { list: [], total: 0, item: r }
  },

  // 2026-10-02 增量：申请一次性订阅消息授权。
  // 未配置模板 ID 或真机不支持时静默跳过，直接回调，不阻断提交。
  askSubscribe(done) {
    const ids = (this.globalData.wxTmplIds || []).filter(Boolean)
    if (!ids.length || typeof wx.requestSubscribeMessage !== 'function') {
      done && done()
      return
    }
    wx.requestSubscribeMessage({
      tmplIds: ids,
      complete: () => { done && done() }
    })
  },

  setAuth(token, user) {
    wx.setStorageSync('token', token)
    wx.setStorageSync('user', user)
    this.globalData.token = token
    this.globalData.user = user
  },

  logout() {
    wx.removeStorageSync('token')
    wx.removeStorageSync('user')
    this.globalData.token = ''
    this.globalData.user = null
  }
})
