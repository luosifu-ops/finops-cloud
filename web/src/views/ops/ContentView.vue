<template>
  <BaseListView ref="listRef" title="内容运营" baseUrl="/ops/content-posts/" auto-form>
    <template #row-actions="{ row }">
      <el-button v-if="row.status === 'PUBLISHED'" link type="warning" @click="toggle(row, 'OFFLINE')">下架</el-button>
      <el-button v-else-if="row.status === 'OFFLINE' || row.publish_at" link type="success" @click="toggle(row, 'PUBLISHED')">上架</el-button>
    </template>
  </BaseListView>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api'
import BaseListView from '@/components/BaseListView.vue'

const listRef = ref(null)
async function toggle(row, status) {
  try {
    const payload = { status }
    if (status === 'PUBLISHED' && !row.publish_at) payload.publish_at = new Date().toISOString().slice(0, 19).replace('T', ' ')
    await http.patch(`/ops/content-posts/${row.id}/`, payload)
    ElMessage.success(status === 'PUBLISHED' ? '已上架' : '已下架')
    listRef.value?.reload()
  } catch (e) { /* 拦截器已提示 */ }
}
</script>
