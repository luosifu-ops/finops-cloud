<template>
  <div>
    <BaseListView ref="listRef" title="客户档案" baseUrl="/sales/customers/" auto-form>
      <template #row-actions="{ row }">
        <el-button link type="warning" @click="openTransfer(row)">转外勤</el-button>
      </template>
    </BaseListView>

    <FieldTransferDialog
      v-model="transferVisible"
      :customer-name="transferRow.name"
      :source-order-no="transferRow.customer_no"
      source-type="客户"
      @transferred="listRef?.reload()"
    />
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import BaseListView from '@/components/BaseListView.vue'
import FieldTransferDialog from '@/components/FieldTransferDialog.vue'

const listRef = ref(null)
const transferVisible = ref(false)
const transferRow = reactive({ name: '', customer_no: '' })
function openTransfer(row) {
  transferRow.name = row.customer_name || row.name || row.company_name || ''
  transferRow.customer_no = row.customer_no || row.code || ''
  transferVisible.value = true
}
</script>
