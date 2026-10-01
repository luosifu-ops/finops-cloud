<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">提成规则</h2>
      <el-button type="primary" :icon="Plus" @click="openCreate">新增规则</el-button>
    </div>

    <el-card shadow="never" class="block-card">
      <div class="card-title">规则列表<el-button text size="small" :icon="Refresh" @click="load" style="float:right">刷新</el-button></div>
      <el-table :data="rules" size="small" stripe max-height="460" empty-text="暂无提成规则">
        <el-table-column prop="name" label="规则名称" min-width="160" />
        <el-table-column label="类型" width="110">
          <template #default="{row}"><el-tag size="small" :type="row.rule_type==='LADDER'?'warning':(row.rule_type==='RATE'?'success':'info')">{{ typeName(row.rule_type) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="department_name" label="适用部门" width="120" />
        <el-table-column label="比例 / 固定" width="140">
          <template #default="{row}">
            <span v-if="row.rule_type==='FIXED'">{{ fmtMoney(row.fixed_amount) }}/单</span>
            <span v-else>{{ row.rate }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="阶梯配置" min-width="280">
          <template #default="{row}">
            <span v-if="row.rule_type==='LADDER' && row.ladder && row.ladder.length">
              <el-tag v-for="(t,i) in row.ladder" :key="i" size="small" effect="plain" class="ladder-tag">{{ fmtMoney(t.min) }}~{{ t.max>=1000000?'∞':fmtMoney(t.max) }}：{{ t.rate }}%</el-tag>
            </span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="effective_month" label="生效月" width="110" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{row}">
            <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="visible" :title="editingId?'编辑规则':'新增规则'" width="620px" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-form-item label="规则名称" required>
          <el-input v-model="form.name" placeholder="如：电销部提成方案" />
        </el-form-item>
        <el-form-item label="适用部门">
          <el-select v-model="form.department" placeholder="全公司通用（留空）" clearable style="width:100%">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="规则类型" required>
          <el-radio-group v-model="form.rule_type">
            <el-radio value="RATE">按比例</el-radio>
            <el-radio value="FIXED">固定金额</el-radio>
            <el-radio value="LADDER">阶梯</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.rule_type==='RATE'" label="提成比例" required>
          <el-input-number v-model="form.rate" :min="0" :max="100" :precision="2" :step="1" style="width:100%" />
          <span class="suffix">%</span>
        </el-form-item>
        <el-form-item v-if="form.rule_type==='FIXED'" label="固定金额" required>
          <el-input-number v-model="form.fixed_amount" :min="0" :precision="2" :step="100" style="width:100%" />
          <span class="suffix">元/单</span>
        </el-form-item>
        <el-form-item v-if="form.rule_type==='LADDER'" label="阶梯配置">
          <div class="ladder-editor">
            <div class="ladder-head">
              <span>区间下限</span><span>区间上限</span><span>比例</span><span></span>
            </div>
            <div class="ladder-row" v-for="(t,i) in form.ladder" :key="i">
              <el-input-number v-model="t.min" :min="0" :step="1000" controls-position="right" />
              <el-input-number v-model="t.max" :min="0" :step="1000" controls-position="right" />
              <el-input-number v-model="t.rate" :min="0" :max="100" :precision="2" :step="1" controls-position="right" />
              <el-button :icon="Minus" circle size="small" type="danger" @click="delLadder(i)" />
            </div>
            <el-button :icon="Plus" size="small" plain @click="addLadder">新增阶梯</el-button>
            <div class="muted tip">上限填 1000000 表示「及以上」（∞）</div>
          </div>
        </el-form-item>
        <el-form-item label="生效月份">
          <el-date-picker v-model="form.effective_month" type="month" value-format="YYYY-MM" placeholder="不选表示长期有效" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Edit, Delete, Minus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import http, { salesApi, orgApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const rules = ref([])
const departments = ref([])
const visible = ref(false)
const editingId = ref(null)
const form = reactive({
  name: '', department: '', rule_type: 'RATE', rate: 10, fixed_amount: 0, ladder: [], effective_month: ''
})

function parseList(resp) {
  if (!resp) return []
  let b = resp
  if (b && typeof b === 'object' && 'code' in b && 'data' in b) b = b.data
  if (b && b.results) return b.results
  if (Array.isArray(b)) return b
  if (b && typeof b === 'object') return [b]
  return []
}
const fmtMoney = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))
const typeName = (t) => ({ RATE: '按比例', FIXED: '固定金额', LADDER: '阶梯' }[t] || t)

const load = async () => {
  loading.value = true
  try { const r = await salesApi.commissionRules({ page_size: 200 }); rules.value = parseList(r) } catch (e) {} finally { loading.value = false }
}
const loadDepartments = async () => {
  try { const r = await orgApi.departments({ page_size: 200 }); const l = parseList(r); departments.value = l } catch (e) {}
}

const addLadder = () => form.ladder.push({ min: 0, max: 1000000, rate: 0 })
const delLadder = (i) => form.ladder.splice(i, 1)

const resetForm = () => {
  editingId.value = null
  Object.assign(form, { name: '', department: '', rule_type: 'RATE', rate: 10, fixed_amount: 0, ladder: [], effective_month: '' })
}
const openCreate = () => { resetForm(); visible.value = true }
const openEdit = (row) => {
  resetForm()
  Object.assign(form, {
    name: row.name, department: row.department, rule_type: row.rule_type,
    rate: Number(row.rate) || 0, fixed_amount: Number(row.fixed_amount) || 0,
    ladder: Array.isArray(row.ladder) ? row.ladder.map(t => ({ ...t })) : [],
    effective_month: row.effective_month || ''
  })
  editingId.value = row.id
  visible.value = true
}
const submit = async () => {
  if (!form.name) return ElMessage.warning('请填写规则名称')
  saving.value = true
  const payload = {
    name: form.name, rule_type: form.rule_type,
    department: form.department || null,
    effective_month: form.effective_month || null
  }
  if (form.rule_type === 'RATE') payload.rate = form.rate
  else if (form.rule_type === 'FIXED') payload.fixed_amount = form.fixed_amount
  else payload.ladder = form.ladder
  try {
    if (editingId.value) await http.patch(`/sales/commission-rules/${editingId.value}/`, payload)
    else await http.post('/sales/commission-rules/', payload)
    ElMessage.success('已保存')
    visible.value = false
    await load()
  } catch (e) {} finally { saving.value = false }
}
const remove = async (row) => {
  try { await ElMessageBox.confirm(`确认删除规则「${row.name}」？`, '删除', { type: 'warning' }) } catch { return }
  try { await http.delete(`/sales/commission-rules/${row.id}/`); ElMessage.success('已删除'); await load() } catch (e) {}
}

onMounted(async () => { await loadDepartments(); await load() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.block-card { border-radius: 10px; border: 1px solid var(--border); }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
.ladder-tag { margin: 0 6px 4px 0; }
.muted { color: #909399; }
.suffix { margin-left: 8px; color: var(--text-sub); }
.tip { margin-top: 6px; font-size: 12px; }
.ladder-editor { width: 100%; }
.ladder-head, .ladder-row { display: grid; grid-template-columns: 1fr 1fr 1fr 40px; gap: 8px; align-items: center; margin-bottom: 8px; }
.ladder-head span { font-size: 12px; color: var(--text-sub); }
.ladder-row .el-input-number { width: 100%; }
</style>
