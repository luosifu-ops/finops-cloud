<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">制度维护</h2>
      <el-tag type="info" effect="plain">考勤 / 薪酬 / 奖惩 / 保密 / 报销 / 行为规范</el-tag>
    </div>

    <el-alert v-if="!canManage" type="warning" :closable="false" show-icon title="仅限老板或人事维护" />

    <BaseListView
      v-else
      title="公司制度"
      baseUrl="/onboarding/regulations/"
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
  { value: 'ATTENDANCE', label: '考勤制度' },
  { value: 'SALARY', label: '薪酬绩效制度' },
  { value: 'REWARD', label: '奖惩制度' },
  { value: 'SECRET', label: '保密与合规' },
  { value: 'EXPENSE', label: '费用报销' },
  { value: 'BEHAVIOR', label: '行为规范' },
]

const columns = [
  { prop: 'title', label: '制度名称', minWidth: 180 },
  { prop: 'category', label: '分类', width: 130, options: categoryOptions },
  { prop: 'version', label: '版本号', width: 100 },
  { prop: 'effective_date', label: '生效日期', width: 130 },
  { prop: 'must_read', label: '要求已读', width: 100 },
  { prop: 'is_published', label: '已发布', width: 90 },
]

const searchFields = [
  { prop: 'category', label: '分类', type: 'select', options: categoryOptions },
]

const formFields = [
  { prop: 'title', label: '制度名称', type: 'text', required: true },
  { prop: 'category', label: '分类', type: 'select', options: categoryOptions, required: true },
  { prop: 'version', label: '版本号', type: 'text' },
  { prop: 'effective_date', label: '生效日期', type: 'date' },
  { prop: 'content', label: '正文', type: 'textarea' },
  { prop: 'must_read', label: '要求已读', type: 'switch' },
  { prop: 'is_published', label: '是否发布', type: 'switch' },
]
</script>

<style scoped>
.page-header { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
</style>
