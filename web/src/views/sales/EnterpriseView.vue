<template>
  <div class="ent">
    <el-alert
      v-if="!live"
      type="warning"
      :closable="false"
      show-icon
      title="当前为演示数据"
      description="在后端配置 QICHACHA_API_KEY / TIANYANCHA_API_KEY 后显示真实工商数据。"
      style="margin-bottom:12px"
    />

    <!-- 单搜索框 -->
    <el-card class="ent-search" shadow="never">
      <el-input
        v-model="keyword"
        placeholder="输入企业名称 / 法人姓名 / 联系电话 / 统一社会信用代码，支持模糊查询"
        clearable
        size="large"
        style="max-width:640px"
        @keyup.enter="search"
      >
        <template #prepend><el-icon><Search /></el-icon></template>
        <template #append>
          <el-button type="primary" :loading="loading" @click="search">查 询</el-button>
        </template>
      </el-input>

      <!-- 历史记录 -->
      <div v-if="history.length" class="ent-history">
        <span class="eh-label">历史：</span>
        <el-tag
          v-for="h in history"
          :key="h"
          class="eh-tag"
          @click="useHistory(h)"
          @close="removeHistory(h)"
          closable
          type="info"
        >{{ h }}</el-tag>
      </div>

      <!-- 高级筛选 -->
      <el-collapse class="ent-adv">
        <el-collapse-item title="高级筛选（按字段精确查询）" name="1">
          <el-form :inline="true" @submit.prevent>
            <el-form-item label="企业名称"><el-input v-model="adv.name" placeholder="如 云创科技" clearable style="width:180px" @keyup.enter="searchAdv" /></el-form-item>
            <el-form-item label="法人姓名"><el-input v-model="adv.legal" placeholder="如 张伟" clearable style="width:150px" @keyup.enter="searchAdv" /></el-form-item>
            <el-form-item label="联系电话"><el-input v-model="adv.phone" placeholder="如 138..." clearable style="width:170px" @keyup.enter="searchAdv" /></el-form-item>
            <el-form-item label="信用代码"><el-input v-model="adv.credit_code" placeholder="统一社会信用代码" clearable style="width:220px" @keyup.enter="searchAdv" /></el-form-item>
            <el-form-item><el-button type="primary" :loading="loading" @click="searchAdv">精确查询</el-button></el-form-item>
          </el-form>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 结果弹窗 -->
    <el-dialog v-model="dialog" title="企业查询结果" width="960px" top="5vh" @closed="onClose">
      <template v-if="results.length">
        <div class="ent-body">
          <div class="ent-left">
            <div
              v-for="c in results"
              :key="c.credit_code"
              class="ent-item"
              :class="{ active: selected && c.credit_code === selected.credit_code }"
              @click="select(c)"
            >
              <div class="ei-name">{{ c.name }}</div>
              <div class="ei-code">{{ c.credit_code }}</div>
              <el-tag size="small" :type="c.status === '注销' ? 'info' : 'success'">{{ c.status }}</el-tag>
            </div>
          </div>

          <div class="ent-right" v-if="selected">
            <el-tabs v-model="tab">
              <el-tab-pane label="工商基本信息" name="base">
                <el-descriptions :column="2" border>
                  <el-descriptions-item label="企业名称">{{ sel.base_info?.name }}</el-descriptions-item>
                  <el-descriptions-item label="统一社会信用代码">{{ sel.base_info?.credit_code }}</el-descriptions-item>
                  <el-descriptions-item label="法定代表人">{{ sel.base_info?.legal }}</el-descriptions-item>
                  <el-descriptions-item label="联系电话">{{ sel.base_info?.phone }}</el-descriptions-item>
                  <el-descriptions-item label="注册资本">{{ sel.base_info?.capital }}</el-descriptions-item>
                  <el-descriptions-item label="成立日期">{{ sel.base_info?.established }}</el-descriptions-item>
                  <el-descriptions-item label="登记状态">
                    <el-tag :type="sel.base_info?.status === '注销' ? 'info' : 'success'">{{ sel.base_info?.status }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="注册地址" :span="2">{{ sel.base_info?.address }}</el-descriptions-item>
                  <el-descriptions-item label="经营范围" :span="2">{{ sel.base_info?.scope }}</el-descriptions-item>
                </el-descriptions>
                <el-button type="success" plain style="margin-top:12px" @click="toLead">转为线索</el-button>
              </el-tab-pane>

              <el-tab-pane label="电子营业执照" name="license">
                <div class="lic">
                  <img :src="sel.license?.image" alt="电子营业执照" class="lic-img" />
                  <div class="lic-ops">
                    <el-button type="primary" @click="downloadLicense">下载电子营业执照</el-button>
                    <p class="lic-note">※ 演示样本，真实电子营业执照请通过「电子营业执照」官方小程序 / 系统获取。</p>
                  </div>
                </div>
              </el-tab-pane>

              <el-tab-pane label="电子税务局" name="tax">
                <div class="tax-head">
                  <el-tag :type="sel.tax?.taxpayer_status === '正常' ? 'success' : 'danger'">纳税人状态：{{ sel.tax?.taxpayer_status }}</el-tag>
                  <el-tag effect="plain">身份：{{ sel.tax?.taxpayer_type }}</el-tag>
                  <el-tag :type="(sel.tax?.owed || 0) > 0 ? 'danger' : 'success'">欠税：{{ sel.tax?.owed }} 元</el-tag>
                  <el-button type="primary" link @click="openPortal(sel.tax?.portal_url)">前往电子税务局 ›</el-button>
                </div>
                <el-table :data="sel.tax?.declarations || []" border style="margin-top:12px">
                  <el-table-column prop="period" label="属期" width="120" />
                  <el-table-column prop="category" label="税种" />
                  <el-table-column prop="status" label="申报状态" width="120" />
                  <el-table-column prop="amount" label="税额(元)" width="140" />
                </el-table>
                <p class="lic-note">发票额度：{{ sel.tax?.invoice_quota }}</p>
              </el-tab-pane>
            </el-tabs>
          </div>
        </div>
      </template>

      <el-empty v-else description="未查询到匹配企业">
        <div class="ent-guide">
          <span>试试这些示例：</span>
          <el-tag
            v-for="e in examples"
            :key="e"
            class="eg-tag"
            @click="useExample(e)"
          >{{ e }}</el-tag>
        </div>
      </el-empty>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { integrationApi, salesApi } from '@/api'

const keyword = ref('')
const adv = ref({ name: '', legal: '', phone: '', credit_code: '' })
const loading = ref(false)
const dialog = ref(false)
const results = ref([])
const selected = ref(null)
const sel = ref({})
const tab = ref('base')
const live = ref(false)
const history = ref([])
const HISTORY_KEY = 'ent_search_history'
const examples = ['云南财税', '张伟', '13887123456']

function unwrap(resp) {
  if (!resp) return []
  if (Array.isArray(resp)) return resp
  if (resp.data && Array.isArray(resp.data.results)) return resp.data.results
  if (resp.data && Array.isArray(resp.data.list)) return resp.data.list
  if (resp.data && Array.isArray(resp.data)) return resp.data
  if (resp.results) return resp.results
  if (resp.list) return resp.list
  return resp.data ? [resp.data] : []
}

function loadHistory() {
  try { history.value = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch (e) { history.value = [] }
}
function pushHistory(k) {
  if (!k) return
  history.value = [k, ...history.value.filter(x => x !== k)].slice(0, 8)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
}
function removeHistory(k) {
  history.value = history.value.filter(x => x !== k)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
}
function useHistory(k) { keyword.value = k; search() }

async function search() {
  const k = keyword.value.trim()
  if (!k) { ElMessage.warning('请输入企业名称 / 法人 / 电话 / 信用代码'); return }
  loading.value = true
  dialog.value = true
  try {
    const r = await integrationApi.enterpriseSearch({ q: k })
    results.value = unwrap(r)
    if (results.value.length) { pushHistory(k); await select(results.value[0]) }
    else { selected.value = null; ElMessage.info('未找到匹配企业（演示数据）') }
  } catch (e) {
    results.value = []
  } finally { loading.value = false }
}

async function searchAdv() {
  const p = {}
  if (adv.value.name.trim()) p.name = adv.value.name.trim()
  if (adv.value.legal.trim()) p.legal = adv.value.legal.trim()
  if (adv.value.phone.trim()) p.phone = adv.value.phone.trim()
  if (adv.value.credit_code.trim()) p.credit_code = adv.value.credit_code.trim()
  if (!Object.keys(p).length) { ElMessage.warning('请至少填写一个精确条件'); return }
  loading.value = true
  dialog.value = true
  try {
    const r = await integrationApi.enterpriseSearch(p)
    results.value = unwrap(r)
    if (results.value.length) await select(results.value[0])
    else { selected.value = null; ElMessage.info('未找到匹配企业（演示数据）') }
  } catch (e) {
    results.value = []
  } finally { loading.value = false }
}

async function select(c) {
  selected.value = c
  tab.value = 'base'
  try {
    const r = await integrationApi.enterpriseDetail(c.credit_code)
    sel.value = r.data || {}
    live.value = sel.value.source !== 'demo'
  } catch (e) {
    sel.value = {}
  }
}

function useExample(e) { keyword.value = e; search() }

function downloadLicense() {
  const lic = sel.value.license
  if (!lic) return
  const a = document.createElement('a')
  a.href = lic.image
  a.download = lic.download_name || '电子营业执照.svg'
  a.click()
  ElMessage.success('已开始下载（演示样本）')
}

async function toLead() {
  const base = sel.value.base_info || {}
  if (!base.name) { ElMessage.warning('暂无企业信息'); return }
  try {
    await ElMessageBox.confirm(`将「${base.name}」转为线索？`, '转为线索', { type: 'info' })
  } catch { return }
  try {
    await salesApi.createLead({
      company: base.name,
      phone: base.phone,
      credit_code: base.credit_code,
      legal: base.legal,
      remark: '企业查询转入',
    })
    ElMessage.success('已转为线索')
  } catch (e) {
    ElMessage.error('创建线索失败，请稍后重试')
  }
}

function openPortal(url) { if (url) window.open(url, '_blank') }
function onClose() { selected.value = null; sel.value = {}; results.value = [] }

loadHistory()
</script>

<style scoped>
.ent-search { margin-bottom: 14px; }
.ent-history { margin-top: 12px; display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.eh-label { color: var(--text-sub); font-size: 13px; }
.eh-tag { cursor: pointer; }
.ent-adv { margin-top: 6px; border: none; }
.ent-body { display: flex; gap: 16px; background: #fff; border-radius: 10px; }
.ent-left { width: 280px; max-height: 560px; overflow-y: auto; border-right: 1px solid var(--border); padding-right: 12px; }
.ent-item { padding: 10px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; cursor: pointer; transition: .15s; }
.ent-item:hover { border-color: var(--primary); }
.ent-item.active { border-color: var(--primary); background: var(--primary-50); }
.ei-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.ei-code { font-size: 12px; color: var(--text-sub); margin-bottom: 6px; }
.ent-right { flex: 1; min-width: 0; }
.lic { display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
.lic-img { width: 320px; border: 1px solid var(--border); border-radius: 8px; }
.lic-ops { flex: 1; min-width: 240px; }
.lic-note { color: var(--text-sub); font-size: 12px; line-height: 1.7; margin-top: 10px; }
.tax-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ent-guide { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: center; }
.eg-tag { cursor: pointer; }
</style>
