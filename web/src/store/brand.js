// 品牌（白标）全局状态：启动时从 /api/branding/ 拉取，覆盖默认「财税企管云」。
// 默认值与后端一致，未配置时不影响任何功能；配置后整体换皮，便于私有化交付同行。
import { reactive } from 'vue'
import { brandingApi } from '@/api'

export const brand = reactive({
  name: '财税企管云',
  logoChar: '财',
  subtitle: '代账公司 · 一体化智能管理平台',
  icpBeian: '',
  policeBeian: '',
  loaded: false
})

// 公安联网备案官方要求：备案号需为可点击链接，跳转到公安部查询页（code 取备案号中的数字）
export function policeBeianUrl(no) {
  const m = String(no || '').match(/\d{8,}/)
  return m
    ? `https://beian.mps.gov.cn/#/query/webSearch?code=${m[0]}`
    : 'https://beian.mps.gov.cn/'
}

export async function initBrand() {
  try {
    const data = await brandingApi.get()
    if (data) {
      if (data.name) brand.name = data.name
      if (data.logo_char) brand.logoChar = data.logo_char
      if (data.subtitle) brand.subtitle = data.subtitle
      if (data.icp_beian !== undefined) brand.icpBeian = data.icp_beian || ''
      if (data.police_beian !== undefined) brand.policeBeian = data.police_beian || ''
    }
  } catch (e) {
    // 保持默认，不阻断使用
  } finally {
    brand.loaded = true
    document.title = `${brand.name} · 企业管理平台`
  }
}
