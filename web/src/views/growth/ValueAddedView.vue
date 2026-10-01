<template>
  <div class="value-added">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>增值业务部 · 独立项目台账（含合同上传）</span>
          <div>
            <el-button type="primary" @click="openCreate">+ 新建项目</el-button>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" class="filter-bar">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width:140px">
            <el-option v-for="s in statusOps" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" plain @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="list" v-loading="loading" border stripe size="default" max-height="560">
        <el-table-column prop="name" label="项目名称" min-width="140" />
        <el-table-column prop="customer_name" label="客户名称" width="120" />
        <el-table-column prop="project_type" label="业务类型" width="130" />
        <el-table-column prop="owner_name" label="负责人" width="100" />
        <el-table-column label="合同金额(元)" width="120">
          <template #default="{ row }"><span class="amt">{{ num(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column label="成本(元)" width="100">
          <template #default="{ row }">{{ num(row.cost) }}</template>
        </el-table-column>
        <el-table-column label="利润(元)" width="110">
          <template #default="{ row }"><span :class="row.profit>=0?'amt':'loss'">{{ num(row.profit) }}</span></template>
        </el-table-column>
        <el-table-column label="标签" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.is_renewal" type="warning" size="small">续费</el-tag>
            <el-tag v-if="row.is_visit" type="success" size="small" style="margin-left:4px">上门拜访</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ row.status_label }}</el-tag></template>
        </el-table-column>
        <el-table-column label="合同附件" width="100">
          <template #default="{ row }">
            <el-button v-if="row.contract_attachment" link type="primary" @click="openUrl(row.contract_attachment)">查看</el-button>
            <span v-else class="muted">未上传</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openUpload(row)">上传合同</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建项目 -->
    <el-dialog v-model="createVisible" title="新建增值业务项目" width="620px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="项目名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="客户名称"><el-input v-model="form.customer_name" /></el-form-item>
        <el-form-item label="业务类型"><el-input v-model="form.project_type" placeholder="如：高新认定 / 资质办理 / 税务筹划" /></el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="form.owner" placeholder="选择负责人" clearable style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="合同金额(元)"><el-input-number v-model="form.amount" :min="0" :precision="2" style="width:200px" /></el-form-item>
        <el-form-item label="成本(元)"><el-input-number v-model="form.cost" :min="0" :precision="2" style="width:200px" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width:160px">
            <el-option v-for="s in statusOps" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务场景">
          <el-checkbox v-model="form.is_renewal">续费业务</el-checkbox>
          <el-checkbox v-model="form.is_visit">客户上门拜访</el-checkbox>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">保存项目</el-button>
      </template>
    </el-dialog>

    <!-- 合同上传 -->
    <el-dialog v-model="uploadVisible" title="上传合同（PDF电子合同 / 扫描件）" width="520px">
      <template v-if="current">
        <p>项目：<strong>{{ current.name }}</strong></p>
        <el-upload :auto-upload="false" :show-file-list="false" :on-change="onFileChange" accept=".pdf,.jpg,.jpeg,.png">
          <el-button type="primary">选择合同文件</el-button>
        </el-upload>
        <p class="muted" style="margin-top:10px">
          说明：本地上传 PDF 电子合同 / 合同扫描件，预留后期对接第三方电子签章跳转能力。
        </p>
        <div v-if="uploading" v-loading="true" element-loading-text="上传中..." style="height:60px" />
      </template>
      <template #footer>
        <el-button @click="uploadVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { growthApi } from '@/api/growth'
import { orgApi } from '@/api/index'

const statusOps = [
  { label: '待启动', value: 'DRAFT' }, { label: '进行中', value: 'DOING' },
  { label: '已完成', value: 'DONE' }, { label: '已暂停', value: 'PAUSED' },
  { label: '已取消', value: 'CANCELED' }
]

const list = ref([])
const loading = ref(false)
const filters = reactive({ status: '' })
const users = ref([])

const createVisible = ref(false)
const uploadVisible = ref(false)
const submitting = ref(false)
const uploading = ref(false)
const current = ref(null)
const pendingFile = ref(null)

const form = reactive({
  name: '', customer_name: '', project_type: '', owner: null,
  amount: 0, cost: 0, status: 'DRAFT', is_renewal: false, is_visit: false, remark: ''
})

function num(v) { const n = Number(v || 0); return n ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '0' }
function statusType(s) {
  return { DRAFT: 'info', DOING: 'warning', DONE: 'success', PAUSED: 'primary', CANCELED: 'danger' }[s] || 'info'
}
function openUrl(u) { if (u) window.open(u, '_blank') }

async function loadUsers() {
  try { const r = await orgApi.users({ page_size: 200 }); users.value = Array.isArray(r) ? r : (r.results || []) } catch (e) {}
}
async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.status) params.status = filters.status
    const res = await growthApi.projects(params)
    list.value = Array.isArray(res) ? res : (res.results || [])
  } finally { loading.value = false }
}

function openCreate() {
  Object.assign(form, { name: '', customer_name: '', project_type: '', owner: null,
    amount: 0, cost: 0, status: 'DRAFT', is_renewal: false, is_visit: false, remark: '' })
  createVisible.value = true
}
async function submitCreate() {
  if (!form.name) return ElMessage.warning('请填写项目名称')
  submitting.value = true
  try {
    await growthApi.createProject({ ...form })
    ElMessage.success('已保存')
    createVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

function openUpload(row) { current.value = row; uploadVisible.value = true; pendingFile.value = null }
function onFileChange(file) { pendingFile.value = file.raw; doUpload() }
async function doUpload() {
  if (!pendingFile.value || !current.value) return
  uploading.value = true
  try {
    await growthApi.uploadVaContract(current.value.id, pendingFile.value)
    ElMessage.success('合同已上传')
    uploadVisible.value = false
    loadData()
  } catch (e) {} finally { uploading.value = false; pendingFile.value = null }
}

onMounted(() => { loadUsers(); loadData() })
</script>

<style scoped>
.value-added { padding: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { margin-bottom: 8px; }
.amt { color: #67c23a; font-weight: 600; }
.loss { color: #f56c6c; font-weight: 600; }
.muted { color: #909399; }
</style>
