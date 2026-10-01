<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">{{ title }} · 员工业绩目标与达成进度</h2>
      <el-date-picker v-model="month" type="month" value-format="YYYY-MM"
                      placeholder="选择月份" style="width: 150px" @change="load" />
    </div>

    <!-- 部门汇总 -->
    <el-card shadow="never" class="sum-card" v-if="summary">
      <el-row :gutter="14">
        <el-col :span="6"><div class="sum-label">部门人数</div><div class="sum-val">{{ summary.member_count }} 人</div></el-col>
        <el-col :span="6"><div class="sum-label">目标合计</div><div class="sum-val">¥{{ wan(summary.total_target) }}</div></el-col>
        <el-col :span="6"><div class="sum-label">已达成</div><div class="sum-val" style="color:#d93026">¥{{ wan(summary.total_achieved) }}</div></el-col>
        <el-col :span="6">
          <div class="sum-label">整体达成率</div>
          <el-progress type="dashboard" :width="70" :percentage="clamp(summary.completion)"
                       :color="progressColor(summary.completion)" />
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="tbl-card">
      <div class="card-title">
        成员业绩目标
        <el-button size="small" type="primary" plain :icon="Edit" style="float:right" @click="batchVisible = true">批量设目标</el-button>
      </div>
      <el-table :data="members" size="small" stripe max-height="520">
        <el-table-column prop="rank" label="排名" width="64" align="center" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="team" label="小组" width="100" />
        <el-table-column prop="role" label="角色" width="96" />
        <el-table-column label="月度目标(¥)" width="150">
          <template #default="{row}">
            <span class="target-val">¥{{ fmt(row.target) }}</span>
            <el-button link type="primary" size="small" @click="openSet(row)">设</el-button>
          </template>
        </el-table-column>
        <el-table-column :label="metricLabel" min-width="140">
          <template #default="{row}">¥{{ fmt(row.achieved) }}</template>
        </el-table-column>
        <el-table-column label="达成进度" min-width="200">
          <template #default="{row}">
            <el-progress :percentage="clamp(row.completion)" :color="progressColor(row.completion)" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{row}">
            <el-tag size="small" :type="row.completion >= 100 ? 'success' : (row.completion >= 60 ? 'warning' : 'danger')">
              {{ row.completion >= 100 ? '已达标' : (row.completion >= 60 ? '进行中' : '滞后') }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 设定目标弹窗 -->
    <el-dialog v-model="setVisible" title="设定月度业绩目标" width="420px">
      <div v-if="cur" class="dlg-body">
        <p>成员：<b>{{ cur.name }}</b>（{{ cur.team }}）</p>
        <el-input-number v-model="targetInput" :min="0" :step="1000" :precision="0"
                         controls-position="right" style="width:100%" />
        <div class="dlg-hint">单位：元。保存后计入该成员当月业绩目标。</div>
      </div>
      <template #footer>
        <el-button @click="setVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveTarget">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量设目标 -->
    <el-dialog v-model="batchVisible" title="批量设定部门目标" width="420px">
      <el-input-number v-model="batchTarget" :min="0" :step="1000" :precision="0"
                       controls-position="right" style="width:100%" />
      <div class="dlg-hint">将按相同金额设定部门全部成员（{{ members.length }} 人）的月度业绩目标。</div>
      <template #footer>
        <el-button @click="batchVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBatch">批量保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit } from '@element-plus/icons-vue'
import { dashApi, orgApi } from '@/api'
import dayjs from 'dayjs'

const props = defineProps({
  code: { type: String, required: true },
  title: { type: String, default: '部门业绩目标' }
})

const month = ref(dayjs().format('YYYY-MM'))
const loading = ref(false)
const members = ref([])
const summary = ref(null)
// 指标名兜底：若为全大写英文码（如 DEAL_AMOUNT）则统一显示为「业绩目标」，避免表头出现英文；已是中文则原样展示
const metricLabel = computed(() => {
  const m = members.value[0]?.metric
  if (!m) return '本月业绩(¥)'
  const cleaned = typeof m === 'string' && /^[A-Z_]+$/.test(m) ? '业绩目标' : m
  return cleaned + '(¥)'
})

const fmt = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 0 }))
const wan = (n) => (n >= 10000 ? (n / 10000).toFixed(1) + '万' : fmt(n))
const clamp = (v) => Math.max(0, Math.min(100, Number(v) || 0))
const progressColor = (v) => (v >= 100 ? '#0f9960' : (v >= 60 ? '#d9822b' : '#d93026'))

const setVisible = ref(false)
const batchVisible = ref(false)
const cur = ref(null)
const targetInput = ref(0)
const batchTarget = ref(0)
const saving = ref(false)

const openSet = (row) => { cur.value = row; targetInput.value = row.target || 0; setVisible.value = true }

const saveTarget = async () => {
  if (!cur.value) return
  saving.value = true
  try {
    await orgApi.updateUser(cur.value.user_id, { month_target: targetInput.value })
    ElMessage.success('目标已保存'); setVisible.value = false; await load()
  } catch (e) {} finally { saving.value = false }
}
const saveBatch = async () => {
  saving.value = true
  try {
    await Promise.all(members.value.map(m => orgApi.updateUser(m.user_id, { month_target: batchTarget.value })))
    ElMessage.success('已批量保存'); batchVisible.value = false; await load()
  } catch (e) {} finally { saving.value = false }
}

const load = async () => {
  loading.value = true
  try {
    const r = await dashApi.departmentMembers(props.code, { month: month.value })
    members.value = r.data || []
    summary.value = r.summary || null
  } catch (e) {} finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.sum-card, .tbl-card { border-radius: 10px; border: 1px solid var(--border); margin-bottom: 14px; }
.sum-label { font-size: 12px; color: var(--text-sub); }
.sum-val { font-size: 20px; font-weight: 700; margin-top: 4px; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
.target-val { font-weight: 600; }
.dlg-hint { font-size: 12px; color: #909399; margin-top: 10px; }
</style>
