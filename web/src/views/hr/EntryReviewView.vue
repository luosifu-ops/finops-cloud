<template>
  <div class="entry-review">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>入职申请审核 · 人事管理员</span>
          <div>
            <el-radio-group v-model="filter" size="small" @change="loadData">
              <el-radio-button label="待审核">待审核</el-radio-button>
              <el-radio-button label="全部">全部</el-radio-button>
            </el-radio-group>
            <el-button style="margin-left:8px" @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" border stripe size="default" max-height="560">
        <el-table-column prop="applicant_name" label="申请人" width="110" />
        <el-table-column prop="phone" label="联系电话" width="140" />
        <el-table-column prop="department_name" label="意向部门" width="110" />
        <el-table-column prop="position_name" label="意向岗位" width="110" />
        <el-table-column label="期望薪资" width="120">
          <template #default="{ row }">{{ num(row.expected_salary) }} 元</template>
        </el-table-column>
        <el-table-column label="简历" width="90">
          <template #default="{ row }">
            <el-button v-if="row.resume_url" link type="primary" @click="openUrl(row.resume_url)">查看</el-button>
            <span v-else class="muted">无</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status==='PENDING'?'warning':(row.status==='APPROVED'?'success':'danger')" size="small">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reviewed_by_name" label="审核人" width="100" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'PENDING'">
              <el-button link type="success" @click="approve(row)">通过</el-button>
              <el-button link type="danger" @click="reject(row)">拒绝</el-button>
            </template>
            <span v-else class="muted">已处理</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { orgApi } from '@/api/index'

const list = ref([])
const loading = ref(false)
const filter = ref('待审核')

function num(v) { const n = Number(v || 0); return n ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '0' }
function openUrl(u) { if (u) window.open(u, '_blank') }

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filter.value === '待审核') params.status = 'PENDING'
    const r = await orgApi.entries(params)
    list.value = Array.isArray(r) ? r : (r.results || [])
  } finally { loading.value = false }
}

async function approve(row) {
  const ok = await ElMessageBox.confirm(`确认通过 ${row.applicant_name} 的入职申请？通过后自动创建员工账号并归入对应部门/岗位。`, '审核通过', { type: 'warning' }).then(() => true).catch(() => false)
  if (!ok) return
  try {
    await orgApi.approveEntry(row.id)
    ElMessage.success('已通过，员工账号已创建')
    loadData()
  } catch (e) {}
}

async function reject(row) {
  const { value } = await ElMessageBox.prompt('填写拒绝原因', '拒绝申请', { inputType: 'textarea', inputPlaceholder: '如：资料不符 / 暂不录用' }).catch(() => ({ value: null }))
  if (value === null) return
  try {
    await orgApi.rejectEntry(row.id, { reject_reason: value || '' })
    ElMessage.success('已拒绝')
    loadData()
  } catch (e) {}
}

onMounted(loadData)
</script>

<style scoped>
.entry-review { padding: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.muted { color: #909399; }
</style>
