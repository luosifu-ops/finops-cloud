<template>
  <HrGenericView title="外部联系人" baseUrl="/hr/external-contacts/"
    :columns="columns" :formFields="formFields" :depends="depends" />
</template>
<script setup>
import HrGenericView from './HrGenericView.vue'
const columns = [
  { prop: 'name', label: '姓名', width: 120 },
  { prop: 'group_name', label: '分组', width: 120 },
  { prop: 'company', label: '单位', minWidth: 140 },
  { prop: 'phone', label: '电话', width: 140 },
  { prop: 'wechat', label: '微信', width: 120 },
  { prop: 'owner_name', label: '负责人', width: 120 },
  { prop: 'remark', label: '备注', minWidth: 160 },
]
const formFields = [
  { prop: 'name', label: '姓名', type: 'text', required: true },
  { prop: 'group', label: '分组', type: 'select', options: [
    { value: 'CUSTOMER', label: '客户' }, { value: 'CHANNEL', label: '渠道合作方' }, { value: 'OTHER', label: '其他' } ] },
  { prop: 'company', label: '单位', type: 'text' },
  { prop: 'phone', label: '电话', type: 'text' },
  { prop: 'wechat', label: '微信', type: 'text' },
  { prop: 'position', label: '职位', type: 'text' },
  { prop: 'owner', label: '负责人', type: 'select', depends: 'user' },
  { prop: 'remark', label: '备注', type: 'textarea' },
]
const depends = { user: '/accounts/users/' }
</script>
