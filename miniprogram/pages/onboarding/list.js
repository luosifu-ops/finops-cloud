const app = getApp()

const MAP = {
  culture: { endpoint: '/onboarding/cultures/', name: '企业文化' },
  regulation: { endpoint: '/onboarding/regulations/', name: '公司制度' },
  knowledge: { endpoint: '/onboarding/articles/', name: '财税知识' }
}

Page({
  data: { type: 'culture', name: '', list: [], error: '', meta: '' },

  onLoad(q) {
    const type = q.type || 'culture'
    const m = MAP[type] || MAP.culture
    wx.setNavigationBarTitle({ title: m.name })
    this.setData({ type, name: m.name })
  },

  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  load(done) {
    this.setData({ error: '', meta: '请求中…' })
    const m = MAP[this.data.type] || MAP.culture
    const url = m.endpoint + (m.endpoint.indexOf('?') >= 0 ? '&' : '?') + 'page_size=100'
    app.request(url)
      .then(r => {
        const { list } = app.parseList(r)
        const st = (app._diag && app._diag.status) || ''
        this.setData({ list, meta: '✅ 接口 ' + st + ' · 取到 ' + list.length + ' 条' })
      })
      .catch(err => this.setData({ list: [], error: (err && err.message) ? String(err.message) : '加载失败', meta: '❌ 失败' }))
      .then(() => done && done())
  },

  open(e) { wx.navigateTo({ url: `/pages/onboarding/detail?type=${this.data.type}&id=${e.currentTarget.dataset.id}` }) }
})
