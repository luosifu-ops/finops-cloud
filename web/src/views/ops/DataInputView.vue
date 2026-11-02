<template>
  <div>
    <!-- ========== 每日投放数据录入（成本字段已并入表单，2026-11-02 Boss 指示） ========== -->
    <BaseListView title="每日投放数据" baseUrl="/ops/daily-stats/" :form-fields="statForm"
      :can-delete="true" :option-sources="statOptions" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import http from '@/api'

// ---------- 每日投放数据（原字段全部保留 + 新增「成本(元)」） ----------
const statForm = [
  { prop: 'date', label: '投放日期', type: 'date', required: true },
  { prop: 'platform', label: '投放平台', type: 'select', required: true },
  { prop: 'account', label: '投放账户', type: 'select' },
  { prop: 'campaign', label: '推广计划', type: 'select' },
  { prop: 'cost', label: '花费(元)', type: 'number' },
  { prop: 'cost_input', label: '成本(元)', type: 'number' },
  { prop: 'impression', label: '展现量', type: 'number' },
  { prop: 'click', label: '点击量', type: 'number' },
  { prop: 'lead_count', label: '线索数', type: 'number' },
  { prop: 'valid_lead', label: '有效线索', type: 'number' },
  { prop: 'phone_added', label: '电话数', type: 'number' },
  { prop: 'wechat_added', label: '加微数', type: 'number' },
  { prop: 'visit_count', label: '访问量', type: 'number' },
  { prop: 'deal_count', label: '成交数', type: 'number' },
  { prop: 'deal_amount', label: '成交金额(元)', type: 'number' },
  { prop: 'remark', label: '备注', type: 'textarea' },
]

// ---------- 字典下拉（平台/账户/计划），替代原「手填ID」 ----------
const statOptions = ref({ platform: [], account: [], campaign: [] })

async function loadDicts() {
  try {
    const [ps, as_, cs] = await Promise.all([
      http.get('/ops/platforms/?page_size=200'),
      http.get('/ops/accounts/?page_size=200').catch(() => null),
      http.get('/ops/campaigns/?page_size=200').catch(() => null),
    ])
    const unwrap = (r) => {
      let body = r || {}
      if (body && typeof body === 'object' && 'code' in body && 'data' in body) body = body.data
      return Array.isArray(body) ? body : (body?.results || [])
    }
    const platforms = unwrap(ps).map((p) => ({ value: p.id, label: p.name }))
    const accounts = unwrap(as_).map((a) => ({
      value: a.id,
      label: a.platform_name ? `${a.platform_name} · ${a.name}` : a.name,
    }))
    const campaigns = unwrap(cs).map((c) => ({ value: c.id, label: c.name }))
    statOptions.value = { platform: platforms, account: accounts, campaign: campaigns }
  } catch (e) { /* 拦截器已提示 */ }
}

onMounted(loadDicts)
</script>
