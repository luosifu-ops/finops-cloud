<template>
  <div class="contracts">
    <el-row :gutter="16" class="stat-row">
      <el-col :span="8">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">{{ deptLabel }}合同数</div>
          <div class="mini-value">{{ total }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">签单总额(元)</div>
          <div class="mini-value ok">{{ amountSum.toLocaleString() }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">平均客单价(元)</div>
          <div class="mini-value">{{ avg.toLocaleString() }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ deptLabel }} · 合同订单名录</span>
          <div>
            <el-button type="primary" @click="openCreate">+ 录入合同</el-button>
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
        <el-form-item label="企业名称">
          <el-input v-model="filters.kw" placeholder="企业名称 / 税号" clearable style="width:200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" plain @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="list" v-loading="loading" border stripe size="default" max-height="540">
        <el-table-column prop="company_name" label="企业名称" min-width="150" />
        <el-table-column prop="credit_code" label="企业税号" width="150" />
        <el-table-column prop="service_content" label="服务内容" min-width="120" />
        <el-table-column prop="service_period" label="服务周期" width="130" />
        <el-table-column label="签单金额(元)" width="120">
          <template #default="{ row }"><span class="amt">{{ num(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column prop="signed_date" label="签单日期" width="120" />
        <el-table-column prop="recv_account" label="收款账户" min-width="120" show-overflow-tooltip />
        <el-table-column prop="signer_name" label="签单人" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="statusType(row.status)" size="small">{{ row.status_label }}</el-tag></template>
        </el-table-column>
        <el-table-column label="附件" width="90">
          <template #default="{ row }">
            <el-badge :value="row.files?.length || 0" :hidden="!(row.files && row.files.length)">
              <el-button link type="primary" @click="openFiles(row)">查看</el-button>
            </el-badge>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openFiles(row)">附件管理</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 录入合同 -->
    <el-dialog v-model="createVisible" :title="'录入' + deptLabel + '合同'" width="640px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="归属部门">
          <el-radio-group v-model="form.dept">
            <el-radio-button label="SALES">电销部</el-radio-button>
            <el-radio-button label="OPS">运营部</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="企业名称" required><el-input v-model="form.company_name" /></el-form-item>
        <el-form-item label="企业税号"><el-input v-model="form.credit_code" placeholder="统一社会信用代码" /></el-form-item>
        <el-form-item label="服务内容"><el-input v-model="form.service_content" placeholder="如：公司注册 / 代理记账 / 注销" /></el-form-item>
        <el-form-item label="服务周期"><el-input v-model="form.service_period" placeholder="如：2026-09 至 2027-08" /></el-form-item>
        <el-form-item label="签单金额(元)" required>
          <el-input-number v-model="form.amount" :min="0" :precision="2" style="width:200px" />
        </el-form-item>
        <el-form-item label="签单日期"><el-date-picker v-model="form.signed_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" /></el-form-item>
        <el-form-item label="收款账户"><el-input v-model="form.recv_account" placeholder="对公 / 对私收款账户" /></el-form-item>
        <el-form-item label="客户联系电话"><el-input v-model="form.customer_phone" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width:160px">
            <el-option v-for="s in statusOps" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">保存合同</el-button>
      </template>
    </el-dialog>

    <!-- 附件管理 -->
    <el-dialog v-model="fileVisible" title="合同附件管理（收款截图 / 合同扫描件 / PDF）" width="680px">
      <template v-if="current">
        <el-alert type="info" :closable="false" show-icon
          title="支持本地上传 PDF 电子合同 / 合同扫描件 / 收款截图；预留后期对接第三方电子签章跳转" style="margin-bottom:12px" />
        <el-upload
          :auto-upload="false" :show-file-list="false" :on-change="onFileChange" accept=".pdf,.jpg,.jpeg,.png">
          <el-button type="primary">选择文件上传</el-button>
        </el-upload>
        <el-form :inline="true" style="margin-top:10px">
          <el-form-item label="附件类型">
            <el-select v-model="uploadType" style="width:160px">
              <el-option label="收款截图" value="RECEIPT" />
              <el-option label="合同扫描件" value="SCAN" />
              <el-option label="PDF电子合同" value="PDF" />
            </el-select>
          </el-form-item>
        </el-form>
        <el-divider />
        <el-table :data="fileList" v-loading="fileLoading" border size="small">
          <el-table-column label="类型" width="120">
            <template #default="{ row }"><el-tag size="small">{{ row.file_type_label }}</el-tag></template>
          </el-table-column>
          <el-table-column label="文件">
            <template #default="{ row }">
              <a :href="row.url" target="_blank" class="file-link">{{ row.url?.split('/').pop() || '文件' }}</a>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="danger" @click="delFile(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!fileList.length && !fileLoading" description="暂无附件，请上传" />
      </template>
      <template #footer>
        <el-button @click="fileVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { contractApi } from '@/api/contracts'
import { useUserStore } from '@/store/user'

const props = defineProps({ dept: { type: String, default: 'SALES' } })
const store = useUserStore()

const statusOps = [
  { label: '待付款', value: 'PENDING' }, { label: '已付款', value: 'PAID' },
  { label: '服务中', value: 'EXECUTING' }, { label: '已完成', value: 'FINISHED' },
  { label: '已作废', value: 'CANCELED' }
]
const deptLabel = computed(() => props.dept === 'OPS' ? '运营部' : '电销部')

const list = ref([])
const loading = ref(false)
const filters = reactive({ status: '', kw: '' })
const total = ref(0)

const createVisible = ref(false)
const submitting = ref(false)
const form = reactive({
  dept: props.dept, company_name: '', credit_code: '', service_content: '',
  service_period: '', amount: 0, signed_date: '', recv_account: '',
  customer_phone: '', status: 'PENDING', remark: ''
})

const fileVisible = ref(false)
const current = ref(null)
const fileList = ref([])
const fileLoading = ref(false)
const uploadType = ref('PDF')
const pendingFile = ref(null)

const amountSum = computed(() => list.value.reduce((s, r) => s + Number(r.amount || 0), 0))
const avg = computed(() => total.value ? Math.round(amountSum.value / total.value) : 0)

function num(v) { const n = Number(v || 0); return n ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '0' }
function statusType(s) {
  return { PENDING: 'info', PAID: 'primary', EXECUTING: 'warning', FINISHED: 'success', CANCELED: 'danger' }[s] || 'info'
}

async function loadData() {
  loading.value = true
  try {
    const params = { dept: props.dept }
    if (filters.status) params.status = filters.status
    if (filters.kw) params.search = filters.kw
    const res = await contractApi.records(params)
    list.value = Array.isArray(res) ? res : (res.results || [])
    total.value = list.value.length
  } finally { loading.value = false }
}

function openCreate() {
  Object.assign(form, {
    dept: props.dept, company_name: '', credit_code: '', service_content: '',
    service_period: '', amount: 0, signed_date: '', recv_account: '',
    customer_phone: '', status: 'PENDING', remark: ''
  })
  createVisible.value = true
}
async function submitCreate() {
  if (!form.company_name) return ElMessage.warning('请填写企业名称')
  if (!form.amount) return ElMessage.warning('请填写签单金额')
  submitting.value = true
  try {
    await contractApi.create({ ...form })
    ElMessage.success('合同已保存')
    createVisible.value = false
    loadData()
  } finally { submitting.value = false }
}

async function openFiles(row) {
  current.value = row
  fileVisible.value = true
  uploadType.value = 'PDF'
  await loadFiles(row)
}
async function loadFiles(row) {
  fileLoading.value = true
  try { fileList.value = row.files || [] } finally { fileLoading.value = false }
}
function onFileChange(file) { pendingFile.value = file.raw; doUpload() }
async function doUpload() {
  if (!pendingFile.value || !current.value) return
  try {
    await contractApi.uploadFile(current.value.id, pendingFile.value, uploadType.value)
    ElMessage.success('上传成功')
    const r = await contractApi.records({ dept: props.dept })
    const all = Array.isArray(r) ? r : (r.results || [])
    const upd = all.find(x => x.id === current.value.id)
    if (upd) { current.value = upd; fileList.value = upd.files || [] }
  } catch (e) {} finally { pendingFile.value = null }
}
async function delFile(row) {
  if (!current.value) return
  try {
    await contractApi.deleteFile(current.value.id, row.id)
    ElMessage.success('已删除')
    const r = await contractApi.records({ dept: props.dept })
    const all = Array.isArray(r) ? r : (r.results || [])
    const upd = all.find(x => x.id === current.value.id)
    if (upd) { current.value = upd; fileList.value = upd.files || [] }
  } catch (e) {}
}

watch(() => props.dept, () => loadData())
onMounted(loadData)
</script>

<style scoped>
.contracts { padding: 4px; }
.stat-row { margin-bottom: 14px; }
.mini-card { text-align: center; }
.mini-label { font-size: 13px; color: #909399; }
.mini-value { font-size: 24px; font-weight: 600; margin-top: 6px; color: #303133; }
.mini-value.ok { color: #67c23a; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { margin-bottom: 8px; }
.amt { color: #67c23a; font-weight: 600; }
.file-link { color: #409eff; text-decoration: underline; }
</style>
