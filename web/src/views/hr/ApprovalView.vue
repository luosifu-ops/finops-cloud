<template>
  <BaseListView ref="listRef" title="审批中心" baseUrl="/hr/approvals/" :can-delete="false"
    @selection-change="onSel">
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
    <!-- 2026-10-30 增量：批量通过 / 批量驳回（Boss 专项：按钮永远可点，未勾选时点击给出引导提示） -->
    <template #header-extra>
      <el-button type="success" plain @click="bulkHandle('approve')">
        批量通过{{ sel.length ? `(${sel.length})` : '' }}
      </el-button>
      <el-button type="danger" plain @click="bulkHandle('reject')">
        批量驳回{{ sel.length ? `(${sel.length})` : '' }}
      </el-button>
    </template>
  </BaseListView>
</template>

<script setup>
import { ref } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import http from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

const listRef = ref(null)
const sel = ref([])

function onSel(rows) {
  sel.value = rows || []
}

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

async function bulkHandle(action) {
  const ids = sel.value.filter(r => r.status === 'PENDING').map(r => r.id)
  if (!ids.length) return ElMessage.warning('请先勾选待审批（PENDING）的审批单')
  let remark = ''
  if (action === 'reject') {
    try {
      const r = await ElMessageBox.prompt(
        `将对选中的 ${ids.length} 条审批单批量驳回，请填写驳回理由（必填）`,
        '批量驳回', { type: 'warning', confirmButtonText: '确认驳回', cancelButtonText: '取消',
          inputPlaceholder: '驳回理由', inputValidator: v => !!(v && v.trim()) || '驳回理由不能为空' }
      )
      remark = r.value
    } catch { return }
  } else {
    try {
      await ElMessageBox.confirm(`确认批量通过选中的 ${ids.length} 条审批单？`, '批量通过', { type: 'success' })
    } catch { return }
  }
  try {
    const resp = await http.post('/hr/approvals/bulk-handle/', { ids, action, remark })
    const data = resp?.data || resp || {}
    const okN = data.success ?? 0
    const badN = data.failed ?? 0
    if (badN > 0) ElMessage.warning(`成功 ${okN} 条，失败 ${badN} 条（无权限或已结束的单子自动跳过）`)
    else ElMessage.success(`批量${action === 'approve' ? '通过' : '驳回'}成功（${okN} 条）`)
    sel.value = []
    listRef.value && listRef.value.reload()
  } catch (e) {
    ElMessage.error('批量审批失败，请检查权限或重试')
  }
}
</script>
