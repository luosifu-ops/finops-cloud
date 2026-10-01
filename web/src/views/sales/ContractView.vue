<template>
  <div>
    <BaseListView
      ref="listRef"
      title="合同订单"
      :base-url="contractBaseUrl"
      :columns="columns"
      :auto-form="false"
      :can-delete="false"
    >
      <template #header-extra>
        <template v-if="canManageAll">
          <el-tag type="warning" effect="plain" style="margin-right: 10px">
            管理视角：{{ scopeMode === 'all' ? '全部人员合同' : '仅我的合同' }}
          </el-tag>
          <el-radio-group v-model="scopeMode" size="small" style="margin-right: 10px" @change="reload">
            <el-radio-button label="all">全部合同</el-radio-button>
            <el-radio-button label="mine">我的合同</el-radio-button>
          </el-radio-group>
        </template>
        <el-button type="success" plain @click="openUpload">上传合同扫描件</el-button>
        <el-button type="primary" plain @click="openCreate">新增合同</el-button>
      </template>

      <template #row-actions="{ row }">
        <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        <el-button link type="warning" @click="openTransfer(row)">转外勤</el-button>
        <el-button
          v-if="row.payment_screenshot_url"
          link type="success"
          @click="openUrl(row.payment_screenshot_url)"
        >查看截图</el-button>
        <el-button
          v-if="row.attachment_url"
          link type="info"
          @click="openUrl(row.attachment_url)"
        >查看扫描件</el-button>
        <el-button link type="danger" @click="remove(row)">删除</el-button>
      </template>
    </BaseListView>

    <!-- 转接外勤 -->
    <FieldTransferDialog
      v-model="transferVisible"
      :customer-name="transferRow.customer_name"
      :source-order-no="transferRow.contract_no"
      source-type="合同"
      @transferred="reload"
    />

    <!-- 合同扫描件上传（保留原有独立功能） -->
    <el-dialog v-model="uploadVisible" title="上传合同扫描件" width="520px">
      <el-form label-width="96px">
        <el-form-item label="选择合同" required>
          <el-select
            v-model="form.contractId"
            filterable
            remote
            reserve-keyword
            clearable
            placeholder="输入合同编号 / 标题 / 客户名搜索"
            :remote-method="searchContracts"
            :loading="searching"
            style="width: 100%"
            @change="onContractChange"
          >
            <el-option
              v-for="c in contractOptions"
              :key="c.id"
              :label="contractLabel(c)"
              :value="c.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="已有附件">
          <span v-if="!form.contractId" class="tip">请先选择合同</span>
          <a v-else-if="currentAttachment" :href="currentAttachment" target="_blank" class="link">
            查看当前扫描件
          </a>
          <span v-else class="tip">暂无，上传后将生成</span>
        </el-form-item>

        <el-form-item label="选择文件" required>
          <div style="width: 100%">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              :on-change="onFileChange"
              :on-exceed="onExceed"
              :file-list="fileList"
              accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx"
            >
              <el-button>选择文件</el-button>
            </el-upload>
            <div class="tip">支持 pdf / 图片 / word / excel，单文件不超过 20MB；重复上传会覆盖旧文件。</div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="uploadVisible = false">取 消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload">开始上传</el-button>
      </template>
    </el-dialog>

    <!-- 新增 / 编辑合同（统一弹窗，内含付款截图上传） -->
    <ContractFormDialog v-model="formVisible" :mode="formMode" :row="formRow" @saved="reload" />
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BaseListView from '../../components/BaseListView.vue'
import FieldTransferDialog from '../../components/FieldTransferDialog.vue'
import ContractFormDialog from '../../components/ContractFormDialog.vue'
import http, { salesApi } from '../../api'
import { useUserStore } from '@/store/user'

const store = useUserStore()
// 管理人员（BOSS / HR / MANAGER）可见全部合同，并提供「全部 / 我的」视角切换
const canManageAll = computed(() => store.isBoss || store.isManager || store.isHR)
const scopeMode = ref('all')
const contractBaseUrl = computed(() =>
  scopeMode.value === 'mine' ? '/sales/contracts/my/' : '/sales/contracts/'
)

// 表头全部中文，无英文残留；付款截图列位于「状态」之后、「签约日期」之前
const columns = [
  { prop: 'id', label: '编号', width: 80 },
  { prop: 'contract_no', label: '合同号', minWidth: 130 },
  { prop: 'customer_name', label: '客户名称', minWidth: 140 },
  { prop: 'lead_name', label: '线索客户', minWidth: 110 },
  { prop: 'biz_type_name', label: '业务类型', width: 110 },
  { prop: 'title', label: '合同标题', minWidth: 160 },
  { prop: 'amount', label: '合同金额', width: 120 },
  { prop: 'received', label: '已收金额', width: 110 },
  { prop: 'receivable', label: '应收金额', width: 110 },
  { prop: 'pay_type_name', label: '付款方式', width: 110 },
  { prop: 'service_period', label: '服务周期', minWidth: 120 },
  { prop: 'sales_name', label: '签单销售', minWidth: 100 },
  { prop: 'status_name', label: '状态', width: 100 },
  { prop: 'payment_screenshot_url', label: '付款截图', minWidth: 200 },
  { prop: 'signed_date', label: '签约日期', width: 120 },
  { prop: 'start_date', label: '服务开始', width: 120 },
  { prop: 'end_date', label: '服务结束', width: 120 },
  { prop: 'attachment_url', label: '合同扫描件', minWidth: 200 },
  { prop: 'remark', label: '备注', minWidth: 160 },
  { prop: 'created_at', label: '创建时间', width: 160 },
]

const listRef = ref(null)
function reload() {
  listRef.value?.reload()
}

function openUrl(url) {
  if (url) window.open(url, '_blank')
}

// ---------------- 转外勤 ----------------
const transferVisible = ref(false)
const transferRow = reactive({ customer_name: '', contract_no: '' })
function openTransfer(row) {
  transferRow.customer_name = row.customer_name || ''
  transferRow.contract_no = row.contract_no || row.order_no || ''
  transferVisible.value = true
}

// ---------------- 合同扫描件上传（保留） ----------------
const uploadRef = ref(null)
const uploadVisible = ref(false)
const uploading = ref(false)
const searching = ref(false)
const contractOptions = ref([])
const fileList = ref([])
const currentAttachment = ref('')
const pickedFile = ref(null)
const form = reactive({ contractId: null })

function contractLabel(c) {
  const parts = [c.contract_no, c.title, c.customer_name].filter(Boolean)
  return parts.join(' · ') || `合同 #${c.id}`
}
async function fetchContracts(keyword = '') {
  searching.value = true
  try {
    const resp = await salesApi.contracts({ search: keyword, page_size: 50 })
    contractOptions.value = resp?.results || resp || []
  } catch (e) {
    contractOptions.value = []
  } finally {
    searching.value = false
  }
}
function searchContracts(kw) {
  fetchContracts(kw || '')
}
function onContractChange(id) {
  const hit = contractOptions.value.find((c) => c.id === id)
  currentAttachment.value = hit?.attachment_url || ''
}
function openUpload() {
  form.contractId = null
  currentAttachment.value = ''
  pickedFile.value = null
  fileList.value = []
  uploadVisible.value = true
  fetchContracts('')
}
function onFileChange(file) {
  pickedFile.value = file.raw || null
  fileList.value = file ? [file] : []
}
function onExceed(files) {
  uploadRef.value?.clearFiles()
  const f = files[0]
  uploadRef.value?.handleStart(f)
  pickedFile.value = f
}
async function submitUpload() {
  if (!form.contractId) return ElMessage.warning('请先选择合同')
  if (!pickedFile.value) return ElMessage.warning('请选择要上传的文件')
  if (pickedFile.value.size > 20 * 1024 * 1024) return ElMessage.warning('文件不能超过 20MB')
  uploading.value = true
  try {
    const resp = await salesApi.uploadContractAttachment(form.contractId, pickedFile.value)
    const url = resp?.data?.attachment_url || ''
    currentAttachment.value = url
    const hit = contractOptions.value.find((c) => c.id === form.contractId)
    if (hit) hit.attachment_url = url
    ElMessage.success('上传成功')
    pickedFile.value = null
    fileList.value = []
    uploadRef.value?.clearFiles()
    reload()
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || '上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

// ---------------- 新增 / 编辑合同（统一弹窗） ----------------
const formVisible = ref(false)
const formMode = ref('create')
const formRow = ref(null)
function openCreate() {
  formMode.value = 'create'
  formRow.value = null
  formVisible.value = true
}
function openEdit(row) {
  formMode.value = 'edit'
  formRow.value = row
  formVisible.value = true
}

// ---------------- 删除 ----------------
async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除合同「${row.contract_no || row.title}」？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await http.delete(`/sales/contracts/${row.id}/`)
    ElMessage.success('已删除')
    reload()
  } catch (e) {
    ElMessage.error('删除失败，请重试')
  }
}
</script>

<style scoped>
.tip { color: #909399; font-size: 12px; line-height: 1.6; }
.link { color: #409eff; font-size: 13px; text-decoration: underline; }
</style>
