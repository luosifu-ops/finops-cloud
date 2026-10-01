<template>
  <div class="lc">
    <el-alert v-if="expiring.length" type="warning" :closable="false" show-icon
      :title="`合同到期预警：近 30 天内有 ${expiring.length} 份劳动合同即将到期`" style="margin-bottom:12px" />
    <div class="bl-head">
      <h2 class="bl-title">劳动合同台账</h2>
      <div class="bl-tools">
        <el-button @click="loadExpiring">刷新到期预警</el-button>
        <el-button type="primary" @click="openCreate">新 增 合 同</el-button>
      </div>
    </div>

    <el-table :data="list" v-loading="loading" border stripe style="width:100%">
      <el-table-column prop="user_name" label="员工" width="110" />
      <el-table-column prop="type_name" label="类型" width="120" />
      <el-table-column prop="contract_no" label="合同编号" width="150" />
      <el-table-column prop="start_date" label="起始" width="120" />
      <el-table-column prop="end_date" label="终止" width="120" />
      <el-table-column prop="status_name" label="状态" width="100" />
      <el-table-column prop="is_renewal" label="续签" width="70">
        <template #default="{ row }">{{ row.is_renewal ? '是' : '否' }}</template>
      </el-table-column>
      <el-table-column label="附件" min-width="120">
        <template #default="{ row }">
          <a v-if="row.attachment" :href="row.attachment" target="_blank" style="color:#409eff">查看</a>
          <span v-else style="color:#909399">无</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status==='ACTIVE'" link type="primary" @click="renew(row)">续签</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" title="新增劳动合同" width="600px" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-form-item label="员工" required>
          <el-select v-model="form.user" filterable placeholder="选择员工" style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.display_name||u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="合同类型">
          <el-select v-model="form.contract_type" style="width:100%">
            <el-option value="FULLTIME" label="劳动合同" />
            <el-option value="INTERN" label="实习协议" />
            <el-option value="PARTTIME" label="劳务协议" />
          </el-select>
        </el-form-item>
        <el-form-item label="合同编号"><el-input v-model="form.contract_no" /></el-form-item>
        <el-form-item label="签订日期"><el-date-picker v-model="form.signed_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="合同起始"><el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="合同终止"><el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="合同附件">
          <el-upload :auto-upload="false" :show-file-list="true" :on-change="onFile" :limit="1">
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api'

const list = ref([])
const users = ref([])
const expiring = ref([])
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const pendingFile = ref(null)
const form = ref({ user: null, contract_type: 'FULLTIME', contract_no: '', signed_date: '', start_date: '', end_date: '', remark: '' })

async function loadUsers() {
  try { const r = await http.get('/accounts/users/', { params: { page_size: 500 } }); users.value = r?.results || [] } catch (e) {}
}
async function reload() {
  loading.value = true
  try {
    const r = await http.get('/hr/labor-contracts/', { params: { page_size: 300 } })
    const body = r || {}
    list.value = body.results || (Array.isArray(body) ? body : (body.data?.results || []))
  } catch (e) {} finally { loading.value = false }
}
async function loadExpiring() {
  try { const r = await http.get('/hr/labor-contracts/expiring/', { params: { days: 30 } }); const b = r?.data || r; expiring.value = Array.isArray(b) ? b : (b?.results || []) } catch (e) {}
}
function resetForm() { form.value = { user: null, contract_type: 'FULLTIME', contract_no: '', signed_date: '', start_date: '', end_date: '', remark: '' }; pendingFile.value = null }
function openCreate() { resetForm(); visible.value = true }
function onFile(file) { pendingFile.value = file.raw }
async function submit() {
  if (!form.value.user) return ElMessage.warning('请选择员工')
  saving.value = true
  try {
    const fd = new FormData()
    for (const k in form.value) fd.append(k, form.value[k] ?? '')
    if (pendingFile.value) fd.append('attachment', pendingFile.value)
    await http.post('/hr/labor-contracts/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success('合同已登记')
    visible.value = false
    reload(); loadExpiring()
  } catch (e) { ElMessage.error('保存失败') } finally { saving.value = false }
}
async function renew(row) {
  try {
    await http.post(`/hr/labor-contracts/${row.id}/renew/`)
    ElMessage.success('已生成续签合同')
    reload()
  } catch (e) { ElMessage.error('续签失败') }
}
async function remove(row) {
  try { await ElMessageBox.confirm('确认删除该合同记录？', '提示', { type: 'warning' }) } catch { return }
  try { await http.delete(`/hr/labor-contracts/${row.id}/`); ElMessage.success('已删除'); reload() } catch (e) {}
}
onMounted(() => { loadUsers(); reload(); loadExpiring() })
</script>

<style scoped>
.lc { padding: 4px; }
.bl-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.bl-title { font-size:18px; margin:0; }
.bl-tools { display:flex; gap:8px; }
</style>
