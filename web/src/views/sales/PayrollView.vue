<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">薪酬绩效</h2>
      <span class="page-tip">工资自动核算 + 绩效薪酬看板，合并为统一入口｜底薪 3500（已含全勤）｜提成阶梯：业绩&lt;1万 10% · 1~1.75万 15% · 1.75~2.5万 20% · ≥2.5万 25%</span>
    </div>

    <el-tabs v-model="activeTab" class="payroll-tabs">
      <!-- Tab 1：工资核算 -->
      <el-tab-pane label="工资核算" name="calc">
        <el-row :gutter="16">
          <el-col :span="10">
            <el-card shadow="never" class="form-card">
              <div class="card-title">录入核算条件</div>
              <el-form label-width="92px" label-position="right">
                <el-form-item label="核算员工" required>
                  <el-select v-model="calc.user_id" filterable placeholder="选择员工" style="width:100%"
                             :loading="calcUserLoading" @change="onUserChange">
                    <el-option v-for="u in calcUsers" :key="u.id" :label="`${u.name || u.username}（${u.dept_name || '未分部门'}）`" :value="u.id" />
                  </el-select>
                </el-form-item>
                <el-form-item label="核算月份" required>
                  <el-date-picker v-model="calc.month" type="month" value-format="YYYY-MM"
                                  placeholder="选择月份" style="width:100%" />
                </el-form-item>
                <el-form-item label="本月业绩" required>
                  <el-input-number v-model="calc.performance" :min="0" :step="1000" :controls="true"
                                  controls-position="right" style="width:100%" placeholder="签单业绩(元)" />
                </el-form-item>
                <el-form-item label="奖金">
                  <el-input-number v-model="calc.bonus" :min="0" :step="100" :precision="2"
                                  controls-position="right" style="width:100%" placeholder="达标奖/其他奖金(元)" />
                </el-form-item>
                <el-form-item label="扣款">
                  <el-input-number v-model="calc.deduction" :min="0" :step="100" :precision="2"
                                  controls-position="right" style="width:100%" placeholder="迟到/请假/社保等(元)" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :icon="Operation" :loading="calcLoading" @click="doCalc">核算工资</el-button>
                  <el-button :icon="RefreshLeft" @click="resetCalc">重置</el-button>
                </el-form-item>
              </el-form>
              <el-alert v-if="calcHint" :title="calcHint" type="info" :closable="false" show-icon style="margin-top:4px" />
            </el-card>
          </el-col>

          <el-col :span="14">
            <el-card shadow="never" class="result-card" v-loading="calcLoading">
              <div class="card-title">核算结果
                <span v-if="calcResult" class="card-tip">{{ calcResult.month }} · {{ calcResult.user_name }}</span>
              </div>
              <el-empty v-if="!calcResult" description="请先在左侧录入条件并点击「核算工资」" :image-size="90" />
              <div v-else>
                <el-descriptions :column="2" border size="default" class="salary-desc">
                  <el-descriptions-item label="底薪">{{ fmt(calcResult.base_salary) }} 元</el-descriptions-item>
                  <el-descriptions-item label="本月业绩">{{ fmt(calcResult.performance) }} 元</el-descriptions-item>
                  <el-descriptions-item label="适用提成规则">
                    <el-tag size="small" type="success">{{ calcResult.commission_rule || '未匹配规则' }}</el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="提成金额">
                    <span class="pos">+ {{ fmt(calcResult.commission) }} 元</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="奖金">
                    <span class="pos">+ {{ fmt(calcResult.bonus) }} 元</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="扣款">
                    <span class="neg">− {{ fmt(calcResult.deduction) }} 元</span>
                  </el-descriptions-item>
                </el-descriptions>
                <div class="total-box">
                  <span class="total-label">实发工资</span>
                  <span class="total-value">{{ fmt(calcResult.total) }} <i>元</i></span>
                </div>
                <div class="result-actions">
                  <el-button type="success" :icon="Check" :loading="saveLoading" @click="saveRecord">保存核算结果</el-button>
                  <span class="save-tip" v-if="savedAt">已于 {{ savedAt }} 保存</span>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

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
      </el-tab-pane>

      <!-- Tab 2：绩效薪酬 -->
      <el-tab-pane label="绩效薪酬" name="perf">
        <div class="card">
          <div class="card-title">个人业绩与预估提成
            <span class="card-tip">提成按「{{ perfRuleName }}」规则前端测算，仅供参考</span>
          </div>
          <div class="table-wrap">
            <el-table :data="perfItems" size="small" stripe max-height="420" empty-text="本月暂无业绩数据">
              <el-table-column prop="name" label="姓名" width="110" />
              <el-table-column label="业绩" width="130" align="right"><template #default="{row}">¥{{ fmt(row.amount) }}</template></el-table-column>
              <el-table-column label="目标" width="130" align="right"><template #default="{row}">¥{{ fmt(row.target) }}</template></el-table-column>
              <el-table-column label="完成率" min-width="170">
                <template #default="{row}">
                  <el-progress :percentage="Math.min(row.rate || 0, 100)"
                               :status="row.rate >= 100 ? 'success' : (row.rate >= 60 ? '' : 'exception')"
                               :text-inside="true" :stroke-width="16" />
                </template>
              </el-table-column>
              <el-table-column prop="order_count" label="订单数" width="90" align="center" />
              <el-table-column label="预估提成" width="130" align="right"><template #default="{row}"><span class="comm">¥{{ fmt(estComm(row.amount)) }}</span></template></el-table-column>
            </el-table>
          </div>
        </div>

        <div class="card">
          <div class="card-title">提成规则</div>
          <div class="table-wrap">
            <el-table :data="perfRules" size="small" stripe empty-text="暂无提成规则">
              <el-table-column prop="name" label="规则名称" width="160" />
              <el-table-column prop="rule_type_name" label="类型" width="110">
                <template #default="{row}"><el-tag size="small" :type="row.rule_type==='LADDER'?'warning':(row.rule_type==='RATE'?'success':'info')">{{ row.rule_type_name }}</el-tag></template>
              </el-table-column>
              <el-table-column prop="department_name" label="适用部门" width="110" />
              <el-table-column label="比例 / 固定" width="130">
                <template #default="{row}">
                  <span v-if="row.rule_type==='FIXED'">¥{{ fmt(row.fixed_amount) }}/单</span>
                  <span v-else>{{ row.rate }}%</span>
                </template>
              </el-table-column>
              <el-table-column label="阶梯配置" min-width="280">
                <template #default="{row}">
                  <span v-if="row.rule_type==='LADDER' && row.ladder && row.ladder.length">
                    <el-tag v-for="(t,i) in row.ladder" :key="i" size="small" effect="plain" class="ladder-tag">{{ fmt(t.min) }}~{{ t.max>=1000000?'∞':fmt(t.max) }}：{{ t.rate }}%</el-tag>
                  </span>
                  <span v-else class="text-muted">—</span>
                </template>
              </el-table-column>
              <el-table-column prop="effective_month" label="生效月" width="110" />
            </el-table>
          </div>
        </div>

        <div class="card">
          <div class="card-title">完成率排行</div>
          <div class="table-wrap">
            <el-table :data="rankItems" size="small" stripe max-height="420" empty-text="暂无排行数据">
              <el-table-column label="排名" width="70" align="center">
                <template #default="{row}">
                  <el-tag v-if="row.rank === 1" type="danger" size="small">第1名</el-tag>
                  <el-tag v-else-if="row.rank === 2" type="warning" size="small">第2名</el-tag>
                  <el-tag v-else-if="row.rank === 3" type="success" size="small">第3名</el-tag>
                  <span v-else>{{ row.rank }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="name" label="姓名" width="100" />
              <el-table-column prop="department_name" label="部门" width="100" />
              <el-table-column prop="team_name" label="小组" width="110" />
              <el-table-column prop="amount" label="业绩" width="120" align="right"><template #default="{row}">¥{{ fmt(row.amount) }}</template></el-table-column>
              <el-table-column prop="target" label="目标" width="120" align="right"><template #default="{row}">¥{{ fmt(row.target) }}</template></el-table-column>
              <el-table-column label="完成率" min-width="160">
                <template #default="{row}">
                  <el-progress :percentage="Math.min(row.rate || 0, 100)"
                               :status="row.rate >= 100 ? 'success' : (row.rate >= 60 ? '' : 'exception')"
                               :text-inside="true" :stroke-width="16" />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Operation, RefreshLeft, Check, Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { salesApi, orgApi } from '@/api'

const activeTab = ref('calc')

/* ---------- 工资核算 ---------- */
const calcUsers = ref([])
const calcUserLoading = ref(false)
const calcLoading = ref(false)
const saveLoading = ref(false)
const calcResult = ref(null)
const savedAt = ref('')
const calcHint = ref('')
const history = ref([])

const calc = reactive({
  user_id: null,
  month: dayjs().format('YYYY-MM'),
  performance: 0,
  bonus: 0,
  deduction: 0
})

const loadCalcUsers = async () => {
  calcUserLoading.value = true
  try {
    const r = await orgApi.users({ page_size: 200 })
    const list = r.results || r.data || []
    calcUsers.value = list.filter(u => !['RESIGNED'].includes(u.status))
  } finally { calcUserLoading.value = false }
}
const onUserChange = (id) => {
  const u = calcUsers.value.find(x => x.id === id)
  calcHint.value = u && u.base_salary ? `该员工底薪设置：${fmt(u.base_salary)} 元/月（核算时自动带入）` : '该员工未设置底薪，请在「系统管理→员工管理」填写底薪'
}
const doCalc = async () => {
  if (!calc.user_id) return ElMessage.warning('请先选择核算员工')
  if (!calc.month) return ElMessage.warning('请选择核算月份')
  calcLoading.value = true
  try {
    const r = await salesApi.salaryCalc({
      user_id: calc.user_id, month: calc.month,
      performance: calc.performance, bonus: calc.bonus, deduction: calc.deduction
    })
    if (r.code === 0) { calcResult.value = r.data; savedAt.value = '' }
    else ElMessage.error(r.msg || '核算失败')
  } finally { calcLoading.value = false }
}
const saveRecord = async () => {
  if (!calcResult.value) return
  saveLoading.value = true
  try {
    const d = calcResult.value
    await salesApi.salarySave({
      user: d.user_id, month: d.month, base_salary: d.base_salary,
      performance: d.performance, commission: d.commission, commission_rule: d.commission_rule,
      bonus: d.bonus, deduction: d.deduction
    })
    ElMessage.success('已保存核算结果')
    savedAt.value = dayjs().format('YYYY-MM-DD HH:mm')
    loadHistory()
  } catch (e) { ElMessage.error('保存失败') }
  finally { saveLoading.value = false }
}
const loadHistory = async () => {
  try { const r = await salesApi.salaryList({ page_size: 50 }); history.value = r.results || r.data || [] } catch (e) {}
}
const resetCalc = () => {
  calc.user_id = null; calc.month = dayjs().format('YYYY-MM')
  calc.performance = 0; calc.bonus = 0; calc.deduction = 0
  calcResult.value = null; calcHint.value = ''; savedAt.value = ''
}

/* ---------- 绩效薪酬 ---------- */
const perfMonth = ref(dayjs().format('YYYY-MM'))
const perf = reactive({ total: {}, items: [] })
const rankItems = ref([])
const perfRules = ref([])

const perfRuleName = computed(() => perfRules.value[0]?.name || '未配置')
const perfItems = computed(() => perf.items || [])
const estComm = (amount) => {
  const rule = perfRules.value[0]
  if (!rule) return 0
  amount = Number(amount) || 0
  if (rule.rule_type === 'RATE') return amount * (Number(rule.rate) || 0) / 100
  if (rule.rule_type === 'FIXED') return Number(rule.fixed_amount) || 0
  if (rule.rule_type === 'LADDER') {
    let comm = 0
    for (const t of (rule.ladder || [])) {
      const min = Number(t.min) || 0, max = Number(t.max) || 0, rate = Number(t.rate) || 0
      const overlap = Math.min(amount, max) - min
      if (overlap > 0) comm += overlap * rate / 100
    }
    return Math.max(Math.round(comm), 0)
  }
  return 0
}
const loadPerf = async () => {
  const [p, r, c] = await Promise.all([
    salesApi.performance({ month: perfMonth.value }),
    salesApi.rank({ month: perfMonth.value }),
    salesApi.commissionRules()
  ])
  perf.total = p.total || {}; perf.items = p.items || []
  rankItems.value = r.items || []; perfRules.value = c.results || c.data || []
}

/* ---------- 公共 ---------- */
const fmt = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))

onMounted(() => { loadCalcUsers(); loadHistory(); loadPerf() })
</script>

<style scoped>
.page-tip { font-size: 12px; color: var(--text-sub); margin-left: 10px; font-weight: 400; }
.payroll-tabs :deep(.el-tabs__header) { margin-bottom: 18px; }
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
.card { background: var(--card, #fff); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.comm { color: var(--success); font-weight: 700; }
.ladder-tag { margin: 0 6px 4px 0; }
</style>
