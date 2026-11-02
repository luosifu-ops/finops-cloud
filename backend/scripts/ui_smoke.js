/** 生产环境 UI 冒烟：新功能页面 + 全站路由遍历（0 JS 报错 / 0 5xx） */
const { chromium } = require('playwright')

const fs = require('fs')
const BASE = 'https://yuncaishuitong.com'

const EXEC = '/Users/luosifu/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell'

async function getToken() {
  // token 由 curl 预取（直连 IP 会被 Caddy 的 SNI 校验拒绝）
  const access = fs.readFileSync('/tmp/tok2.txt', 'utf8').trim()
  const user = JSON.parse(fs.readFileSync('/tmp/user2.json', 'utf8'))
  return { access, user }
}

;(async () => {
  const data = await getToken()
  if (!data) { console.log('登录失败'); process.exit(1) }
  const browser = await chromium.launch({ executablePath: EXEC })
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 }, ignoreHTTPSErrors: true })
  await ctx.addInitScript(([t, u]) => {
    localStorage.setItem('token', t)
    localStorage.setItem('user', JSON.stringify(u))
  }, [data.access, data.user])

  const page = await ctx.newPage()
  const errors = []
  const bad5xx = []
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message))
  page.on('console', m => { if (m.type() === 'error') errors.push('CONSOLE: ' + m.text().slice(0, 200)) })
  page.on('response', r => { if (r.status() >= 500) bad5xx.push(r.status() + ' ' + r.url()) })

  // ---- 1. 新功能：部门业绩核算 ----
  await page.goto(BASE + '/performance/dept', { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const title = await page.locator('.page-title').first().textContent().catch(() => '')
  const deptRows = await page.locator('.el-table__body tr').count()
  const cards = await page.locator('.stat-card').count()
  console.log(`[部门业绩核算] 标题="${title}" 指标卡=${cards} 部门行=${deptRows}`)
  await page.screenshot({ path: '/tmp/shot_dept_perf.png', fullPage: true })

  // 侧栏菜单是否出现「部门业绩核算」
  const menuHas = await page.locator('.side-menu', { hasText: '部门业绩核算' }).count()
  console.log(`[侧栏] 含「部门业绩核算」= ${menuHas > 0}`)

  // ---- 2. 新功能：企业查询 → 国家电子税务局 ----
  await page.goto(BASE + '/sales/enterprise', { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  const taxBtn = page.locator('button', { hasText: '国家电子税务局' })
  const taxCount = await taxBtn.count()
  let popupUrl = ''
  if (taxCount) {
    const [popup] = await Promise.all([
      ctx.waitForEvent('page', { timeout: 8000 }).catch(() => null),
      taxBtn.first().click()
    ])
    if (popup) { popupUrl = popup.url(); await popup.close().catch(() => {}) }
  }
  console.log(`[企业查询] 税务局按钮=${taxCount} 跳转URL=${popupUrl}`)
  await page.screenshot({ path: '/tmp/shot_enterprise.png', fullPage: false })

  // ---- 3. 全站路由遍历 ----
  const routes = await page.evaluate(async () => {
    const res = await fetch('/src/router/index.js').catch(() => null)
    return null
  })
  const list = [
    '/dashboard', '/performance/dept', '/about',
    '/growth/channels', '/growth/leads', '/growth/pool', '/growth/field-tasks', '/growth/value-added', '/growth/stats',
    '/ops/dashboard', '/ops/budget', '/ops/input', '/ops/compare', '/ops/funnel', '/ops/content', '/ops/anchors', '/ops/performance', '/ops/target',
    '/sales/tools', '/sales/followup', '/sales/enterprise', '/sales/intention', '/sales/contracts', '/sales/customers',
    '/sales/renewal', '/sales/data-wall', '/sales/overview', '/sales/target',
    '/accounting/clients', '/accounting/tasks', '/accounting/declaration', '/accounting/business', '/accounting/overview', '/accounting/target',
    '/hr/org', '/hr/archive', '/hr/attendance', '/hr/leave', '/hr/approval', '/hr/salary', '/hr/labor-contracts', '/hr/permission',
    '/reports/daily', '/reports/weekly', '/reports/monthly', '/reports/review', '/reports/team',
    '/notices', '/membership/plans', '/membership/members', '/investment/policy', '/investment/inquiry',
    '/system/users', '/system/departments', '/system/op-logs', '/system/third-party-api', '/system/storage',
    '/onboarding/profile', '/onboarding/tasks', '/onboarding/exam', '/onboarding/business',
    '/contracts/sales', '/contracts/ops', '/growth/contracts', '/training/video'
  ]
  let navFail = 0
  for (const r of list) {
    try {
      await page.goto(BASE + r, { waitUntil: 'domcontentloaded', timeout: 25000 })
      await page.waitForTimeout(320)
      const body = await page.locator('body').innerText().catch(() => '')
      if (!body || body.length < 10) { navFail++; console.log('  空白页:', r) }
    } catch (e) { navFail++; console.log('  导航失败:', r, e.message.slice(0, 80)) }
  }
  console.log(`[遍历] 共 ${list.length} 条路由，导航异常 ${navFail} 条`)

  console.log(`\n[汇总] JS 报错 ${errors.length} 条 / 5xx ${bad5xx.length} 条`)
  errors.slice(0, 12).forEach(e => console.log('  !', e))
  bad5xx.slice(0, 12).forEach(e => console.log('  !', e))

  await browser.close()
})()
