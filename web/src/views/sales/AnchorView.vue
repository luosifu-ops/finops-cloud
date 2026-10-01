<template>
  <BaseListView
    title="主播管理"
    base-url="/sales/streamers/"
    :columns="columns"
    :form-fields="formFields"
    :search-fields="searchFields"
  />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import { orgApi } from '@/api'

const deptOptions = ref([])
const userOptions = ref([])

const columns = [
  { prop: 'name', label: '主播昵称', width: 130 },
  { prop: 'platform_name', label: '平台', width: 90 },
  { prop: 'account', label: '账号/主页ID', minWidth: 150 },
  { prop: 'department_name', label: '所属部门', width: 100 },
  { prop: 'manager_name', label: '负责人', width: 100 },
  { prop: 'status_name', label: '状态', width: 90 },
  { prop: 'fans_count', label: '粉丝数', width: 100, align: 'right' },
  { prop: 'live_count', label: '本月开播', width: 100, align: 'right' },
  { prop: 'gmv', label: '本月GMV', width: 120, align: 'right' },
  { prop: 'commission_rate', label: '提成%', width: 90, align: 'right' },
]

const searchFields = [
  { prop: 'platform', label: '平台', type: 'select', options: [
    { value: 'DOUYIN', label: '抖音' }, { value: 'KUAISHOU', label: '快手' },
    { value: 'VIDEO', label: '视频号' }, { value: 'RED', label: '小红书' }, { value: 'OTHER', label: '其他' },
  ] },
  { prop: 'status', label: '状态', type: 'select', options: [
    { value: 'ACTIVE', label: '开播中' }, { value: 'INACTIVE', label: '停播' }, { value: 'RESIGNED', label: '已离职' },
  ] },
]

const formFields = ref([
  { prop: 'name', label: '主播昵称', type: 'text', required: true },
  { prop: 'platform', label: '平台', type: 'select', required: true, options: [
    { value: 'DOUYIN', label: '抖音' }, { value: 'KUAISHOU', label: '快手' },
    { value: 'VIDEO', label: '视频号' }, { value: 'RED', label: '小红书' }, { value: 'OTHER', label: '其他' },
  ] },
  { prop: 'account', label: '账号/主页ID', type: 'text' },
  { prop: 'phone', label: '联系电话', type: 'text' },
  { prop: 'department', label: '所属部门', type: 'select', options: [] },
  { prop: 'manager', label: '负责人', type: 'select', options: [] },
  { prop: 'status', label: '状态', type: 'select', options: [
    { value: 'ACTIVE', label: '开播中' }, { value: 'INACTIVE', label: '停播' }, { value: 'RESIGNED', label: '已离职' },
  ] },
  { prop: 'entry_date', label: '入职日期', type: 'date' },
  { prop: 'fans_count', label: '粉丝数', type: 'number' },
  { prop: 'live_count', label: '本月开播场次', type: 'number' },
  { prop: 'gmv', label: '本月GMV(元)', type: 'number' },
  { prop: 'commission_rate', label: '提成比例(%)', type: 'number' },
  { prop: 'remark', label: '备注', type: 'textarea' },
])

onMounted(async () => {
  const [d, u] = await Promise.all([
    orgApi.departments({ page_size: 50 }),
    orgApi.users({ page_size: 300 }),
  ])
  const depts = d.results || d.data || []
  const users = u.results || u.data || []
  const deptOpts = depts.map(x => ({ value: x.id, label: x.name }))
  const userOpts = users.map(x => ({ value: x.id, label: x.name || x.first_name || x.username }))
  formFields.value = formFields.value.map(f => {
    if (f.prop === 'department') return { ...f, options: deptOpts }
    if (f.prop === 'manager') return { ...f, options: userOpts }
    return f
  })
})
</script>
