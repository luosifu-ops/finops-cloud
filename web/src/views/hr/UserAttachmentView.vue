<template>
  <div class="ua">
    <div class="bl-head">
      <h2 class="bl-title">员工证件 / 材料附件</h2>
      <el-button type="primary" @click="openCreate">上 传 附 件</el-button>
    </div>
    <el-table :data="list" v-loading="loading" border stripe style="width:100%">
      <el-table-column prop="user_name" label="员工" width="110" />
      <el-table-column prop="category_name" label="材料类别" width="130" />
      <el-table-column prop="remark" label="说明" min-width="160" show-overflow-tooltip />
      <el-table-column label="附件" min-width="120">
        <template #default="{ row }">
          <a v-if="row.file" :href="row.file" target="_blank" style="color:#409eff">查看</a>
          <span v-else style="color:#909399">无</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="visible" title="上传员工材料附件" width="560px" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-form-item label="员工" required>
          <PersonSelect v-model="form.user" placeholder="选择员工" />
        </el-form-item>
        <el-form-item label="材料类别">
          <el-select v-model="form.category" style="width:100%">
            <el-option value="ID_CARD" label="身份证件" />
            <el-option value="EDUCATION" label="学历证明" />
            <el-option value="CONTRACT" label="劳动合同" />
            <el-option value="BANK" label="银行卡" />
            <el-option value="PHOTO" label="证件照" />
            <el-option value="OTHER" label="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="附件" required>
          <el-upload :auto-upload="false" :show-file-list="true" :on-change="onFile" :limit="1">
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="form.remark" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">上 传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api'
import PersonSelect from '@/components/PersonSelect.vue'

const list = ref([])
const users = ref([])
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const pendingFile = ref(null)
const form = ref({ user: null, category: 'ID_CARD', remark: '' })

async function loadUsers() {
  try { const r = await http.get('/accounts/users/', { params: { page_size: 500 } }); users.value = r?.results || [] } catch (e) {}
}
async function reload() {
  loading.value = true
  try {
    const r = await http.get('/hr/user-attachments/', { params: { page_size: 300 } })
    const body = r || {}
    list.value = body.results || (Array.isArray(body) ? body : (body.data?.results || []))
  } catch (e) {} finally { loading.value = false }
}
function resetForm() { form.value = { user: null, category: 'ID_CARD', remark: '' }; pendingFile.value = null }
function openCreate() { resetForm(); visible.value = true }
function onFile(file) { pendingFile.value = file.raw }
async function submit() {
  if (!form.value.user) return ElMessage.warning('请选择员工')
  if (!pendingFile.value) return ElMessage.warning('请选择附件文件')
  saving.value = true
  try {
    const fd = new FormData()
    fd.append('user', String(form.value.user))
    fd.append('category', form.value.category)
    fd.append('remark', form.value.remark || '')
    fd.append('file', pendingFile.value)
    await http.post('/hr/user-attachments/', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success('附件已上传')
    visible.value = false
    reload()
  } catch (e) { ElMessage.error('上传失败') } finally { saving.value = false }
}
async function remove(row) {
  try { await ElMessageBox.confirm('确认删除该附件？', '提示', { type: 'warning' }) } catch { return }
  try { await http.delete(`/hr/user-attachments/${row.id}/`); ElMessage.success('已删除'); reload() } catch (e) {}
}
onMounted(() => { loadUsers(); reload() })
</script>

<style scoped>
.ua { padding: 4px; }
.bl-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.bl-title { font-size:18px; margin:0; }
</style>
