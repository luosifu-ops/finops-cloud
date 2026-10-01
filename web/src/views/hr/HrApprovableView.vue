<template>
  <div class="approvable">
    <div class="bl-head">
      <h2 class="bl-title">{{ title }}</h2>
      <div class="bl-tools">
        <el-button v-if="formFields.length" type="primary" @click="openCreate">新 增</el-button>
      </div>
    </div>

    <el-table :data="list" v-loading="loading" border stripe style="width:100%">
      <el-table-column v-for="c in columns" :key="c.prop" :prop="c.prop" :label="c.label"
        :width="c.width" :min-width="c.minWidth || 110" show-overflow-tooltip />
      <el-table-column label="操作" :width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'PENDING' || row.status_name === '审批中'"
            link type="primary" @click="openApprove(row, 'approve')">通过</el-button>
          <el-button v-if="row.status === 'PENDING' || row.status_name === '审批中'"
            link type="danger" @click="openApprove(row, 'reject')">驳回</el-button>
          <span v-else type="info" style="color:#909399">已{{ row.status_name }}</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createVisible" :title="'新增' + title" width="560px" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-form-item v-for="f in formFields" :key="f.prop" :label="f.label" :required="f.required">
          <el-input v-if="f.type==='text'||f.type==='textarea'" v-model="form[f.prop]"
            :type="f.type==='textarea'?'textarea':''" :rows="3" />
          <el-input-number v-else-if="f.type==='number'" v-model="form[f.prop]" :min="0" style="width:100%" />
          <el-date-picker v-else-if="f.type==='date'" v-model="form[f.prop]" type="date" value-format="YYYY-MM-DD" style="width:100%" />
          <el-select v-else-if="f.type==='select'" v-model="form[f.prop]" clearable style="width:100%">
            <el-option v-for="o in f.options" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">保 存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="approveVisible" :title="approveAct==='approve'?'审批通过':'审批驳回'" width="460px">
      <p>单号 #{{ current?.id }} · {{ current?.user_name || '' }}</p>
      <el-input v-model="approveRemark" type="textarea" :rows="3" placeholder="审批意见（可选）" />
      <template #footer>
        <el-button @click="approveVisible=false">取消</el-button>
        <el-button :type="approveAct==='approve'?'primary':'danger'" :loading="saving" @click="submitApprove">确认{{ approveAct==='approve'?'通过':'驳回' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api'

const props = defineProps({
  title: { type: String, default: '' },
  baseUrl: { type: String, required: true },
  columns: { type: Array, default: () => [] },
  formFields: { type: Array, default: () => [] },
  depends: { type: Object, default: () => ({}) },
})

const list = ref([])
const loading = ref(false)
const createVisible = ref(false)
const approveVisible = ref(false)
const approveAct = ref('approve')
const current = ref(null)
const approveRemark = ref('')
const saving = ref(false)
const form = reactive({})
const optionMap = ref({})

function pickLabel(it) { return it.display_name || it.name || it.username || it.title || ('#' + it.id) }

async function loadDepends() {
  for (const field in props.depends) {
    try {
      const r = await http.get(props.depends[field], { params: { page_size: 500 } })
      const data = r?.results || (Array.isArray(r) ? r : (r?.data?.results || []))
      optionMap.value[field] = (data || []).map(it => ({ value: it.id, label: pickLabel(it) }))
    } catch (e) { optionMap.value[field] = [] }
  }
}
const resolvedFormFields = computed(() => props.formFields.map(f =>
  f.depends ? { ...f, type: 'select', options: optionMap.value[f.depends] || [] } : f))

async function reload() {
  loading.value = true
  try {
    const resp = await http.get(props.baseUrl, { params: { page_size: 200 } })
    const body = resp || {}
    let payload = body
    if (body && typeof body === 'object' && 'code' in body && 'data' in body) payload = body.data
    if (payload && payload.results) list.value = payload.results
    else if (Array.isArray(payload)) list.value = payload
    else list.value = []
  } catch (e) {} finally { loading.value = false }
}

function resetForm() { for (const k in form) delete form[k] }
function openCreate() {
  resetForm()
  for (const f of props.formFields) form[f.prop] = f.type === 'number' ? 0 : ''
  createVisible.value = true
}
async function submitCreate() {
  saving.value = true
  try {
    await http.post(props.baseUrl, { ...form })
    ElMessage.success('已提交')
    createVisible.value = false
    reload()
  } catch (e) { ElMessage.error('提交失败，请检查字段') } finally { saving.value = false }
}

function openApprove(row, act) { current.value = row; approveAct.value = act; approveRemark.value = ''; approveVisible.value = true }
async function submitApprove() {
  if (!current.value) return
  saving.value = true
  try {
    await http.post(`${props.baseUrl}${current.value.id}/approve/`, { action: approveAct.value, remark: approveRemark.value })
    ElMessage.success(approveAct.value === 'approve' ? '已通过' : '已驳回')
    approveVisible.value = false
    reload()
  } catch (e) { ElMessage.error('操作失败') } finally { saving.value = false }
}

onMounted(() => { loadDepends(); reload() })
</script>

<style scoped>
.approvable { padding: 4px; }
.bl-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.bl-title { font-size:18px; margin:0; }
.bl-tools { display:flex; gap:8px; }
</style>
