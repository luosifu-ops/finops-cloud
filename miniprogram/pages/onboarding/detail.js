const app = getApp()

const MAP = {
  culture: '/onboarding/cultures/',
  regulation: '/onboarding/regulations/',
  knowledge: '/onboarding/articles/'
}

Page({
  data: { type: '', id: '', item: null },

  onLoad(q) {
    this.setData({ type: q.type || '', id: q.id || '' })
    if (q.type === 'profile') wx.setNavigationBarTitle({ title: '入职资料' })
  },

  onShow() { this.load() },

  load() {
    if (this.data.type === 'profile') {
      app.request('/onboarding/profiles/my/')
        .then(d => this.setData({ item: d || null }))
        .catch(() => this.setData({ item: null }))
      return
    }
    const m = MAP[this.data.type]
    if (!m) return
    app.request(m + this.data.id + '/')
      .then(d => this.setData({ item: d || {} }))
      .catch(() => this.setData({ item: {} }))
  },

  ack() {
    app.request(MAP.regulation + this.data.id + '/ack/', 'POST', {})
      .then(() => { wx.showToast({ title: '已确认', icon: 'success' }); this.load() })
      .catch(() => {})
  },

  learn() {
    app.request(MAP.knowledge + this.data.id + '/learn/', 'POST', { finished: true })
      .then(() => { wx.showToast({ title: '已完成', icon: 'success' }); this.load() })
      .catch(() => {})
  },

  submitProfile() {
    wx.showModal({
      title: '提交入职资料', content: '将提交当前账号的入职资料供人事审核',
      confirmColor: '#FF5C8A',
      success: (r) => {
        if (r.confirm) {
          app.request('/onboarding/profiles/submit/', 'POST', {})
            .then(() => { wx.showToast({ title: '已提交', icon: 'success' }); this.load() })
            .catch(() => {})
        }
      }
    })
  }
})
