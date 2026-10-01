const app = getApp()

// 兼容 options 为数组/对象，统一成 [{key,text}]
function normalizeOptions(opts) {
  if (!opts) return []
  if (Array.isArray(opts)) {
    return opts.map((it, i) => {
      if (typeof it === 'string') {
        const m = it.match(/^\s*([A-Za-z])[\.、)、]\s*(.*)$/)
        if (m) return { key: m[1].toUpperCase(), text: m[2] }
        return { key: String.fromCharCode(65 + i), text: it }
      }
      return { key: String.fromCharCode(65 + i), text: JSON.stringify(it) }
    })
  }
  if (typeof opts === 'object') {
    return Object.keys(opts).map(k => ({ key: k.toUpperCase(), text: opts[k] }))
  }
  return []
}

Page({
  data: {
    id: '', exam: {}, phase: 'info',
    questions: [], answers: {}, record_id: '', result: { score: 0, passed: false }
  },

  onLoad(q) {
    this.setData({ id: q.id || '' })
    app.request('/onboarding/exams/' + this.data.id + '/')
      .then(d => this.setData({ exam: d || {} }))
      .catch(() => {})
  },

  start() {
    app.request('/onboarding/exams/' + this.data.id + '/start/', 'POST', {})
      .then(d => {
        const data = d && d.data ? d.data : {}
        const qs = (data.questions || []).map(q => ({ id: q.id, stem: q.stem, options: normalizeOptions(q.options) }))
        this.setData({ phase: 'doing', record_id: data.record_id, questions: qs, answers: {} })
      })
      .catch(() => {})
  },

  answer(e) {
    const q = e.currentTarget.dataset.q
    const k = e.currentTarget.dataset.k
    this.setData({ ['answers.' + q]: k })
  },

  submit() {
    const answers = {}
    Object.keys(this.data.answers).forEach(qid => {
      if (this.data.answers[qid]) answers[qid] = this.data.answers[qid]
    })
    app.request('/onboarding/exams/' + this.data.id + '/submit/', 'POST', { record_id: this.data.record_id, answers })
      .then(d => {
        const data = d && d.data ? d.data : {}
        this.setData({ phase: 'result', result: { score: data.score || 0, passed: !!data.passed } })
      })
      .catch(() => {})
  },

  back() { wx.navigateBack() }
})
