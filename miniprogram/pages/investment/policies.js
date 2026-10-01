const app = getApp()
const ENDPOINT = '/investment/policies/'
const PAGE_SIZE = 100
const ROWS = [{"k":"title","t":"title"},{"k":"content","label":"内容","t":"sub"},{"k":"is_published","label":"已发布","t":"tag"},{"k":"sort_order","label":"排序","t":"sub"}]
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
  data: { tab: '', list: [], tabs: TABS, search: SEARCH, kw: '', emptyText: '暂无政策', error: '', meta: '' },
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
