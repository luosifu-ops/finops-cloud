<template>
  <div class="bank-view">
    <el-row :gutter="16" v-loading="loading">
      <!-- 左侧题库 -->
      <el-col :span="7">
        <el-card shadow="never" class="bank-list">
          <div class="bl-head">
            <span class="bl-title">题库</span>
            <el-button type="primary" size="small" :icon="Plus" @click="openBankCreate">新建</el-button>
          </div>
          <div v-for="b in banks" :key="b.id" class="bank-item" :class="{ active: b.id === curBank }" @click="selectBank(b)">
            <div class="bank-item-main">
              <span class="bank-name">{{ b.name }}</span>
              <span class="bank-count">{{ b.question_count || 0 }} 题</span>
            </div>
            <div class="bank-item-desc">{{ b.description || '' }}</div>
            <div class="bank-item-ops">
              <el-button link type="primary" size="small" @click.stop="openBankEdit(b)">重命名</el-button>
              <el-button link type="danger" size="small" @click.stop="delBank(b)">删除</el-button>
            </div>
          </div>
          <el-empty v-if="!banks.length" description="暂无题库" :image-size="60" />
        </el-card>
      </el-col>

      <!-- 右侧题目 -->
      <el-col :span="17">
        <el-card shadow="never" v-if="curBank">
          <div class="q-head">
            <span class="q-title">题目列表</span>
            <div class="q-tools">
              <el-select v-model="qtypeFilter" placeholder="题型" clearable style="width:120px" @change="loadQuestions">
                <el-option v-for="t in qtypes" :key="t.value" :label="t.label" :value="t.value" />
              </el-select>
              <el-input v-model="kw" placeholder="关键词" clearable style="width:150px" @keyup.enter="loadQuestions" @clear="loadQuestions" />
              <el-button @click="loadQuestions">查询</el-button>
              <el-button type="primary" :icon="Plus" @click="openQuestionCreate">新增题目</el-button>
            </div>
          </div>
          <el-table :data="questions" size="small" stripe max-height="520" v-loading="qLoading">
            <el-table-column prop="stem" label="题干" min-width="220" show-overflow-tooltip />
            <el-table-column label="题型" width="80"><template #default="{row}">{{ qtypeName(row.qtype) }}</template></el-table-column>
            <el-table-column prop="score" label="分值" width="64" align="center" />
            <el-table-column label="难度" width="74" align="center">
              <template #default="{ row }">{{ levelMap[row.level] || row.level }}</template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{row}">
                <el-button link type="primary" @click="openQuestionEdit(row)">编辑</el-button>
                <el-button link type="danger" @click="delQuestion(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!qLoading && !questions.length" description="该题库暂无题目" />
        </el-card>
        <el-empty v-else description="请选择左侧题库" />
      </el-col>
    </el-row>

    <!-- 题库新建/重命名 -->
    <el-dialog v-model="bankVis" :title="bankEditing ? '重命名题库' : '新建题库'" width="420px">
      <el-form label-width="72px">
        <el-form-item label="名称" required><el-input v-model="bankName" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="bankDesc" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bankVis = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveBank">保存</el-button>
      </template>
    </el-dialog>

    <!-- 题目新建/编辑 -->
    <el-dialog v-model="qVis" :title="qEditing ? '编辑题目' : '新增题目'" width="640px" @closed="resetQ">
      <el-form :model="qf" label-width="80px">
        <el-form-item label="题型" required>
          <el-select v-model="qf.qtype" style="width:100%" @change="onQtypeChange">
            <el-option v-for="t in qtypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干" required><el-input v-model="qf.stem" type="textarea" :rows="3" /></el-form-item>
        <!-- 选项编辑（单选/多选） -->
        <el-form-item v-if="needOptions" label="选项">
          <div class="opts">
            <div v-for="(o, i) in qf.options" :key="i" class="opt-row">
              <span class="opt-key">{{ keyOf(i) }}</span>
              <el-input v-model="o.text" placeholder="选项内容" />
              <el-button link type="danger" :icon="Delete" @click="qf.options.splice(i, 1)" />
            </div>
            <el-button text :icon="Plus" @click="qf.options.push({ key: '', text: '' })">添加选项</el-button>
          </div>
        </el-form-item>
        <el-form-item label="正确答案" required>
          <el-select v-if="qf.qtype === 'JUDGE'" v-model="qf.answer" style="width:100%">
            <el-option label="正确（对）" value="对" /><el-option label="错误（错）" value="错" />
          </el-select>
          <el-select v-else-if="qf.qtype === 'SINGLE'" v-model="qf.answer" style="width:100%" placeholder="选择正确选项">
            <el-option v-for="(o, i) in qf.options" :key="i" :label="keyOf(i) + '. ' + o.text" :value="keyOf(i)" :disabled="!o.text" />
          </el-select>
          <el-select v-else-if="qf.qtype === 'MULTI'" v-model="qf.answer" multiple style="width:100%" placeholder="可多选正确选项">
            <el-option v-for="(o, i) in qf.options" :key="i" :label="keyOf(i) + '. ' + o.text" :value="keyOf(i)" :disabled="!o.text" />
          </el-select>
          <el-input v-else v-model="qf.answer" :type="qf.qtype === 'ESSAY' ? 'textarea' : 'text'" :rows="3" placeholder="填空/简答答案" />
        </el-form-item>
        <el-form-item label="解析"><el-input v-model="qf.analysis" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="分值"><el-input-number v-model="qf.score" :min="1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="难度">
            <el-select v-model="qf.level" style="width:100%">
              <el-option label="入门" value="BASIC" /><el-option label="进阶" value="MIDDLE" /><el-option label="高阶" value="ADVANCED" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="qVis = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveQuestion">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { onboardingApi } from '@/api'

const loading = ref(false)
const qLoading = ref(false)
const banks = ref([])
const curBank = ref(null)
const questions = ref([])
const qtypeFilter = ref('')
const kw = ref('')

const qtypes = [
  { value: 'SINGLE', label: '单选题' }, { value: 'MULTI', label: '多选题' },
  { value: 'JUDGE', label: '判断题' }, { value: 'FILL', label: '填空题' }, { value: 'ESSAY', label: '简答题' }
]
const qtypeName = (t) => (qtypes.find(x => x.value === t) || {}).label || t
const levelMap = { BASIC: '入门', MIDDLE: '进阶', ADVANCED: '高阶' }
const needOptions = computed(() => ['SINGLE', 'MULTI'].includes(qf.qtype))
const keyOf = (i) => String.fromCharCode(65 + i)

const unwrap = (r) => { const b = r || {}; return (b && typeof b === 'object' && !Array.isArray(b) && 'code' in b && 'data' in b) ? b.data : b }
const asList = (p) => { if (!p) return []; if (Array.isArray(p)) return p; if (p.results) return p.results; return [p] }

async function loadBanks() {
  loading.value = true
  try { banks.value = asList(unwrap(await onboardingApi.questionBanks())) } finally { loading.value = false }
}
async function loadQuestions() {
  if (!curBank.value) return
  qLoading.value = true
  try {
    const p = { bank: curBank.value }
    if (qtypeFilter.value) p.qtype = qtypeFilter.value
    if (kw.value) p.search = kw.value
    questions.value = asList(unwrap(await onboardingApi.questions(p)))
  } finally { qLoading.value = false }
}
function selectBank(b) { curBank.value = b.id; qtypeFilter.value = ''; kw.value = ''; loadQuestions() }

// 题库 CRUD
const bankVis = ref(false)
const bankEditing = ref(null)
const bankName = ref('')
const bankDesc = ref('')
const saving = ref(false)
function openBankCreate() { bankEditing.value = null; bankName.value = ''; bankDesc.value = ''; bankVis.value = true }
function openBankEdit(b) { bankEditing.value = b; bankName.value = b.name; bankDesc.value = b.description || ''; bankVis.value = true }
async function saveBank() {
  if (!bankName.value) return ElMessage.warning('请填写名称')
  saving.value = true
  try {
    if (bankEditing.value) await onboardingApi.updateBank(bankEditing.value.id, { name: bankName.value, description: bankDesc.value })
    else await onboardingApi.createBank({ name: bankName.value, description: bankDesc.value })
    ElMessage.success('已保存'); bankVis.value = false; loadBanks()
  } catch (e) { ElMessage.error('保存失败') } finally { saving.value = false }
}
async function delBank(b) {
  try { await ElMessageBox.confirm(`确认删除题库「${b.name}」？其下题目将一并删除`, '提示', { type: 'warning' }) } catch { return }
  try { await onboardingApi.deleteBank(b.id); ElMessage.success('已删除'); if (curBank.value === b.id) curBank.value = null; loadBanks() } catch (e) { ElMessage.error('删除失败') }
}

// 题目 CRUD
const qVis = ref(false)
const qEditing = ref(null)
const qf = reactive({ qtype: 'SINGLE', stem: '', options: [], answer: '', analysis: '', score: 5, level: 'BASIC' })
function resetQ() { Object.assign(qf, { qtype: 'SINGLE', stem: '', options: [], answer: '', analysis: '', score: 5, level: 'BASIC' }) }
function onQtypeChange() { qf.answer = ['SINGLE', 'MULTI'].includes(qf.qtype) && !Array.isArray(qf.answer) ? '' : (qf.qtype === 'MULTI' && !Array.isArray(qf.answer) ? [] : qf.answer); qf.options = [] }
function openQuestionCreate() {
  if (!curBank.value) return ElMessage.warning('请先选择题库')
  resetQ(); qEditing.value = null; qVis.value = true
}
function openQuestionEdit(row) {
  qEditing.value = row
  qf.qtype = row.qtype; qf.stem = row.stem
  qf.options = Array.isArray(row.options) ? row.options.map(o => ({ ...o })) : []
  qf.answer = row.answer || ''
  qf.analysis = row.analysis || ''; qf.score = row.score || 5; qf.level = row.level || 'BASIC'
  qVis.value = true
}
async function saveQuestion() {
  if (!qf.stem) return ElMessage.warning('请填写题干')
  if (!qf.answer || (Array.isArray(qf.answer) && !qf.answer.length)) return ElMessage.warning('请设置正确答案')
  saving.value = true
  try {
    const opts = needOptions.value ? qf.options.filter(o => o.text).map((o, i) => ({ key: keyOf(i), text: o.text })) : []
    const payload = { bank: curBank.value, qtype: qf.qtype, stem: qf.stem, options: opts, answer: Array.isArray(qf.answer) ? qf.answer.join('') : qf.answer, analysis: qf.analysis, score: qf.score, level: qf.level }
    if (qEditing.value) await onboardingApi.updateQuestion(qEditing.value.id, payload)
    else await onboardingApi.createQuestion(payload)
    ElMessage.success('已保存'); qVis.value = false; loadQuestions(); loadBanks()
  } catch (e) { ElMessage.error('保存失败') } finally { saving.value = false }
}
async function delQuestion(row) {
  try { await ElMessageBox.confirm('确认删除该题目？', '提示', { type: 'warning' }) } catch { return }
  try { await onboardingApi.deleteQuestion(row.id); ElMessage.success('已删除'); loadQuestions(); loadBanks() } catch (e) { ElMessage.error('删除失败') }
}

loadBanks()
</script>

<style scoped>
.bank-list { min-height: 560px; }
.bl-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.bl-title { font-weight: 700; font-size: 15px; }
.bank-item { padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px; cursor: pointer; }
.bank-item.active { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); }
.bank-item-main { display: flex; justify-content: space-between; }
.bank-name { font-weight: 600; }
.bank-count { font-size: 12px; color: var(--text-sub); }
.bank-item-desc { font-size: 12px; color: var(--text-sub); margin: 4px 0 6px; min-height: 16px; }
.q-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.q-title { font-weight: 700; font-size: 15px; }
.q-tools { display: flex; gap: 8px; align-items: center; }
.opts { width: 100%; }
.opt-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.opt-key { width: 24px; text-align: center; font-weight: 700; }
</style>
