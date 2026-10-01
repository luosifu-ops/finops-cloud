<template>
  <div class="profile-view">
    <el-tabs v-model="tab">
      <el-tab-pane label="我的入职资料" name="mine" />
      <el-tab-pane v-if="user.isHR || user.isBoss" label="待审管理" name="review" />
    </el-tabs>

    <!-- 我的资料 -->
    <template v-if="tab === 'mine'">
      <el-alert v-if="profile" :title="`当前状态：${profile.status_name}`" :type="statusType" :closable="false" show-icon>
        <template #default>
          <span v-if="profile.review_by_name">审核人：{{ profile.review_by_name }} · 审核时间：{{ fmt(profile.review_at) }}</span>
          <span v-if="profile.review_remark"> · 审核意见：{{ profile.review_remark }}</span>
          <span v-if="profile.status === 'REJECTED'" class="rej-hint">（可修改后重新提交）</span>
        </template>
      </el-alert>

      <el-steps :active="step" finish-status="success" class="pf-steps" align-center>
        <el-step title="基本信息" /><el-step title="身份与证件" /><el-step title="工作与银行" /><el-step title="提交确认" />
      </el-steps>

      <el-form ref="formRef" :model="form" label-width="110px" class="pf-form" v-loading="loading">
        <!-- 步骤1 -->
        <div v-show="step === 0">
          <el-row :gutter="16">
            <el-col :span="12"><el-form-item label="姓名" required><el-input v-model="form.name" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="手机号" required><el-input v-model="form.phone" maxlength="11" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="身份证号" required><el-input v-model="form.id_card_no" maxlength="18" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="性别"><el-select v-model="form.gender" clearable style="width:100%"><el-option label="男" value="男" /><el-option label="女" value="女" /></el-select></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="出生日期"><el-date-picker v-model="form.birth_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="学历"><el-select v-model="form.education" style="width:100%"><el-option v-for="e in educations" :key="e.value" :label="e.label" :value="e.value" /></el-select></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="毕业院校"><el-input v-model="form.school" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="家庭住址"><el-input v-model="form.address" /></el-form-item></el-col>
          </el-row>
        </div>
        <!-- 步骤2 -->
        <div v-show="step === 1">
          <el-row :gutter="16">
            <el-col :span="12"><el-form-item label="身份证人像面"><upload-img :model="files.id_card_front" :file="profile && profile.id_card_front" tip="点击上传人像面" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="身份证国徽面"><upload-img :model="files.id_card_back" :file="profile && profile.id_card_back" tip="点击上传国徽面" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="学历证书"><upload-img :model="files.diploma" :file="profile && profile.diploma" tip="点击上传学历证书" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="一寸照片"><upload-img :model="files.photo" :file="profile && profile.photo" tip="点击上传一寸照" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="紧急联系人"><el-input v-model="form.emergency_contact" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="紧急联系电话"><el-input v-model="form.emergency_phone" /></el-form-item></el-col>
          </el-row>
        </div>
        <!-- 步骤3 -->
        <div v-show="step === 2">
          <el-row :gutter="16">
            <el-col :span="12"><el-form-item label="拟入职部门" required><el-select v-model="form.department" filterable placeholder="选择部门" style="width:100%"><el-option v-for="d in depts" :key="d.id" :label="d.name" :value="d.id" /></el-select></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="拟任岗位" required><el-input v-model="form.position" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="预计入职日期"><el-date-picker v-model="form.entry_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="工资卡号"><el-input v-model="form.bank_card_no" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="银行卡照片"><upload-img :model="files.bank_card_img" :file="profile && profile.bank_card_img" tip="点击上传银行卡" /></el-form-item></el-col>
            <el-col :span="12"><el-form-item label="简历附件"><upload-file :model="files.resume" :file="profile && profile.resume" /></el-form-item></el-col>
          </el-row>
        </div>
        <!-- 步骤4 -->
        <div v-show="step === 3" v-loading="!profile && loading">
          <el-descriptions :column="2" border size="small" class="pf-confirm">
            <el-descriptions-item label="姓名">{{ form.name }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ form.phone }}</el-descriptions-item>
            <el-descriptions-item label="身份证号">{{ form.id_card_no }}</el-descriptions-item>
            <el-descriptions-item label="性别">{{ form.gender }}</el-descriptions-item>
            <el-descriptions-item label="学历">{{ eduName(form.education) }}</el-descriptions-item>
            <el-descriptions-item label="毕业院校">{{ form.school }}</el-descriptions-item>
            <el-descriptions-item label="家庭住址">{{ form.address }}</el-descriptions-item>
            <el-descriptions-item label="紧急联系人">{{ form.emergency_contact }} / {{ form.emergency_phone }}</el-descriptions-item>
            <el-descriptions-item label="拟入职部门">{{ deptName(form.department) }}</el-descriptions-item>
            <el-descriptions-item label="拟任岗位">{{ form.position }}</el-descriptions-item>
            <el-descriptions-item label="预计入职日期">{{ form.entry_date }}</el-descriptions-item>
            <el-descriptions-item label="工资卡号">{{ form.bank_card_no }}</el-descriptions-item>
          </el-descriptions>
          <div class="pf-file-tip">证件/照片/简历附件已包含在上述步骤上传内容中，提交时一并报送。</div>
        </div>
      </el-form>

      <div class="pf-actions">
        <el-button v-if="step > 0" @click="step--">上一步</el-button>
        <el-button v-if="step < 3" type="primary" @click="next">下一步</el-button>
        <el-button v-else type="success" :loading="submitting" @click="submit">提交入职资料</el-button>
      </div>
    </template>

    <!-- 待审管理 -->
    <template v-else>
      <el-table :data="pendings" v-loading="rvLoading" stripe border style="width:100%">
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="department_name" label="部门" width="120" />
        <el-table-column prop="position" label="岗位" width="120" />
        <el-table-column prop="id_card_no" label="身份证号" width="180" />
        <el-table-column prop="created_at" label="提交时间" min-width="150"><template #default="{row}">{{ fmt(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{row}">
            <el-button link type="success" @click="review(row, 'APPROVE')">通过</el-button>
            <el-button link type="danger" @click="review(row, 'REJECT')">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!rvLoading && !pendings.length" description="暂无待审核资料" />
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { onboardingApi, orgApi } from '@/api'
import { useUserStore } from '@/store/user'

const user = useUserStore()
const tab = ref('mine')
const loading = ref(false)
const submitting = ref(false)
const step = ref(0)
const formRef = ref(null)
const profile = ref(null)
const depts = ref([])

const educations = [
  { value: 'HIGH', label: '高中及以下' }, { value: 'COLLEGE', label: '大专' },
  { value: 'BACHELOR', label: '本科' }, { value: 'MASTER', label: '硕士及以上' }
]
const eduName = (v) => (educations.find(e => e.value === v) || {}).label || '—'
const deptName = (v) => (depts.value.find(d => d.id === v) || {}).name || '—'
const statusType = computed(() => ({ DRAFT: 'info', SUBMITTED: 'warning', APPROVED: 'success', REJECTED: 'error' }[profile.value?.status] || 'info'))
const fmt = (t) => t ? String(t).replace('T', ' ').slice(0, 16) : '—'

const form = reactive({ name: '', phone: '', id_card_no: '', gender: '', birth_date: '', education: 'COLLEGE', school: '', address: '', emergency_contact: '', emergency_phone: '', bank_card_no: '', department: null, position: '', entry_date: '' })
const files = reactive({ id_card_front: [], id_card_back: [], diploma: [], bank_card_img: [], photo: [], resume: [] })

// 上传子组件（不自动上传，收集 raw 文件）
const UploadImg = {
  props: { model: { type: Array, default: () => [] }, file: { type: [String, Object], default: '' } },
  setup(props) {
    const fileList = ref(Array.isArray(props.file) && props.file.length ? props.file : (props.file ? [{ name: '已上传', url: props.file }] : []))
    return () => h('el-upload', {
      listType: 'picture-card', limit: 1, 'auto-upload': false, 'file-list': fileList.value,
      onChange: (f, l) => { props.model.length = 0; if (l[0] && l[0].raw) props.model.push(l[0].raw) },
      onRemove: () => { props.model.length = 0 }
    }, { default: () => h('el-icon', {}, () => h(UploadFilled)) })
  }
}
const UploadFile = {
  props: { model: { type: Array, default: () => [] }, file: { type: [String, Object], default: '' } },
  setup(props) {
    const fileList = ref(props.file ? [{ name: '已上传简历', url: props.file }] : [])
    return () => h('el-upload', {
      limit: 1, 'auto-upload': false, 'file-list': fileList.value,
      onChange: (f, l) => { props.model.length = 0; if (l[0] && l[0].raw) props.model.push(l[0].raw) },
      onRemove: () => { props.model.length = 0 }
    }, { default: () => h('el-button', {}, () => '选择文件') })
  }
}

function next() {
  if (step.value === 0 && !form.name) return ElMessage.warning('请填写姓名')
  if (step.value === 0 && !/^1[3-9]\d{9}$/.test(form.phone)) return ElMessage.warning('手机号格式不正确')
  if (step.value === 0 && !/^\d{17}[\dXx]$/.test(form.id_card_no)) return ElMessage.warning('身份证号应为18位')
  step.value++
}
async function submit() {
  if (!form.department) return ElMessage.warning('请选择拟入职部门')
  if (!form.position) return ElMessage.warning('请填写拟任岗位')
  const fd = new FormData()
  for (const k in form) { if (form[k] !== '' && form[k] !== null) fd.append(k, form[k]) }
  for (const k in files) { if (files[k] && files[k].length) fd.append(k, files[k][0]) }
  submitting.value = true
  try {
    const r = await onboardingApi.submitProfile(fd)
    profile.value = (r && r.data) ? r.data : (r || null)
    if (profile.value && profile.value.status) profile.value.status_name = ({ DRAFT: '待提交', SUBMITTED: '待审核', APPROVED: '已通过', REJECTED: '已驳回' })[profile.value.status]
    ElMessage.success('已提交，等待审核')
    step.value = 0
  } catch (e) { ElMessage.error('提交失败，请检查必填项') } finally { submitting.value = false }
}

// HR 待审
const rvLoading = ref(false)
const pendings = ref([])
async function loadPendings() {
  if (!(user.isHR || user.isBoss)) return
  rvLoading.value = true
  try {
    const r = await onboardingApi.profiles({ status: 'SUBMITTED' })
    const list = (r.results) ? r.results : (Array.isArray(r) ? r : (r.data ? (r.data.results || r.data) : []))
    pendings.value = list
  } catch (e) {} finally { rvLoading.value = false }
}
async function review(row, action) {
  let remark = ''
  if (action === 'REJECT') {
    try { const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回', { inputType: 'textarea', required: true }); remark = value } catch { return }
  }
  try {
    await onboardingApi.reviewProfile(row.id, { action, remark })
    ElMessage.success(action === 'APPROVE' ? '已通过' : '已驳回')
    loadPendings()
  } catch (e) { ElMessage.error('操作失败') }
}

async function loadMine() {
  loading.value = true
  try {
    const r = await onboardingApi.myProfile()
    const p = (r && r.data !== undefined) ? r.data : r
    if (p) {
      profile.value = p
      for (const k in form) if (p[k] !== undefined) form[k] = p[k]
    }
  } catch (e) {} finally { loading.value = false }
}
async function loadDepts() { try { const r = await orgApi.departments({ page_size: 100 }); depts.value = (r.results) ? r.results : (r.data || []) } catch (e) {} }

onMounted(() => { loadDepts(); loadMine(); loadPendings() })
</script>

<style scoped>
.pf-steps { margin: 16px 0; }
.pf-form { max-width: 960px; margin-top: 8px; }
.pf-actions { margin-top: 18px; text-align: center; }
.pf-confirm { margin-bottom: 10px; }
.pf-file-tip { font-size: 12px; color: var(--text-sub); margin-top: 8px; }
.rej-hint { color: #d93026; font-weight: 600; }
</style>
