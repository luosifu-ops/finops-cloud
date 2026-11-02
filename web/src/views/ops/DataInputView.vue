<template>
  <BaseListView title="数据录入" baseUrl="/ops/daily-stats/" :form-fields="statForm" :can-delete="true" />
</template>

<script setup>
import BaseListView from '@/components/BaseListView.vue'

// 运营部·每日投放数据：补全新增 / 编辑 / 删除（此前为只读，电销部/运营无法维护投放明细）
// 平台/账户/计划 以 ID 维护；展示列表仍由后端 *_name 字段显示中文名称
const statForm = [
  { prop: 'date', label: '投放日期', type: 'date', required: true },
  { prop: 'platform', label: '平台ID', type: 'number', required: true },
  { prop: 'account', label: '账户ID', type: 'number', required: true },
  { prop: 'campaign', label: '计划ID', type: 'number' },
  { prop: 'cost', label: '花费(元)', type: 'number' },
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
</script>
