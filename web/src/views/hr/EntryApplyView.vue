<template>
  <div class="entry-apply">
    <el-card shadow="never" style="max-width:760px;margin:0 auto">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span>入职申请 · 提交个人资料</span>
          <el-button v-if="isPublic" link type="primary" @click="$router.push('/login')">返回登录 →</el-button>
        </div>
      </template>
      <el-alert type="info" :closable="false" show-icon
        title="提交后由人事管理员审核；审核通过后，用你的手机号 + 自设密码即可登录系统" style="margin-bottom:16px" />
      <el-form :model="form" label-width="120px" ref="formRef">
        <el-form-item label="申请人姓名" required><el-input v-model="form.applicant_name" /></el-form-item>
        <el-form-item label="联系电话" required><el-input v-model="form.phone" placeholder="审核通过后作为登录账号" /></el-form-item>
        <el-form-item label="登录密码" required>
          <el-input v-model="form.password" type="password" show-password placeholder="8-64 位，审核通过后用它登录系统" />
        </el-form-item>
        <el-form-item label="确认密码" required>
          <el-input v-model="form.password2" type="password" show-password placeholder="再输入一次密码" />
        </el-form-item>
        <el-form-item label="身份证号"><el-input v-model="form.id_card_no" /></el-form-item>
        <el-form-item label="意向部门" required>
          <el-select v-model="form.proposed_department" placeholder="选择部门" style="width:100%">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="意向岗位">
          <el-select v-model="form.proposed_position" placeholder="选择岗位（可选）" clearable style="width:100%">
            <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="期望薪资(元/月)"><el-input-number v-model="form.expected_salary" :min="0" :precision="2" style="width:220px" /></el-form-item>
        <el-form-item label="简历 / 资料">
          <el-upload :auto-upload="false" :show-file-list="true" :on-change="onFileChange" :limit="1">
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" /></el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="submit">提交入职申请</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { orgApi } from '@/api/index'

const route = useRoute()
const isPublic = route.path === '/apply'

const departments = ref([])
const positions = ref([])
const submitting = ref(false)
const pendingFile = ref(null)
const form = reactive({
  applicant_name: '', phone: '', id_card_no: '', proposed_department: null,
  proposed_position: null, expected_salary: 0, remark: '', password: '', password2: ''
})

function onFileChange(file) { pendingFile.value = file.raw }

async function loadDepts() {
  try { const r = await orgApi.departments(); departments.value = Array.isArray(r) ? r : (r.results || []) } catch (e) {}
  try { const r = await orgApi.positions(); positions.value = Array.isArray(r) ? r : (r.results || []) } catch (e) {}
}

async function submit() {
  if (!form.applicant_name) return ElMessage.warning('请填写申请人姓名')
  if (!form.phone || !/^1\d{10}$/.test(form.phone.trim())) return ElMessage.warning('请填写正确的 11 位手机号（将作为登录账号）')
  if (!form.proposed_department) return ElMessage.warning('请选择意向部门')
  if (form.password.length < 8) return ElMessage.warning('登录密码至少 8 位')
  if (form.password !== form.password2) return ElMessage.warning('两次输入的密码不一致')
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('applicant_name', form.applicant_name)
    fd.append('phone', form.phone || '')
    fd.append('password', form.password)
    fd.append('id_card_no', form.id_card_no || '')
    fd.append('proposed_department', String(form.proposed_department))
    if (form.proposed_position) fd.append('proposed_position', String(form.proposed_position))
    fd.append('expected_salary', String(form.expected_salary || 0))
    fd.append('remark', form.remark || '')
    if (pendingFile.value) fd.append('resume', pendingFile.value)
    // 直接走底层 http（multipart）
    const http = (await import('@/api/index')).default
    await http.post('/accounts/entries/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success('入职申请已提交，等待人事审核；通过后用手机号 + 自设密码登录')
    pendingFile.value = null
    Object.assign(form, { applicant_name: '', phone: '', id_card_no: '', proposed_department: null, proposed_position: null, expected_salary: 0, remark: '', password: '', password2: '' })
  } catch (e) {} finally { submitting.value = false }
}

onMounted(loadDepts)
</script>

<style scoped>
.entry-apply { padding: 8px 4px; }
</style>
