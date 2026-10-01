<template>
  <BaseListView ref="listRef" title="审批中心" baseUrl="/hr/approvals/" :can-delete="false">
    <template #row-actions="{ row }">
      <el-button
        v-if="row.status === 'PENDING'"
        link
        type="success"
        @click="handle(row, 'approve')"
      >通过</el-button>
      <el-button
        v-if="row.status === 'PENDING'"
        link
        type="danger"
        @click="handle(row, 'reject')"
      >驳回</el-button>
    </template>
  </BaseListView>
</template>

<script setup>
import { ref } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import http from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const listRef = ref(null)

async function handle(row, action) {
  const tip = action === 'approve' ? '确认通过该审批单？' : '确认驳回该审批单？'
  try {
    await ElMessageBox.confirm(tip, '审批操作', { type: action === 'approve' ? 'success' : 'warning' })
  } catch {
    return
  }
  try {
    await http.post(`/hr/approvals/${row.id}/handle/`, { action, remark: '' })
    ElMessage.success(action === 'approve' ? '已通过' : '已驳回')
    listRef.value && listRef.value.reload()
  } catch (e) {
    ElMessage.error('审批失败，请检查权限或重试')
  }
}
</script>
