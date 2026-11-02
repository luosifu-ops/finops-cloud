<template>
  <div>
    <BaseListView ref="listRef" title="预算管理" baseUrl="/ops/budgets/" auto-form
      :form-fields="budgetFields">
      <template #row-actions="{ row }">
        <el-tag v-if="row.approve_status === 'PENDING'" type="warning" size="small">
          待审批{{ row.pending_budget ? `（申请 ${row.pending_budget}）` : '' }}
        </el-tag>
        <el-tag v-else-if="row.approve_status === 'REJECTED'" type="danger" size="small">已驳回</el-tag>
        <el-tag v-else type="success" size="small">已生效</el-tag>
        <template v-if="isManager && row.approve_status === 'PENDING'">
          <el-button link type="success" @click="doApprove(row)">通过</el-button>
          <el-button link type="danger" @click="doReject(row)">驳回</el-button>
        </template>
      </template>
    </BaseListView>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api'
import BaseListView from '@/components/BaseListView.vue'
import { useUserStore } from '@/store/user'

const store = useUserStore()
const isManager = computed(() => store.isBoss || store.isManager || store.isSuper)
const listRef = ref(null)

// 预算表单字段（覆盖 autoForm 推导，确保申请理由等字段可填）
const budgetFields = [
  { prop: 'month', label: '月份', type: 'text', required: true },
  { prop: 'platform', label: '平台编号', type: 'number', required: true },
  { prop: 'budget', label: '预算(元)', type: 'number', required: true },
  { prop: 'lead_target', label: '线索目标', type: 'number' },
  { prop: 'deal_target', label: '成交目标', type: 'number' },
  { prop: 'remark', label: '备注/申请理由', type: 'textarea' },
]

async function doApprove(row) {
  try {
    await ElMessageBox.confirm(
      `确认通过该预算调整？${row.month} 预算将变为 ${row.pending_budget} 元`, '审批通过', { type: 'warning' }
    )
  } catch { return }
  try {
    const r = await http.post(`/ops/budgets/${row.id}/approve/`, {})
    ElMessage.success(r?.msg || '已通过')
    listRef.value?.reload()
  } catch (e) { /* 拦截器已提示 */ }
}

async function doReject(row) {
  const r = await ElMessageBox.prompt('填写驳回理由', '驳回预算调整', {
    inputType: 'textarea', inputPlaceholder: '如：本月消耗超标，暂不追加'
  }).catch(() => null)
  if (!r) return
  try {
    const resp = await http.post(`/ops/budgets/${row.id}/reject/`, { reason: r.value || '' })
    ElMessage.success(resp?.msg || '已驳回')
    listRef.value?.reload()
  } catch (e) { /* 拦截器已提示 */ }
}
</script>
