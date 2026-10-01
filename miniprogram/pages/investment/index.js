const app = getApp()
Page({
  data: {
    cards: [
      { label: '招商政策', desc: '招商扶持政策一览', icon: '📜', color: 'linear-gradient(135deg,#FF6B9D,#FF8FB1)', url: '/pages/investment/policies' },
      { label: '招商素材', desc: '对外宣传物料库', icon: '🎯', color: 'linear-gradient(135deg,#54A0FF,#74B9FF)', url: '/pages/investment/materials' }
    ]
  },
  go(e) { wx.navigateTo({ url: e.currentTarget.dataset.url }) }
})
