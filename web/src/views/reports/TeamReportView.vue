<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">团队汇报</h2>
        <p class="page-sub">
          员工提交日报 / 周报 / 月报后自动汇总到「团队汇总」；主管可直接编辑修改汇总内容
        </p>
      </div>
      <div class="page-actions">
        <el-button type="primary" plain :loading="loading" @click="loadSummaries">刷新汇总</el-button>
      </div>
    </div>

    <el-tabs v-model="tab" class="rep-tabs">
      <!-- ① 原有汇报明细（保持原行为不变） -->
      <el-tab-pane label="汇报明细" name="detail">
        <BaseListView
          title="团队汇报明细"
          baseUrl="/reports/daily-reports/team/"
          read-only
          raw-array
          :can-delete="false"
        />
      </el-tab-pane>

      <!-- ② 新增：团队汇总 -->
      <el-tab-pane label="团队汇总" name="summary">
        <div class="card sum-card">
          <el-form :inline="true" class="filter-bar">
            <el-form-item label="汇总类型">
              <el-select v-model="filters.kind" placeholder="全部" clearable style="width:150px">
                <el-option label="日报汇总" value="DAILY" />
                <el-option label="周报汇总" value="WEEKLY" />
                <el-option label="月报汇总" value="MONTHLY" />
              </el-select>
            </el-form-item>
            <el-form-item label="周期">
              <el-input v-model="filters.period" placeholder="如 2026-10-30 / 2026-W44 / 2026-10"
                        clearable style="width:210px" @keyup.enter="loadSummaries" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" plain @click="loadSummaries">查询</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="summaries" v-loading="loading" border stripe size="default" max-height="560">
            <el-table-column prop="title" label="汇总标题" min-width="240" show-overflow-tooltip />
            <el-table-column label="类型" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="kindTag(row.kind)">{{ row.kind_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="部门 / 小组" min-width="150">
              <template #default="{ row }">
                <span>{{ row.department_name || '全公司' }}</span>
                <span v-if="row.team_name" class="muted"> · {{ row.team_name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="period_label" label="周期" width="150" />
            <el-table-column label="提交 / 在职" width="120" align="center">
              <template #default="{ row }">
                <span class="cnt">{{ row.submitted_total }}</span>
                <span class="muted"> / {{ row.member_total }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.is_edited" size="small" type="warning">已人工编辑</el-tag>
                <el-tag v-else size="small" type="info">自动汇总</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="170">
              <template #default="{ row }">{{ fmt(row.updated_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="170" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openSummary(row)">查看 / 编辑</el-button>
                <el-button link type="warning" @click="rebuildOne(row)">重新生成</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loading && !summaries.length" description="暂无团队汇总，员工提交汇报后自动生成" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 汇总详情 / 编辑 -->
    <el-dialog v-model="dlgVisible" :title="current?.title || '团队汇总'" width="820px" top="6vh">
      <template v-if="current">
        <el-descriptions :column="4" border size="small" class="sum-desc">
          <el-descriptions-item label="类型">{{ current.kind_label }}</el-descriptions-item>
          <el-descriptions-item label="周期">{{ current.period_label }}</el-descriptions-item>
          <el-descriptions-item label="部门">{{ current.department_name || '全公司' }}</el-descriptions-item>
          <el-descriptions-item label="提交 / 在职">
            {{ current.submitted_total }} / {{ current.member_total }}
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin:10px 0"
          title="汇总正文可直接编辑；保存后标记为「已人工编辑」，后续自动汇总只刷新统计，不再覆盖你修改过的内容"
        />
        <el-input v-model="editContent" type="textarea" :rows="16" resize="vertical" />
        <div v-if="current.is_edited" class="muted" style="margin-top:8px">
          最后编辑：{{ current.edited_by_name || '-' }} · {{ fmt(current.edited_at) }}
        </div>
      </template>
      <template #footer>
        <el-button @click="dlgVisible = false">关闭</el-button>
        <el-button type="warning" plain :loading="rebuilding" @click="rebuildCurrent">重新生成</el-button>
        <el-button type="primary" :loading="saving" @click="saveSummary">保存修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BaseListView from '@/components/BaseListView.vue'
import http from '@/api'

const tab = ref('detail')
const summaries = ref([])
const loading = ref(false)
const filters = reactive({ kind: '', period: '' })

const dlgVisible = ref(false)
const current = ref(null)
const editContent = ref('')
const saving = ref(false)
const rebuilding = ref(false)

function kindTag(k) {
  return { DAILY: 'primary', WEEKLY: 'success', MONTHLY: 'warning' }[k] || 'info'
}
function fmt(t) {
  return t ? String(t).slice(0, 19).replace('T', ' ') : '-'
}

async function loadSummaries() {
  loading.value = true
  try {
    const params = {}
    if (filters.kind) params.kind = filters.kind
    if (filters.period) params.period = filters.period.trim()
    const res = await http.get('/reports/team-summaries/', { params })
    summaries.value = Array.isArray(res) ? res : (res.results || [])
  } catch (e) {
    summaries.value = []
  } finally {
    loading.value = false
  }
}

function openSummary(row) {
  current.value = row
  editContent.value = row.content || ''
  dlgVisible.value = true
}

async function saveSummary() {
  if (!current.value) return
  saving.value = true
  try {
    const res = await http.patch(`/reports/team-summaries/${current.value.id}/`, {
      content: editContent.value,
    })
    ElMessage.success('汇总内容已保存')
    const updated = res?.data || res
    if (updated && updated.id) current.value = updated
    loadSummaries()
  } catch (e) { /* 拦截器已提示 */ } finally {
    saving.value = false
  }
}

async function rebuildCurrent() {
  if (!current.value) return
  try {
    await ElMessageBox.confirm(
      '将按最新汇报重新生成正文，你会覆盖当前人工修改的内容，确认继续？', '重新生成',
      { type: 'warning' }
    )
  } catch { return }
  rebuilding.value = true
  try {
    const res = await http.post(`/reports/team-summaries/${current.value.id}/rebuild/`)
    ElMessage.success('已按最新汇报重新生成')
    const updated = res?.data || res
    if (updated && updated.id) {
      current.value = updated
      editContent.value = updated.content || ''
    }
    loadSummaries()
  } catch (e) { /* 拦截器已提示 */ } finally {
    rebuilding.value = false
  }
}

async function rebuildOne(row) {
  try {
    await ElMessageBox.confirm(`确认按最新汇报重新生成「${row.title}」？`, '重新生成', { type: 'warning' })
  } catch { return }
  try {
    await http.post(`/reports/team-summaries/${row.id}/rebuild/`)
    ElMessage.success('已重新生成')
    loadSummaries()
  } catch (e) { /* 拦截器已提示 */ }
}

onMounted(loadSummaries)
</script>

<style scoped>
.page { padding: 4px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
.page-title { font-size: 19px; font-weight: 700; color: #1f2d3d; margin: 0; }
.page-sub { margin: 6px 0 0; font-size: 12.5px; color: #909399; }
.rep-tabs :deep(.el-tabs__header) { margin-bottom: 12px; }
.card { background: #fff; border-radius: 12px; padding: 14px; border: 1px solid #ebeef5; }
.filter-bar { margin-bottom: 6px; }
.muted { color: #909399; }
.cnt { font-weight: 600; color: #2f6bff; }
.sum-desc { margin-bottom: 6px; }
</style>
