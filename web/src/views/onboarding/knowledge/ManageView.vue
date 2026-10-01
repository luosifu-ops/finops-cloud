<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">知识库维护</h2>
      <el-tag type="info" effect="plain">代理记账 / 税务 / 发票 / 工商 / 社保 / 法规 / 软件 / 话术</el-tag>
    </div>

    <el-alert v-if="!canManage" type="warning" :closable="false" show-icon title="仅限老板或人事维护" />

    <BaseListView
      v-else
      title="知识文章"
      baseUrl="/onboarding/articles/"
      :columns="columns"
      :formFields="formFields"
      :searchFields="searchFields"
      dialogWidth="640px"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const canManage = computed(() => userStore.isBoss || userStore.isHR)

const categoryOptions = [
  { value: 'agency', label: '代理记账基础' },
  { value: 'tax', label: '税务知识' },
  { value: 'invoice', label: '发票管理' },
  { value: 'business', label: '工商注册/变更/注销' },
  { value: 'social', label: '社保公积金' },
  { value: 'law', label: '财税法规' },
  { value: 'software', label: '做账软件操作' },
  { value: 'sale', label: '销售话术' },
]

const levelOptions = [
  { value: 'BASIC', label: '入门' },
  { value: 'MIDDLE', label: '进阶' },
  { value: 'ADVANCED', label: '高阶' },
]

const columns = [
  { prop: 'title', label: '标题', minWidth: 200 },
  { prop: 'category', label: '分类', width: 150 },
  { prop: 'level', label: '难度', width: 90 },
  { prop: 'is_required', label: '必修', width: 80 },
  { prop: 'sort', label: '排序', width: 80 },
  { prop: 'view_count', label: '阅读量', width: 90 },
]

const searchFields = [
  { prop: 'category', label: '分类', type: 'select', options: categoryOptions },
]

const formFields = [
  { prop: 'title', label: '标题', type: 'text', required: true },
  { prop: 'category', label: '分类', type: 'select', options: categoryOptions, required: true },
  { prop: 'level', label: '难度', type: 'select', options: levelOptions },
  { prop: 'summary', label: '摘要', type: 'textarea' },
  { prop: 'content', label: '正文', type: 'textarea' },
  { prop: 'tags', label: '标签', type: 'text' },
  { prop: 'is_required', label: '是否必修', type: 'switch' },
  { prop: 'sort', label: '排序', type: 'number' },
]
</script>

<style scoped>
.page-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
</style>
