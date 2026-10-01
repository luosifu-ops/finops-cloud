<template>
  <div class="page" v-loading="loading">
    <!-- 全员管理模式 -->
    <template v-if="canManage">
      <div class="page-header">
        <h2 class="page-title">薪酬绩效</h2>
        <div class="header-tools">
          <el-button type="warning" :icon="MagicStick" :loading="batchLoading" @click="batchCalc">全员批量核算</el-button>
          <el-button :icon="Download" @click="exportCsv">导出 CSV</el-button>
          <el-button type="primary" :icon="Coin" @click="openCalc">单人员工核算</el-button>
        </div>
      </div>

      <!-- 筛选 -->
      <el-card shadow="never" class="filter-card">
        <el-form :inline="true" @submit.prevent>
          <el-form-item label="核算月份">
            <el-date-picker v-model="filter.month" type="month" value-format="YYYY-MM" style="width:150px" @change="reload" />
          </el-form-item>
          <el-form-item label="部门">
            <el-select v-model="filter.department" placeholder="全公司" clearable style="width:160px" @change="reload">
              <el-option label="全公司" value="" />
              <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="员工">
            <el-input v-model="filter.keyword" placeholder="姓名/工号" clearable style="width:150px" @keyup.enter="reload" @clear="reload" />
          </el-form-item>
          <el-form-item label="发放状态">
            <el-select v-model="filter.settled" placeholder="全部" clearable style="width:120px" @change="reload">
              <el-option label="已发放" :value="true" />
              <el-option label="未发放" :value="false" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="reload">查询</el-button>
            <el-button @click="resetFilter">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 统计卡片 -->
      <el-row :gutter="14" class="stat-row">
        <el-col :span="6" v-for="c in summaryCards" :key="c.label">
          <el-card shadow="never" class="stat-card">
            <div class="label">{{ c.label }}</div>
            <div class="value" :style="{ color: c.color }">{{ c.value }}</div>
            <div class="sub">{{ c.sub }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 部门分布 -->
      <el-card shadow="never" class="block-card">
        <div class="card-title">部门分布</div>
        <el-table :data="deptDist" size="small" stripe max-height="260" empty-text="暂无数据">
          <el-table-column prop="name" label="部门" min-width="140" />
          <el-table-column prop="headcount" label="核算人数" width="110" align="center" />
          <el-table-column label="应发总额" align="right" min-width="140">
            <template #default="{row}">{{ fmtMoney(row.total) }}</template>
          </el-table-column>
          <el-table-column label="人均工资" align="right" min-width="140">
            <template #default="{row}">{{ fmtMoney(row.avg) }}</template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 工资列表 -->
      <el-card shadow="never" class="block-card">
        <div class="card-title">工资明细</div>
        <el-table :data="list" size="small" stripe max-height="420" empty-text="暂无工资记录">
          <el-table-column prop="user_name" label="员工" width="110" />
          <el-table-column prop="department_name" label="部门" width="120" />
          <el-table-column label="岗位" width="110"><template #default="{row}">{{ row.position_name || row.position || '—' }}</template></el-table-column>
          <el-table-column label="底薪" align="right" width="110"><template #default="{row}">{{ fmtMoney(row.base_salary) }}</template></el-table-column>
          <el-table-column label="业绩" align="right" width="110"><template #default="{row}">{{ fmtMoney(row.performance) }}</template></el-table-column>
          <el-table-column label="提成" align="right" width="110"><template #default="{row}">{{ fmtMoney(row.commission) }}</template></el-table-column>
          <el-table-column label="奖金" align="right" width="100"><template #default="{row}">{{ fmtMoney(row.bonus) }}</template></el-table-column>
          <el-table-column label="扣款" align="right" width="100"><template #default="{row}">{{ fmtMoney(row.deduction) }}</template></el-table-column>
          <el-table-column label="实发工资" align="right" width="130"><template #default="{row}"><b>{{ fmtMoney(row.total) }}</b></template></el-table-column>
          <el-table-column prop="commission_rule" label="提成规则" width="140" show-overflow-tooltip />
          <el-table-column prop="month" label="月份" width="100" />
          <el-table-column label="发放" width="80" align="center">
            <template #default="{row}"><el-tag size="small" :type="row.settled?'success':'info'">{{ row.settled?'已发':'未发' }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{row}">
              <el-button link type="primary" :icon="Edit" @click="openAdjust(row)">调整</el-button>
              <el-button link type="success" :disabled="row.settled" @click="markPaid(row)">标记发放</el-button>
              <el-button link type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager" v-if="total > pageSize">
          <el-pagination background layout="total, prev, pager, next" :total="total" :page-size="pageSize" :current-page="page" @current-change="onPage" />
        </div>
      </el-card>
    </template>

    <!-- 员工本人视角 -->
    <template v-else>
      <div class="page-header">
        <h2 class="page-title">我的工资条</h2>
        <el-date-picker v-model="selfMonth" type="month" value-format="YYYY-MM" style="width:150px" @change="loadSelf" />
      </div>
      <el-card shadow="never" class="block-card" v-loading="loading">
        <el-empty v-if="!selfSalary" description="该月暂无工资条" />
        <div v-else>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="员工">{{ selfSalary.user_name }}</el-descriptions-item>
            <el-descriptions-item label="核算月份">{{ selfSalary.month }}</el-descriptions-item>
            <el-descriptions-item label="底薪">{{ fmtMoney(selfSalary.base_salary) }}</el-descriptions-item>
            <el-descriptions-item label="本月业绩">{{ fmtMoney(selfSalary.performance) }}</el-descriptions-item>
            <el-descriptions-item label="适用提成规则"><el-tag size="small" type="success">{{ selfSalary.commission_rule || '未匹配' }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="提成">{{ fmtMoney(selfSalary.commission) }}</el-descriptions-item>
            <el-descriptions-item label="奖金">{{ fmtMoney(selfSalary.bonus) }}</el-descriptions-item>
            <el-descriptions-item label="扣款">{{ fmtMoney(selfSalary.deduction) }}</el-descriptions-item>
            <el-descriptions-item label="发放状态"><el-tag size="small" :type="selfSalary.settled?'success':'info'">{{ selfSalary.settled?'已发放':'未发放' }}</el-tag></el-descriptions-item>
          </el-descriptions>
          <div class="self-total">
            <span>实发工资</span><b>{{ fmtMoney(selfSalary.total) }}</b>
          </div>
        </div>
      </el-card>
    </template>

    <!-- 单人核算弹窗 -->
    <el-dialog v-model="calcVisible" title="员工工资核算" width="560px" @closed="closeCalc">
      <el-form label-width="96px" v-if="!calcResult">
        <el-form-item label="核算员工" required>
          <el-select v-model="calcForm.user_id" filterable placeholder="选择员工" style="width:100%" :loading="userLoading" @change="onUserChange">
            <el-option v-for="u in calcUsers" :key="u.id" :label="`${u.name || u.username}（${u.dept_name || '未分部门'}）`" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="核算月份" required>
          <el-date-picker v-model="calcForm.month" type="month" value-format="YYYY-MM" style="width:100%" />
        </el-form-item>
        <el-alert v-if="calcHint" :title="calcHint" type="info" :closable="false" show-icon />
      </el-form>
      <div v-else v-loading="calcLoading">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="员工">{{ calcResult.user_name }}</el-descriptions-item>
          <el-descriptions-item label="月份">{{ calcResult.month }}</el-descriptions-item>
          <el-descriptions-item label="底薪">{{ fmtMoney(calcResult.base_salary) }}</el-descriptions-item>
          <el-descriptions-item label="本月业绩">{{ fmtMoney(calcResult.performance) }}</el-descriptions-item>
          <el-descriptions-item label="提成规则"><el-tag size="small" type="success">{{ calcResult.commission_rule || '未匹配' }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="提成金额"><span class="pos">+ {{ fmtMoney(calcResult.commission) }}</span></el-descriptions-item>
        </el-descriptions>
        <el-form label-width="96px" style="margin-top:14px">
          <el-form-item label="奖金"><el-input-number v-model="calcResult.bonus" :min="0" :precision="2" :step="100" style="width:100%" /></el-form-item>
          <el-form-item label="扣款"><el-input-number v-model="calcResult.deduction" :min="0" :precision="2" :step="100" style="width:100%" /></el-form-item>
          <el-form-item label="备注"><el-input v-model="calcResult.remark" placeholder="手工调整备注" /></el-form-item>
        </el-form>
        <div class="self-total"><span>实发工资</span><b>{{ fmtMoney(adjustedTotal) }}</b></div>
      </div>
      <template #footer>
        <template v-if="!calcResult">
          <el-button @click="calcVisible=false">取消</el-button>
          <el-button type="primary" :loading="calcLoading" @click="doCalc">开始核算</el-button>
        </template>
        <template v-else>
          <el-button @click="calcResult=null">重新核算</el-button>
          <el-button type="success" :loading="saveLoading" @click="saveCalc">确认保存</el-button>
        </template>
      </template>
    </el-dialog>

    <!-- 调整弹窗 -->
    <el-dialog v-model="adjustVisible" title="工资调整" width="520px">
      <el-descriptions :column="2" border size="small" v-if="editing">
        <el-descriptions-item label="员工">{{ editing.user_name }}</el-descriptions-item>
        <el-descriptions-item label="月份">{{ editing.month }}</el-descriptions-item>
      </el-descriptions>
      <el-form label-width="96px" style="margin-top:14px" v-if="editing">
        <el-form-item label="奖金"><el-input-number v-model="editing.bonus" :min="0" :precision="2" :step="100" style="width:100%" /></el-form-item>
        <el-form-item label="扣款"><el-input-number v-model="editing.deduction" :min="0" :precision="2" :step="100" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="editing.remark" placeholder="调整备注" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustVisible=false">取消</el-button>
        <el-button type="primary" :loading="saveLoading" @click="saveAdjust">保存调整</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Coin, MagicStick, Download, Edit, Delete } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { hrApi, orgApi } from '@/api'
import { useUserStore } from '@/store/user'

const store = useUserStore()
const canManage = computed(() => store.isHR || store.isBoss)

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const departments = ref([])
const summary = ref(null)
const filter = reactive({ month: dayjs().format('YYYY-MM'), department: '', keyword: '', settled: '' })

const summaryCards = computed(() => {
  const s = summary.value || {}
  return [
    { label: '核算人数', value: s.headcount ?? '—', sub: filter.month, color: '#1f2329' },
    { label: '应发总额', value: fmtMoney(s.total_amount), sub: '底薪+提成+奖金-扣款', color: '#d93026' },
    { label: '提成总额', value: fmtMoney(s.total_commission), sub: '本月提成合计', color: '#0f9960' },
    { label: '人均工资', value: fmtMoney(s.avg_amount), sub: '应发/人数', color: '#2f6fed' }
  ]
})
const deptDist = computed(() => summary.value?.departments || [])

/* ---------- 解析兼容 DRF / {code,data} / 裸数组 ---------- */
function parseList(resp) {
  if (!resp) return { list: [], total: 0 }
  let b = resp
  if (b && typeof b === 'object' && 'code' in b && 'data' in b) b = b.data
  if (b && b.results) return { list: b.results, total: b.count || b.results.length }
  if (Array.isArray(b)) return { list: b, total: b.length }
  if (b && typeof b === 'object') return { list: [b], total: 1 }
  return { list: [], total: 0 }
}
function parseObj(resp) {
  if (!resp) return null
  if (resp && typeof resp === 'object' && 'code' in resp && 'data' in resp) return resp.data
  return resp
}
const fmtMoney = (n) => (n === undefined || n === null ? '¥0.00' : '¥' + Number(n).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }))

const reload = async () => {
  loading.value = true
  page.value = 1
  await Promise.all([loadList(), loadSummary()])
  loading.value = false
}
const loadList = async () => {
  try {
    const p = { page: page.value, page_size: pageSize.value, month: filter.month }
    if (filter.department) p.department = filter.department
    if (filter.keyword) p.keyword = filter.keyword
    if (filter.settled !== '') p.settled = filter.settled
    const r = await hrApi.salaries(p)
    const { list: l, total: t } = parseList(r)
    list.value = l; total.value = t
  } catch (e) {}
}
const loadSummary = async () => {
  try { const r = await hrApi.salarySummary({ month: filter.month }); summary.value = parseObj(r) || null } catch (e) {}
}
const onPage = (p) => { page.value = p; loadList() }
const resetFilter = () => { filter.department = ''; filter.keyword = ''; filter.settled = ''; reload() }

/* ---------- 批量核算 ---------- */
const batchLoading = ref(false)
const batchCalc = async () => {
  try {
    await ElMessageBox.confirm(`确认对 ${filter.month} 公司全体在职员工进行薪酬批量核算？`, '批量核算', { type: 'warning' })
  } catch { return }
  batchLoading.value = true
  try {
    const r = await hrApi.salaryBatchCalc({ month: filter.month })
    const d = parseObj(r) || {}
    ElMessage.success(`批量核算完成，共 ${d.count ?? '?'} 条`)
    await reload()
  } catch (e) {} finally { batchLoading.value = false }
}

/* ---------- 单人核算 ---------- */
const calcVisible = ref(false)
const calcLoading = ref(false)
const saveLoading = ref(false)
const calcUsers = ref([])
const userLoading = ref(false)
const calcHint = ref('')
const calcResult = ref(null)
const calcForm = reactive({ user_id: null, month: dayjs().format('YYYY-MM') })

const loadCalcUsers = async () => {
  userLoading.value = true
  try {
    const r = await orgApi.users({ page_size: 300 })
    const { list: l } = parseList(r)
    calcUsers.value = l.filter(u => !['RESIGNED'].includes(u.status))
  } finally { userLoading.value = false }
}
const onUserChange = (id) => {
  const u = calcUsers.value.find(x => x.id === id)
  calcHint.value = u && u.base_salary ? `底薪 ${fmtMoney(u.base_salary)}，核算时自动带入` : '该员工未设底薪，请在「系统管理→员工管理」维护'
}
const openCalc = () => { calcVisible.value = true; calcResult.value = null; calcForm.user_id = null; calcForm.month = filter.month; loadCalcUsers() }
const closeCalc = () => { calcResult.value = null; calcHint.value = '' }
const doCalc = async () => {
  if (!calcForm.user_id) return ElMessage.warning('请选择核算员工')
  if (!calcForm.month) return ElMessage.warning('请选择核算月份')
  calcLoading.value = true
  try {
    const r = await hrApi.salaryCalc({ month: calcForm.month, user_id: calcForm.user_id })
    const d = parseObj(r)
    if (!d) return ElMessage.error('核算失败')
    calcResult.value = { user_id: calcForm.user_id, user_name: calcUsers.value.find(x => x.id === calcForm.user_id)?.name || '', month: calcForm.month, base_salary: 0, performance: 0, commission: 0, commission_rule: '', bonus: 0, deduction: 0, remark: '', ...d }
  } catch (e) {} finally { calcLoading.value = false }
}
const adjustedTotal = computed(() => {
  const c = calcResult.value
  if (!c) return '¥0.00'
  const t = Number(c.base_salary || 0) + Number(c.commission || 0) + Number(c.bonus || 0) - Number(c.deduction || 0)
  return fmtMoney(t)
})
const saveCalc = async () => {
  const c = calcResult.value
  if (!c) return
  saveLoading.value = true
  try {
    await hrApi.salarySave({
      user: c.user_id, month: c.month, base_salary: c.base_salary, performance: c.performance,
      commission: c.commission, commission_rule: c.commission_rule, bonus: c.bonus, deduction: c.deduction, remark: c.remark
    })
    ElMessage.success('已保存核算结果')
    calcVisible.value = false
    await reload()
  } catch (e) {} finally { saveLoading.value = false }
}

/* ---------- 调整 / 发放 / 删除 ---------- */
const adjustVisible = ref(false)
const editing = ref(null)
const openAdjust = (row) => { editing.value = { ...row, bonus: Number(row.bonus) || 0, deduction: Number(row.deduction) || 0 }; adjustVisible.value = true }
const saveAdjust = async () => {
  const e = editing.value
  saveLoading.value = true
  try {
    await hrApi.salaryUpdate(e.id, { bonus: e.bonus, deduction: e.deduction, remark: e.remark })
    ElMessage.success('已保存调整')
    adjustVisible.value = false
    await reload()
  } catch (err) {} finally { saveLoading.value = false }
}
const markPaid = async (row) => {
  try {
    await hrApi.salaryUpdate(row.id, { settled: true })
    ElMessage.success('已标记为已发放')
    await reload()
  } catch (e) {}
}
const remove = async (row) => {
  try { await ElMessageBox.confirm(`确认删除 ${row.user_name} ${row.month} 的工资记录？`, '删除', { type: 'warning' }) } catch { return }
  try { await hrApi.salaryDelete(row.id); ElMessage.success('已删除'); await reload() } catch (e) {}
}

/* ---------- 导出 CSV ---------- */
const exportCsv = () => {
  const headers = ['姓名', '部门', '岗位', '底薪', '业绩', '提成', '奖金', '扣款', '实发工资', '提成规则', '月份', '发放状态']
  const rows = list.value.map(r => [r.user_name, r.department_name, r.position_name, r.base_salary, r.performance, r.commission, r.bonus, r.deduction, r.total, r.commission_rule, r.month, r.settled ? '已发' : '未发'])
  const csv = [headers, ...rows].map(row => row.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `薪酬绩效-${filter.month}.csv`
  a.click()
  URL.revokeObjectURL(a.href)
}

/* ---------- 员工本人视角 ---------- */
const selfMonth = ref(dayjs().format('YYYY-MM'))
const selfSalary = ref(null)
const loadSelf = async () => {
  loading.value = true
  try { const r = await hrApi.mySalary({ month: selfMonth.value }); const { list: l } = parseList(r); selfSalary.value = l[0] || parseObj(r) || null } catch (e) {} finally { loading.value = false }
}
const loadDepartments = async () => {
  try { const r = await orgApi.departments({ page_size: 200 }); const { list: l } = parseList(r); departments.value = l } catch (e) {}
}

onMounted(async () => {
  if (canManage.value) { await loadDepartments(); await reload() }
  else await loadSelf()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 10px; }
.header-tools { display: flex; gap: 8px; }
.filter-card, .block-card, .stat-card { border-radius: 10px; border: 1px solid var(--border); margin-bottom: 14px; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
.stat-row { margin-bottom: 0; }
.stat-card .label { font-size: 13px; color: var(--text-sub); }
.stat-card .value { font-size: 24px; font-weight: 800; margin: 6px 0; }
.stat-card .sub { font-size: 12px; color: #909399; }
.pager { margin-top: 12px; display: flex; justify-content: flex-end; }
.pos { color: var(--success); font-weight: 600; }
.self-total { display: flex; align-items: baseline; justify-content: flex-end; gap: 14px; padding: 14px 8px; border-top: 1px dashed var(--border); margin-top: 12px; }
.self-total span { color: var(--text-sub); }
.self-total b { color: #d93026; font-size: 26px; }
</style>
