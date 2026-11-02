<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">操作日志</h2>
        <span class="page-tip">全站操作留痕：谁在什么时间对什么做了什么（新增/修改/删除/导入/导出/审批）</span>
      </div>
      <el-button @click="load">刷新</el-button>
    </div>

    <el-card shadow="never">
      <div class="filters">
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD"
          range-separator="~" start-placeholder="开始日期" end-placeholder="结束日期" @change="load" style="width:240px" />
        <el-select v-model="filters.action" placeholder="全部动作" clearable style="width:130px" @change="load">
          <el-option v-for="(label, key) in ACTIONS" :key="key" :label="label" :value="key" />
        </el-select>
        <el-input v-model="filters.module" placeholder="功能模块" clearable style="width:150px" @keyup.enter="load" @clear="load" />
        <el-input v-model="filters.keyword" placeholder="操作人 / 对象摘要" clearable style="width:180px" @keyup.enter="load" @clear="load" />
        <el-button type="primary" @click="load">查询</el-button>
      </div>

      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="user_name" label="操作人" width="110" />
        <el-table-column prop="action_name" label="动作" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="tagType(row.action)" size="small">{{ row.action_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="功能模块" width="120" />
        <el-table-column prop="object_repr" label="操作对象" min-width="200" show-overflow-tooltip />
        <el-table-column prop="detail" label="变更明细" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">{{ row.detail || '—' }}</template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="130">
          <template #default="{ row }">{{ row.ip || '—' }}</template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination background layout="total, prev, pager, next" :total="total"
          :page-size="pageSize" :current-page="page" @current-change="onPage" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { commonApi } from '@/api'

const ACTIONS = { CREATE: '新增', UPDATE: '修改', DELETE: '删除', BULK_DELETE: '批量删除', IMPORT: '导入', EXPORT: '导出', APPROVE: '审批通过', REJECT: '审批驳回', ASSIGN: '分配', RETURN: '退回', LOGIN: '登录', OTHER: '其他' }
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const dateRange = ref(null)
const filters = reactive({ action: '', module: '', keyword: '' })

const fmtTime = (t) => (t ? String(t).replace('T', ' ').slice(0, 19) : '—')
const tagType = (a) => ({ CREATE: 'success', DELETE: 'danger', BULK_DELETE: 'danger', REJECT: 'danger', UPDATE: 'warning', APPROVE: 'success', LOGIN: 'info' }[a] || 'info')

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (dateRange.value?.[0]) params.start_date = dateRange.value[0]
    if (dateRange.value?.[1]) params.end_date = dateRange.value[1]
    for (const k of ['action', 'module', 'keyword']) if (filters[k]) params[k] = filters[k]
    const r = await commonApi.opLogs(params)
    const payload = r?.data || r || {}
    list.value = payload.results || []
    total.value = payload.count || list.value.length
  } finally { loading.value = false }
}
function onPage(p) { page.value = p; load() }
onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.page-tip { font-size: 12px; color: var(--text-sub); font-weight: 400; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.pager { margin-top: 14px; display: flex; justify-content: flex-end; }
</style>
