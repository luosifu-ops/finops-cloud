<template>
  <div class="exam-center">
    <div class="ec-head">
      <div>
        <h2 class="ec-title">考试中心</h2>
        <span class="ec-tip">下方面试/转正/业务考试，点击「开始考试」进入作答</span>
      </div>
      <el-button v-if="user.isHR || user.isBoss" type="primary" :icon="Plus" @click="openCreate">新建考试</el-button>
    </div>

    <el-row v-loading="loading" :gutter="16">
      <el-col v-for="ex in exams" :key="ex.id" :span="8" class="ec-card-wrap">
        <el-card shadow="hover" class="ec-card">
          <div class="ec-card-title">{{ ex.title }}</div>
          <div class="ec-card-desc">{{ ex.description || '暂无说明' }}</div>
          <el-descriptions :column="2" size="small" class="ec-meta">
            <el-descriptions-item label="题量">{{ ex.question_count }}</el-descriptions-item>
            <el-descriptions-item label="时长">{{ ex.duration }} 分钟</el-descriptions-item>
            <el-descriptions-item label="总分">{{ ex.total_score }}</el-descriptions-item>
            <el-descriptions-item label="及格">{{ ex.pass_score }}</el-descriptions-item>
          </el-descriptions>
          <div class="ec-times">
            开放：{{ fmtTime(ex.start_at) }} ～ {{ fmtTime(ex.end_at) }}
          </div>
          <div class="ec-foot">
            <span class="ec-try">我已考 {{ myTried(ex.id) }}/{{ ex.max_attempts }} 次</span>
            <el-button type="primary" size="small" :disabled="!canStart(ex)" @click="startExam(ex)">开始考试</el-button>
          </div>
          <el-tag v-if="!canStart(ex)" size="small" type="info" effect="plain" class="ec-disabled">
            {{ startTip(ex) }}
          </el-tag>
        </el-card>
      </el-col>
    </el-row>
    <el-empty v-if="!loading && !exams.length" description="暂无可参加考试" />

    <!-- 答题弹窗 -->
    <el-dialog v-model="paperVis" fullscreen class="exam-paper" @close="closePaper">
      <template #header>
        <div class="ep-head">
          <span class="ep-title">{{ paper.title }}（第 {{ paper.attempt }} 次）</span>
          <span class="ep-timer" :class="{ danger: timeLeft <= 60 }">剩余 {{ mmss(timeLeft) }}</span>
          <el-button type="danger" @click="submitPaper">交卷</el-button>
          <el-button text @click="sheetVis = true">答题卡</el-button>
        </div>
      </template>
      <div v-if="paper.questions && paper.questions.length" class="ep-body">
        <div v-for="(q, i) in paper.questions" :key="q.id" :ref="el => qRefs[i] = el" class="ep-q">
          <div class="ep-q-stem">
            <span class="ep-no">{{ i + 1 }}.</span>
            <el-tag size="small" effect="plain">{{ qtypeName(q.qtype) }}</el-tag>
            <span class="ep-score">{{ q.score }}分</span>
            <span>{{ q.stem }}</span>
          </div>
          <!-- 单选 -->
          <el-radio-group v-if="q.qtype === 'SINGLE'" v-model="answers[q.id]">
            <el-radio v-for="o in (q.options || [])" :key="o.key" :value="o.key" class="ep-opt">{{ o.key }}. {{ o.text }}</el-radio>
          </el-radio-group>
          <!-- 多选 -->
          <el-checkbox-group v-else-if="q.qtype === 'MULTI'" v-model="answers[q.id]">
            <el-checkbox v-for="o in (q.options || [])" :key="o.key" :value="o.key" class="ep-opt">{{ o.key }}. {{ o.text }}</el-checkbox>
          </el-checkbox-group>
          <!-- 判断 -->
          <el-radio-group v-else-if="q.qtype === 'JUDGE'" v-model="answers[q.id]">
            <el-radio value="对" class="ep-opt">正确</el-radio>
            <el-radio value="错" class="ep-opt">错误</el-radio>
          </el-radio-group>
          <!-- 填空/简答 -->
          <el-input v-else v-model="answers[q.id]" :type="q.qtype === 'ESSAY' ? 'textarea' : 'text'"
                    :rows="3" :placeholder="q.qtype === 'FILL' ? '请输入答案' : '请输入你的作答'" />
        </div>
      </div>
      <el-empty v-else description="未获取到题目" />
    </el-dialog>

    <!-- 答题卡 -->
    <el-drawer v-model="sheetVis" title="答题卡" direction="rtl" size="320px">
      <div class="sheet-grid">
        <div v-for="(q, i) in (paper.questions || [])" :key="q.id"
             class="sheet-cell" :class="{ done: isAnswered(q) }" @click="jump(i)">
          {{ i + 1 }}
        </div>
      </div>
      <div class="sheet-legend"><span class="dot done" />已答 <span class="dot" />未答</div>
    </el-drawer>

    <!-- 成绩 -->
    <el-dialog v-model="resultVis" title="考试成绩" width="420px" align-center>
      <el-result :icon="result.passed ? 'success' : 'error'" :title="result.passed ? '恭喜，已通过' : '很遗憾，未通过'">
        <template #sub-title>
          <div>得分 <b>{{ result.score }}</b> / 及格分 {{ result.pass_score }}</div>
          <div v-if="result.pending_count" class="ep-pending">有 {{ result.pending_count }} 道填空/简答题待人工阅卷，分数可能更新</div>
        </template>
      </el-result>
      <template #footer>
        <el-button type="primary" @click="afterResult">知道了</el-button>
      </template>
    </el-dialog>

    <!-- 新建考试 -->
    <el-dialog v-model="createVis" title="新建考试" width="560px" @closed="resetCreate">
      <el-form :model="cf" label-width="92px">
        <el-form-item label="考试名称" required><el-input v-model="cf.title" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="cf.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="题库">
          <el-select v-model="cf.bank" placeholder="选择题库" clearable style="width:100%">
            <el-option v-for="b in banks" :key="b.id" :label="b.name" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="抽题数量"><el-input-number v-model="cf.question_count" :min="1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="考试时长(分)"><el-input-number v-model="cf.duration" :min="1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="总分"><el-input-number v-model="cf.total_score" :min="1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="及格分"><el-input-number v-model="cf.pass_score" :min="0" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="最大次数"><el-input-number v-model="cf.max_attempts" :min="1" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态">
            <el-select v-model="cf.status" style="width:100%">
              <el-option label="草稿" value="DRAFT" /><el-option label="已发布" value="PUBLISHED" /><el-option label="已结束" value="CLOSED" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="开放时间"><el-date-picker v-model="cf.start_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="截止时间"><el-date-picker v-model="cf.end_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="允许重考"><el-switch v-model="cf.allow_retake" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVis = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createExam">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { onboardingApi } from '@/api'
import { useUserStore } from '@/store/user'

const user = useUserStore()
const loading = ref(false)
const exams = ref([])
const records = ref([])
const banks = ref([])

const unwrap = (r) => { const b = r || {}; return (b && typeof b === 'object' && !Array.isArray(b) && 'code' in b && 'data' in b) ? b.data : b }
const asList = (p) => { if (!p) return []; if (Array.isArray(p)) return p; if (p.results) return p.results; return [p] }
const fmtTime = (t) => t ? String(t).replace('T', ' ').slice(0, 16) : '不限'
const qtypeName = (t) => ({ SINGLE: '单选', MULTI: '多选', JUDGE: '判断', FILL: '填空', ESSAY: '简答' }[t] || t)
const myTried = (id) => records.value.filter(r => r.exam === id).length

function canStart(ex) {
  if (ex.status !== 'PUBLISHED') return false
  if (myTried(ex.id) >= (ex.max_attempts || 1)) return false
  if (!ex.allow_retake && myTried(ex.id) > 0) return false
  return true
}
function startTip(ex) {
  if (ex.status !== 'PUBLISHED') return '尚未发布'
  if (myTried(ex.id) >= (ex.max_attempts || 1)) return '次数已用完'
  if (!ex.allow_retake && myTried(ex.id) > 0) return '不可重考'
  return '可参加'
}

async function load() {
  loading.value = true
  try {
    const [e, r, b] = await Promise.all([
      onboardingApi.exams({ status: 'PUBLISHED' }),
      onboardingApi.myExamRecords(),
      user.isHR || user.isBoss ? onboardingApi.questionBanks() : Promise.resolve(null)
    ])
    exams.value = asList(unwrap(e))
    records.value = asList(unwrap(r))
    banks.value = asList(unwrap(b))
  } finally { loading.value = false }
}

// ---------- 答题 ----------
const paperVis = ref(false)
const sheetVis = ref(false)
const resultVis = ref(false)
const paper = reactive({ examId: null, title: '', attempt: 1, duration: 60, questions: [], record_id: null })
const answers = reactive({})
const qRefs = ref([])
const timeLeft = ref(0)
let timer = null
const result = reactive({ score: 0, pass_score: 0, passed: false, pending_count: 0 })

async function startExam(ex) {
  try {
    const r = unwrap(await onboardingApi.startExam(ex.id))
    paper.examId = ex.id
    paper.title = ex.title
    paper.attempt = r.attempt
    paper.duration = r.duration
    paper.questions = r.questions || []
    paper.record_id = r.record_id
    for (const q of paper.questions) answers[q.id] = q.qtype === 'MULTI' ? [] : ''
    qRefs.value = []
    paperVis.value = true
    startTimer()
  } catch (e) { /* 拦截器已提示 */ }
}
function startTimer() {
  clearInterval(timer)
  timeLeft.value = paper.duration * 60
  timer = setInterval(() => {
    timeLeft.value--
    if (timeLeft.value <= 0) { clearInterval(timer); submitPaper(true) }
  }, 1000)
}
const mmss = (s) => { const m = Math.floor(s / 60), ss = s % 60; return `${String(m).padStart(2, '0')}:${String(ss).padStart(2, '0')}` }
const isAnswered = (q) => { const v = answers[q.id]; return q.qtype === 'MULTI' ? (Array.isArray(v) && v.length) : (v !== '' && v != null) }
function jump(i) { const el = qRefs.value[i]; if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); sheetVis.value = false }

async function submitPaper(auto = false) {
  const payload = {}
  for (const q of paper.questions) {
    let v = answers[q.id]
    if (q.qtype === 'MULTI' && Array.isArray(v)) v = v.join('')
    payload[q.id] = v ?? ''
  }
  clearInterval(timer)
  try {
    const r = unwrap(await onboardingApi.submitExam(paper.examId, { record_id: paper.record_id, answers: payload }))
    Object.assign(result, { score: r.score, pass_score: r.pass_score, passed: r.passed, pending_count: r.pending_count || 0 })
    resultVis.value = true
    if (auto) ElMessage.warning('时间到，已自动交卷')
  } catch (e) { /* 拦截器已提示 */ }
}
function afterResult() { resultVis.value = false; paperVis.value = false; load() }
function closePaper() { clearInterval(timer) }

// ---------- 新建考试 ----------
const createVis = ref(false)
const saving = ref(false)
const cf = reactive({ title: '', description: '', bank: null, question_count: 20, total_score: 100, pass_score: 60, duration: 60, max_attempts: 3, status: 'PUBLISHED', allow_retake: true, start_at: '', end_at: '' })
function openCreate() { createVis.value = true }
function resetCreate() { Object.assign(cf, { title: '', description: '', bank: null, question_count: 20, total_score: 100, pass_score: 60, duration: 60, max_attempts: 3, status: 'PUBLISHED', allow_retake: true, start_at: '', end_at: '' }) }
async function createExam() {
  if (!cf.title) return ElMessage.warning('请填写考试名称')
  saving.value = true
  try {
    await onboardingApi.createExam({ ...cf })
    ElMessage.success('已创建考试')
    createVis.value = false
    load()
  } catch (e) { ElMessage.error('创建失败') } finally { saving.value = false }
}

onMounted(load)
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.ec-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.ec-title { font-size: 18px; margin: 0; }
.ec-tip { font-size: 12px; color: var(--text-sub); margin-left: 10px; }
.ec-card-wrap { margin-bottom: 16px; }
.ec-card { border-radius: 10px; }
.ec-card-title { font-weight: 700; font-size: 15px; }
.ec-card-desc { color: var(--text-sub); font-size: 12px; margin: 6px 0 10px; min-height: 18px; }
.ec-meta { margin-bottom: 8px; }
.ec-times { font-size: 12px; color: var(--text-sub); margin-bottom: 10px; }
.ec-foot { display: flex; align-items: center; justify-content: space-between; }
.ec-try { font-size: 12px; color: var(--text-sub); }
.ec-disabled { margin-top: 8px; }
.exam-paper :deep(.el-dialog__header) { margin-right: 0; }
.ep-head { display: flex; align-items: center; gap: 14px; }
.ep-title { font-weight: 700; }
.ep-timer { font-size: 16px; font-weight: 700; color: var(--success); }
.ep-timer.danger { color: #d93026; }
.ep-body { padding: 8px 4px; }
.ep-q { padding: 14px 0; border-bottom: 1px solid var(--border); scroll-margin-top: 16px; }
.ep-q-stem { margin-bottom: 10px; line-height: 1.6; }
.ep-no { font-weight: 700; margin-right: 4px; }
.ep-score { color: var(--text-sub); font-size: 12px; margin: 0 6px; }
.ep-opt { display: block; margin: 6px 0; }
.ep-pending { color: #b88230; font-size: 13px; margin-top: 6px; }
.sheet-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; }
.sheet-cell { height: 36px; line-height: 36px; text-align: center; border-radius: 6px; background: #f4f4f5; cursor: pointer; }
.sheet-cell.done { background: var(--success); color: #fff; }
.sheet-legend { margin-top: 16px; font-size: 12px; color: var(--text-sub); }
.dot { display: inline-block; width: 12px; height: 12px; border-radius: 3px; background: #f4f4f5; vertical-align: middle; margin: 0 4px 0 10px; }
.dot.done { background: var(--success); }
</style>
