<template>
  <div>
    <el-tabs v-model="tab">
      <el-tab-pane label="采购申请" name="purchase" />
      <el-tab-pane label="用印申请" name="seal" />
    </el-tabs>
    <HrApprovableView v-if="tab==='purchase'" :key="'pc'" title="采购申请"
      baseUrl="/hr/purchases/" :columns="pc.columns" :formFields="pc.formFields" :depends="depends" />
    <HrApprovableView v-else :key="'sl'" title="用印申请"
      baseUrl="/hr/seals/" :columns="sl.columns" :formFields="sl.formFields" :depends="depends" />
  </div>
</template>
<script setup>
import { ref } from 'vue'
import HrApprovableView from './HrApprovableView.vue'
const tab = ref('purchase')
const depends = { user: '/accounts/users/' }
const pc = {
  columns: [
    { prop: 'applicant_name', label: '申请人', width: 110 },
    { prop: 'item_name', label: '采购物品', width: 140 },
    { prop: 'spec', label: '规格', width: 120 },
    { prop: 'quantity', label: '数量', width: 80 },
    { prop: 'amount', label: '预算(元)', width: 110 },
    { prop: 'purpose', label: '用途', minWidth: 180 },
    { prop: 'status_name', label: '状态', width: 100 },
  ],
  formFields: [
    { prop: 'item_name', label: '采购物品', type: 'text', required: true },
    { prop: 'spec', label: '规格/型号', type: 'text' },
    { prop: 'quantity', label: '数量', type: 'number' },
    { prop: 'amount', label: '预算金额', type: 'number' },
    { prop: 'purpose', label: '用途说明', type: 'textarea' },
    { prop: 'supplier', label: '建议供应商', type: 'text' },
  ],
}
const sl = {
  columns: [
    { prop: 'applicant_name', label: '申请人', width: 110 },
    { prop: 'type_name', label: '用印类型', width: 120 },
    { prop: 'doc_name', label: '用印文件', width: 160 },
    { prop: 'reason', label: '用印事由', minWidth: 220 },
    { prop: 'status_name', label: '状态', width: 100 },
  ],
  formFields: [
    { prop: 'seal_type', label: '用印类型', type: 'select', options: [
      { value: 'CONTRACT', label: '合同章' }, { value: 'FINANCE', label: '财务章' },
      { value: 'LEGAL', label: '公章' }, { value: 'INVOICE', label: '发票章' } ] },
    { prop: 'doc_name', label: '用印文件', type: 'text', required: true },
    { prop: 'reason', label: '用印事由', type: 'textarea' },
    { prop: 'use_date', label: '用印日期', type: 'date' },
  ],
}
</script>
