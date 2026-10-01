const app = getApp()

// 企业查询（对标企查查/天眼查）：对接企业工商信息查询接口
// 列表：GET /integrations/enterprise/search/?keyword=关键词  -> data:[{name,credit_code,legal,phone,capital,established,status,address,scope}]
// 详情：GET /integrations/enterprise/{credit_code}/          -> data.base_info:{...}
Page({
  data: {
    keyword: '',
    list: [],
    detail: null, // base_info
    loading: false
  },

  onKeyword(e) { this.setData({ keyword: e.detail.value }) },

  search() {
    const kw = (this.data.keyword || '').trim()
    if (!kw) { wx.showToast({ title: '请输入企业名称或关键词', icon: 'none' }); return }
    this.setData({ loading: true })
    app.request('/integrations/enterprise/search/?keyword=' + encodeURIComponent(kw))
      .then(r => {
        const d = (r && r.data) ? r.data : r
        this.setData({ list: Array.isArray(d) ? d : [], loading: false })
      })
      .catch(() => this.setData({ list: [], loading: false }))
  },

  open(e) {
    const code = e.currentTarget.dataset.code
    if (!code) return
    app.request('/integrations/enterprise/' + code + '/')
      .then(r => { const d = (r && r.data) ? r.data : r; this.setData({ detail: d.base_info || d }) })
      .catch(() => {})
  },

  closeDetail() { this.setData({ detail: null }) }
})
