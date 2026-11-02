<template>
  <div class="cus-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">客户档案</h2>
        <span class="page-tip">客户分层运营：等级 + 自定义标签，可按标签快速筛选</span>
      </div>
      <div class="head-btns">
        <el-button @click="tagBox = true">标签管理</el-button>
        <el-button type="primary" @click="openCreate">+ 新增客户</el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" size="default">
        <el-form-item label="关键字">
          <el-input v-model="filters.keyword" placeholder="客户名称 / 联系人 / 电话" clearable
            style="width:220px" @keyup.enter="load" @clear="load" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="filters.tag" placeholder="全部标签" clearable style="width:160px" @change="load">
            <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级">
          <el-select v-model="filters.level" placeholder="全部" clearable style="width:110px" @change="load">
            <el-option label="A级" value="A" /><el-option label="B级" value="B" />
            <el-option label="C级" value="C" /><el-option label="D级" value="D" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width:120px" @change="load">
            <el-option label="合作中" value="COOPERATING" /><el-option label="暂停" value="PAUSED" />
            <el-option label="已流失" value="CHURNED" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="load">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column prop="name" label="客户名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="customer_type_name" label="类型" width="100" />
        <el-table-column prop="contact" label="联系人" width="100" />
        <el-table-column prop="phone" label="电话" width="130" />
        <el-table-column label="等级" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="dark" :type="levelType(row.level)">{{ row.level || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="t in (row.tags_info || [])" :key="t.id" size="small"
              :type="t.color" effect="plain" class="cus-tag">{{ t.name }}</el-tag>
            <span v-if="!(row.tags_info || []).length" class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="owner_name" label="归属销售" width="110" />
        <el-table-column prop="status_name" label="状态" width="100" />
        <el-table-column prop="expire_at" label="服务到期" width="120" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openTag(row)">打标签</el-button>
            <el-button link @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" @click="openTransfer(row)">转外勤</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination background layout="total, prev, pager, next" :total="total"
          :page-size="pageSize" :current-page="page" @current-change="onPage" />
      </div>
    </el-card>

    <!-- 新增/编辑客户 -->
    <el-dialog v-model="boxVisible" :title="editingId ? '编辑客户' : '新增客户'" width="720px" @closed="resetForm">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="客户名称" required>
            <el-input v-model="form.name" maxlength="200" />
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="简称">
            <el-input v-model="form.short_name" maxlength="100" />
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="客户类型">
            <el-select v-model="form.customer_type" style="width:100%">
              <el-option label="企业" value="ENTERPRISE" />
              <el-option label="个体工商户" value="INDIVIDUAL" />
              <el-option label="个人" value="PERSONAL" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系人">
            <el-input v-model="form.contact" maxlength="50" />
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="联系电话">
            <el-input v-model="form.phone" maxlength="30" />
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="微信">
            <el-input v-model="form.wechat" maxlength="60" />
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="信用代码">
            <el-input v-model="form.credit_code" maxlength="50" />
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="所属行业">
            <el-input v-model="form.industry" maxlength="100" />
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="所属区域">
            <el-input v-model="form.region" maxlength="100" />
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="客户等级">
            <el-select v-model="form.level" style="width:100%">
              <el-option label="A级" value="A" /><el-option label="B级" value="B" />
              <el-option label="C级" value="C" /><el-option label="D级" value="D" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="状态">
            <el-select v-model="form.status" style="width:100%">
              <el-option label="合作中" value="COOPERATING" /><el-option label="暂停" value="PAUSED" />
              <el-option label="已流失" value="CHURNED" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="归属销售">
            <el-select v-model="form.owner" filterable clearable style="width:100%">
              <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="主办会计">
            <el-select v-model="form.accountant" filterable clearable style="width:100%">
              <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="签约日期">
            <el-date-picker v-model="form.signed_at" type="date" value-format="YYYY-MM-DD" style="width:100%" />
          </el-form-item></el-col>
          <el-col :span="12"><el-form-item label="服务到期">
            <el-date-picker v-model="form.expire_at" type="date" value-format="YYYY-MM-DD" style="width:100%" />
          </el-form-item></el-col>
          <el-col :span="24"><el-form-item label="客户标签">
            <el-select v-model="form.tags" multiple filterable clearable style="width:100%"
              placeholder="选择标签（可在标签管理中维护）">
              <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </el-form-item></el-col>
          <el-col :span="24"><el-form-item label="地址">
            <el-input v-model="form.address" maxlength="300" />
          </el-form-item></el-col>
          <el-col :span="24"><el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="2" />
          </el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="boxVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 打标签 -->
    <el-dialog v-model="tagPickVisible" :title="`打标签 · ${tagRow?.name || ''}`" width="480px">
      <el-select v-model="tagPickIds" multiple filterable clearable style="width:100%"
        placeholder="选择标签，可多选">
        <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
      </el-select>
      <div class="tag-tip">标签在「标签管理」中维护；保存后立即在列表以彩色标签展示，并可用于筛选。</div>
      <template #footer>
        <el-button @click="tagPickVisible = false">取消</el-button>
        <el-button type="primary" :loading="tagSaving" @click="saveTags">保存</el-button>
      </template>
    </el-dialog>

    <!-- 标签管理 -->
    <el-dialog v-model="tagBox" title="标签管理" width="620px">
      <div class="tag-add">
        <el-input v-model="newTag.name" placeholder="标签名称（如 重点客户）" style="width:180px" maxlength="30" />
        <el-select v-model="newTag.color" style="width:120px">
          <el-option label="蓝(主色)" value="primary" /><el-option label="绿(成功)" value="success" />
          <el-option label="橙(警示)" value="warning" /><el-option label="红(危险)" value="danger" />
          <el-option label="灰(信息)" value="info" />
        </el-select>
        <el-button type="primary" @click="addTag">添加标签</el-button>
      </div>
      <el-table :data="tags" border size="small" style="margin-top:12px">
        <el-table-column label="标签" min-width="140">
          <template #default="{ row }">
            <el-tag :type="row.color" effect="plain">{{ row.name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="customer_count" label="客户数" width="90" align="center" />
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button link type="primary" @click="renameTag(row)">改名</el-button>
            <el-button link :type="row.is_active ? 'warning' : 'success'" @click="toggleTag(row)">
              {{ row.is_active ? '停用' : '启用' }}
            </el-button>
            <el-button link type="danger" @click="deleteTag(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button type="primary" @click="tagBox = false">完成</el-button>
      </template>
    </el-dialog>

    <FieldTransferDialog
      v-model="transferVisible"
      :customer-name="transferRow.name"
      :source-order-no="transferRow.customer_no"
      source-type="客户"
      @transferred="load"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '@/api'
import FieldTransferDialog from '@/components/FieldTransferDialog.vue'

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const users = ref([])
const tags = ref([])

const filters = reactive({ keyword: '', tag: null, level: '', status: '' })

const boxVisible = ref(false)
const saving = ref(false)
const editingId = ref(null)
const emptyForm = {
  name: '', short_name: '', customer_type: 'ENTERPRISE', contact: '', phone: '', wechat: '',
  credit_code: '', industry: '', region: '', address: '', level: 'C', status: 'COOPERATING',
  owner: null, accountant: null, signed_at: null, expire_at: null, tags: [], remark: ''
}
const form = reactive({ ...emptyForm })

const tagPickVisible = ref(false)
const tagPickIds = ref([])
const tagSaving = ref(false)
const tagRow = ref(null)

const tagBox = ref(false)
const newTag = reactive({ name: '', color: 'primary' })

const transferVisible = ref(false)
const transferRow = reactive({ name: '', customer_no: '' })

const levelType = (lv) => ({ A: 'danger', B: 'warning', C: 'primary', D: 'info' }[lv] || 'info')

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (filters.keyword) params.search = filters.keyword
    if (filters.tag) params.tag = filters.tag
    if (filters.level) params.level = filters.level
    if (filters.status) params.status = filters.status
    const r = await http.get('/sales/customers/', { params })
    list.value = r?.results || r?.data?.results || (Array.isArray(r) ? r : [])
    total.value = r?.count || r?.data?.count || list.value.length
  } catch (e) { /* 拦截器已提示 */ } finally { loading.value = false }
}
function onPage(p) { page.value = p; load() }

async function loadRefs() {
  try {
    const r = await http.get('/accounts/users/', { params: { page_size: 500 } })
    users.value = r?.results || (Array.isArray(r) ? r : [])
  } catch (e) { users.value = [] }
  await loadTags()
}
async function loadTags() {
  try {
    const r = await http.get('/sales/customer-tags/', { params: { page_size: 100 } })
    tags.value = r?.results || (Array.isArray(r) ? r : [])
  } catch (e) { tags.value = [] }
}

function resetForm() {
  editingId.value = null
  Object.assign(form, { ...emptyForm, tags: [] })
}
function openCreate() { resetForm(); boxVisible.value = true }
function openEdit(row) {
  resetForm()
  editingId.value = row.id
  Object.assign(form, {
    name: row.name || '', short_name: row.short_name || '', customer_type: row.customer_type || 'ENTERPRISE',
    contact: row.contact || '', phone: row.phone || '', wechat: row.wechat || '',
    credit_code: row.credit_code || '', industry: row.industry || '', region: row.region || '',
    address: row.address || '', level: row.level || 'C', status: row.status || 'COOPERATING',
    owner: row.owner || null, accountant: row.accountant || null,
    signed_at: row.signed_at || null, expire_at: row.expire_at || null,
    tags: (row.tags || []), remark: row.remark || ''
  })
  boxVisible.value = true
}
async function save() {
  if (!form.name.trim()) return ElMessage.warning('请填写客户名称')
  saving.value = true
  try {
    if (editingId.value) {
      await http.patch(`/sales/customers/${editingId.value}/`, { ...form })
      ElMessage.success('已保存')
    } else {
      await http.post('/sales/customers/', { ...form })
      ElMessage.success('客户已创建')
    }
    boxVisible.value = false
    load()
  } catch (e) { /* 拦截器已提示 */ } finally { saving.value = false }
}
async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除客户「${row.name}」？`, '删除客户', { type: 'warning' })
  } catch { return }
  try {
    await http.delete(`/sales/customers/${row.id}/`)
    ElMessage.success('已删除')
    load()
  } catch (e) { /* 拦截器已提示 */ }
}

// —— 打标签 ——
function openTag(row) {
  tagRow.value = row
  tagPickIds.value = (row.tags_info || []).map((t) => t.id)
  tagPickVisible.value = true
}
async function saveTags() {
  tagSaving.value = true
  try {
    await http.patch(`/sales/customers/${tagRow.value.id}/`, { tags: tagPickIds.value })
    ElMessage.success('标签已更新')
    tagPickVisible.value = false
    load()
  } catch (e) { /* 拦截器已提示 */ } finally { tagSaving.value = false }
}

// —— 标签管理 ——
async function addTag() {
  if (!newTag.name.trim()) return ElMessage.warning('请填写标签名称')
  try {
    await http.post('/sales/customer-tags/', { name: newTag.name.trim(), color: newTag.color })
    ElMessage.success('已添加')
    newTag.name = ''
    loadTags()
  } catch (e) { /* 拦截器已提示 */ }
}
async function renameTag(row) {
  const r = await ElMessageBox.prompt('新的标签名称', '修改标签名', { inputValue: row.name }).catch(() => null)
  if (!r || !r.value) return
  try {
    await http.patch(`/sales/customer-tags/${row.id}/`, { name: r.value.trim() })
    ElMessage.success('已修改')
    loadTags()
  } catch (e) { /* 拦截器已提示 */ }
}
async function toggleTag(row) {
  try {
    await http.patch(`/sales/customer-tags/${row.id}/`, { is_active: !row.is_active })
    loadTags()
  } catch (e) { /* 拦截器已提示 */ }
}
async function deleteTag(row) {
  try {
    await ElMessageBox.confirm(`删除标签「${row.name}」？已打此标签的客户会同步解除。`, '删除标签', { type: 'warning' })
  } catch { return }
  try {
    await http.delete(`/sales/customer-tags/${row.id}/`)
    ElMessage.success('已删除')
    loadTags()
    load()
  } catch (e) { /* 拦截器已提示 */ }
}

// —— 转外勤（保留原能力）——
function openTransfer(row) {
  transferRow.name = row.name || ''
  transferRow.customer_no = row.customer_no || row.code || ''
  transferVisible.value = true
}

onMounted(() => { load(); loadRefs() })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.page-title { font-size: 18px; margin: 0; }
.page-tip { font-size: 12px; color: var(--text-sub); font-weight: 400; }
.head-btns { display: flex; gap: 8px; }
.filter-card { margin-bottom: 14px; }
.filter-card :deep(.el-form-item) { margin-bottom: 0; }
.cus-tag { margin-right: 4px; margin-bottom: 2px; }
.muted { color: #909399; }
.pager { margin-top: 14px; display: flex; justify-content: flex-end; }
.tag-add { display: flex; gap: 8px; }
.tag-tip { font-size: 12px; color: var(--text-sub); margin-top: 8px; }
</style>
