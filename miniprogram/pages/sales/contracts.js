const app = getApp()
const ENDPOINT = '/sales/contracts/'
const PAGE_SIZE = 100
const ROWS = [{"k":"customer_name","t":"title"},{"k":"title","label":"合同标题","t":"sub"},{"k":"contract_no","label":"合同号","t":"sub"},{"k":"biz_type_name","label":"业务类型","t":"sub"},{"k":"amount","label":"金额","t":"sub","money":true},{"k":"received","label":"已收","t":"sub","money":true},{"k":"receivable","label":"应收","t":"sub","money":true},{"k":"pay_type","label":"回款方式","t":"right"}]
const TAGMAP = {}
const TABS = []
const SEARCH = null

function build(raw) {
  const item = { id: raw.id, title: '', subs: [], tag: '', tagCls: '', right: '' }
  ROWS.forEach(r => {
    const v = fmt(raw[r.k], r)
    if (r.t === 'title') item.title = v
    else if (r.t === 'tag') {
      item.tag = v
      const code = r.codeKey ? String(raw[r.codeKey]) : String(raw[r.k])
      item.tagCls = TAGMAP[code] || TAGMAP[v] || 'tag'
    }
    else if (r.t === 'right') item.right = (r.label ? r.label + '：' : '') + v
    else item.subs.push({ label: r.label || '', value: v })
  })
  return item
}

Page({
  data: { tab: '', list: [], tabs: TABS, search: SEARCH, kw: '', emptyText: '暂无合同', error: '', meta: '' },
  onShow() { this.load() },
  onPullDownRefresh() { this.load(() => wx.stopPullDownRefresh()) },

  filter(e) { this.setData({ tab: e.currentTarget.dataset.v }, () => this.load()) },
  onSearch(e) { this.setData({ kw: e.detail.value }, () => this.load()) },

  load(done) {
    this.setData({ error: '', meta: '请求中…' })
    let url = ENDPOINT + '?page_size=' + PAGE_SIZE
    if (this.data.tab && TABS.length) {
      const t = TABS.find(x => x.value === this.data.tab)
      if (t && t.qs) url += '&' + t.qs
    }
    if (this.data.kw && SEARCH) url += '&' + SEARCH.param + '=' + encodeURIComponent(this.data.kw)
    app.request(url)
      .then(r => {
        const { list } = app.parseList(r)
        const st = (app._diag && app._diag.status) || ''
        const note = (app._diag && app._diag.note) || ''
        this.setData({ list: list.map(build), meta: '✅ 接口 ' + st + ' · 取到 ' + list.length + ' 条' + (note ? ' · ' + note : '') })
      })
      .catch(err => { this.setData({ list: [], error: (err && err.message) ? String(err.message) : '加载失败', meta: '❌ 失败' }) })
      .then(() => done && done())
  }
})
