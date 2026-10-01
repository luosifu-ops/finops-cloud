<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">工资自动核算</h2>
      <span class="page-tip">自动核算「底薪 + 提成 + 奖金 − 扣款 = 实发工资」｜底薪 3500（已含全勤）｜提成阶梯：业绩&lt;1万 10% · 1~1.75万 15% · 1.75~2.5万 20% · ≥2.5万 25%</span>
    </div>

    <el-row :gutter="16">
      <!-- 左侧：录入 -->
      <el-col :span="10">
        <el-card shadow="never" class="form-card">
          <div class="card-title">录入核算条件</div>
          <el-form label-width="92px" label-position="right">
            <el-form-item label="核算员工" required>
              <el-select v-model="form.user_id" filterable placeholder="选择员工" style="width:100%"
                         :loading="userLoading" @change="onUserChange">
                <el-option v-for="u in users" :key="u.id" :label="`${u.name || u.username}（${u.dept_name || '未分部门'}）`" :value="u.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="核算月份" required>
              <el-date-picker v-model="form.month" type="month" value-format="YYYY-MM"
                              placeholder="选择月份" style="width:100%" />
            </el-form-item>
            <el-form-item label="本月业绩" required>
              <el-input-number v-model="form.performance" :min="0" :step="1000" :controls="true"
                              controls-position="right" style="width:100%" placeholder="签单业绩(元)" />
            </el-form-item>
            <el-form-item label="奖金">
              <el-input-number v-model="form.bonus" :min="0" :step="100" :precision="2"
                              controls-position="right" style="width:100%" placeholder="达标奖/其他奖金(元)" />
            </el-form-item>
            <el-form-item label="扣款">
              <el-input-number v-model="form.deduction" :min="0" :step="100" :precision="2"
                              controls-position="right" style="width:100%" placeholder="迟到/请假/社保等(元)" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Operation" :loading="calcLoading" @click="doCalc">核算工资</el-button>
              <el-button :icon="RefreshLeft" @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
          <el-alert v-if="baseHint" :title="baseHint" type="info" :closable="false" show-icon style="margin-top:4px" />
        </el-card>
      </el-col>

      <!-- 右侧：结果 -->
      <el-col :span="14">
        <el-card shadow="never" class="result-card" v-loading="calcLoading">
          <div class="card-title">核算结果
            <span v-if="result" class="card-tip">{{ result.month }} · {{ result.user_name }}</span>
          </div>

          <el-empty v-if="!result" description="请先在左侧录入条件并点击「核算工资」" :image-size="90" />

          <div v-else>
            <el-descriptions :column="2" border size="default" class="salary-desc">
              <el-descriptions-item label="底薪">{{ fmt(result.base_salary) }} 元</el-descriptions-item>
              <el-descriptions-item label="本月业绩">{{ fmt(result.performance) }} 元</el-descriptions-item>
              <el-descriptions-item label="适用提成规则">
                <el-tag size="small" type="success">{{ result.commission_rule || '未匹配规则' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="提成金额">
                <span class="pos">+ {{ fmt(result.commission) }} 元</span>
              </el-descriptions-item>
              <el-descriptions-item label="奖金">
                <span class="pos">+ {{ fmt(result.bonus) }} 元</span>
              </el-descriptions-item>
              <el-descriptions-item label="扣款">
                <span class="neg">− {{ fmt(result.deduction) }} 元</span>
              </el-descriptions-item>
            </el-descriptions>

            <div class="total-box">
              <span class="total-label">实发工资</span>
              <span class="total-value">{{ fmt(result.total) }} <i>元</i></span>
            </div>

            <div class="result-actions">
              <el-button type="success" :icon="Check" :loading="saveLoading" @click="saveRecord">保存核算结果</el-button>
              <span class="save-tip" v-if="savedAt">已于 {{ savedAt }} 保存</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 历史核算记录 -->
    <el-card shadow="never" class="history-card" style="margin-top:16px">
      <div class="card-title">历史核算记录
        <el-button text size="small" :icon="Refresh" @click="loadHistory" style="float:right">刷新</el-button>
      </div>
      <el-table :data="history" size="small" stripe max-height="320" empty-text="暂无记录">
        <el-table-column prop="user_name" label="员工" width="120" />
        <el-table-column prop="month" label="月份" width="100" />
        <el-table-column label="底薪" width="110" align="right"><template #default="{row}">{{ fmt(row.base_salary) }}</template></el-table-column>
        <el-table-column label="业绩" width="110" align="right"><template #default="{row}">{{ fmt(row.performance) }}</template></el-table-column>
        <el-table-column label="提成" width="110" align="right"><template #default="{row}">{{ fmt(row.commission) }}</template></el-table-column>
        <el-table-column label="奖金" width="90" align="right"><template #default="{row}">{{ fmt(row.bonus) }}</template></el-table-column>
        <el-table-column label="扣款" width="90" align="right"><template #default="{row}">{{ fmt(row.deduction) }}</template></el-table-column>
        <el-table-column label="实发" width="120" align="right"><template #default="{row}"><b>{{ fmt(row.total) }}</b></template></el-table-column>
        <el-table-column label="发放" width="80" align="center">
          <template #default="{row}"><el-tag size="small" :type="row.settled?'success':'info'">{{ row.settled?'已发':'未发' }}</el-tag></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Operation, RefreshLeft, Check, Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { salesApi, orgApi } from '@/api'

const users = ref([])
const userLoading = ref(false)
const calcLoading = ref(false)
const saveLoading = ref(false)
const result = ref(null)
const savedAt = ref('')
const baseHint = ref('')
const history = ref([])

const form = reactive({
  user_id: null,
  month: dayjs().format('YYYY-MM'),
  performance: 0,
  bonus: 0,
  deduction: 0
})

const fmt = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))

const loadUsers = async () => {
  userLoading.value = true
  try {
    const r = await orgApi.users({ page_size: 200 })
    const list = r.results || r.data || []
    users.value = list.filter(u => !['RESIGNED'].includes(u.status))
  } finally { userLoading.value = false }
}

const onUserChange = (id) => {
  const u = users.value.find(x => x.id === id)
  baseHint.value = u && u.base_salary ? `该员工底薪设置：${fmt(u.base_salary)} 元/月（核算时自动带入）` : '该员工未设置底薪，请在「系统管理→员工管理」填写底薪'
}

const doCalc = async () => {
  if (!form.user_id) return ElMessage.warning('请先选择核算员工')
  if (!form.month) return ElMessage.warning('请选择核算月份')
  calcLoading.value = true
  try {
    const r = await salesApi.salaryCalc({
      user_id: form.user_id,
      month: form.month,
      performance: form.performance,
      bonus: form.bonus,
      deduction: form.deduction
    })
    if (r.code === 0) {
      result.value = r.data
      savedAt.value = ''
    } else {
      ElMessage.error(r.msg || '核算失败')
    }
  } finally { calcLoading.value = false }
}

const saveRecord = async () => {
  if (!result.value) return
  saveLoading.value = true
  try {
    const d = result.value
    await salesApi.salarySave({
      user: d.user_id,
      month: d.month,
      base_salary: d.base_salary,
      performance: d.performance,
      commission: d.commission,
      commission_rule: d.commission_rule,
      bonus: d.bonus,
      deduction: d.deduction
    })
    ElMessage.success('已保存核算结果')
    savedAt.value = dayjs().format('YYYY-MM-DD HH:mm')
    loadHistory()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally { saveLoading.value = false }
}

const loadHistory = async () => {
  try {
    const r = await salesApi.salaryList({ page_size: 50 })
    history.value = r.results || r.data || []
  } catch (e) {}
}

const resetForm = () => {
  form.user_id = null
  form.month = dayjs().format('YYYY-MM')
  form.performance = 0
  form.bonus = 0
  form.deduction = 0
  result.value = null
  baseHint.value = ''
  savedAt.value = ''
}

onMounted(() => { loadUsers(); loadHistory() })
</script>

<style scoped>
.page-tip { font-size: 12px; color: var(--text-sub); margin-left: 10px; font-weight: 400; }
.form-card, .result-card { border-radius: 10px; border: 1px solid var(--border); min-height: 360px; }
.card-title { font-weight: 700; margin-bottom: 14px; font-size: 15px; }
.card-tip { font-size: 12px; font-weight: 400; color: var(--text-sub); margin-left: 8px; }
.salary-desc { margin-bottom: 16px; }
.pos { color: var(--success); font-weight: 600; }
.neg { color: var(--danger, #d93026); font-weight: 600; }
.total-box { display: flex; align-items: baseline; justify-content: flex-end; gap: 14px; padding: 14px 8px; border-top: 1px dashed var(--border); }
.total-label { color: var(--text-sub); font-size: 14px; }
.total-value { color: #d93026; font-size: 30px; font-weight: 800; }
.total-value i { font-size: 14px; font-style: normal; font-weight: 500; }
.result-actions { margin-top: 8px; text-align: right; }
.save-tip { font-size: 12px; color: var(--success); margin-left: 10px; }
</style>
