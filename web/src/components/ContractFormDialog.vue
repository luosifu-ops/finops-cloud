<template>
  <el-dialog
    :model-value="modelValue"
    :title="mode === 'create' ? '新增合同' : '编辑合同'"
    width="660px"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @open="onOpen"
    @closed="onClosed"
  >
    <el-form :model="form" label-width="96px">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="合同编号（留空自动生成）">
            <el-input v-model="form.contract_no" placeholder="留空则系统自动生成（HT…），亦可手填" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="业务类型" required>
            <el-select v-model="form.biz_type" style="width: 100%">
              <el-option v-for="o in bizTypeOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="客户" required>
        <el-select
          v-model="form.customer" filterable remote reserve-keyword clearable
          placeholder="输入客户名称搜索" :remote-method="searchCustomers" :loading="loadingCustomer"
          style="width: 100%"
        >
          <el-option v-for="o in customerOptions" :key="o.id" :label="o.name" :value="o.id" />
        </el-select>
      </el-form-item>

      <el-form-item label="来源线索">
        <el-select
          v-model="form.lead" filterable remote reserve-keyword clearable
          placeholder="输入姓名/电话搜索" :remote-method="searchLeads" :loading="loadingLead"
          style="width: 100%"
        >
          <el-option v-for="o in leadOptions" :key="o.id" :label="`${o.name} ${o.phone || ''}`" :value="o.id" />
        </el-select>
      </el-form-item>

      <el-form-item label="合同标题" required>
        <el-input v-model="form.title" placeholder="如：2026 年度代理记账服务" />
      </el-form-item>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="合同金额" required>
            <el-input-number v-model="form.amount" :min="0" :precision="2" :step="100" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="付款方式">
            <el-select v-model="form.pay_type" style="width: 100%">
              <el-option v-for="o in payTypeOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="服务周期">
        <el-input v-model="form.service_period" placeholder="如 2026-09 至 2027-08" />
      </el-form-item>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="签单销售">
            <el-select v-model="form.sales" filterable clearable style="width: 100%">
              <el-option v-for="o in salesOptions" :key="o.id" :label="o.display_name || o.username" :value="o.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="签订日期">
            <el-date-picker v-model="form.signed_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="服务开始">
            <el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="服务结束">
            <el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" />
      </el-form-item>

      <el-divider>客户付款截图（统一上传）</el-divider>
      <el-form-item label="付款截图">
        <div style="width: 100%">
          <div v-if="currentPaymentUrl" style="margin-bottom: 8px">
            <a :href="currentPaymentUrl" target="_blank" class="link">查看当前付款截图</a>
          </div>
          <el-upload
            ref="paymentUploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="onPaymentChange"
            :on-exceed="onPaymentExceed"
            :file-list="paymentFileList"
            accept=".jpg,.jpeg,.png,.webp,.pdf"
          >
            <el-button>选择截图</el-button>
          </el-upload>
          <div class="tip">支持 jpg / png / webp / pdf，单文件不超过 20MB；重复上传会覆盖旧截图。</div>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取 消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保 存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import http, { salesApi, orgApi } from '@/api'
import { useUserStore } from '@/store/user'

const store = useUserStore()
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // create | edit
  row: { type: Object, default: null }
})
const emit = defineEmits(['update:modelValue', 'saved'])

const blankForm = () => ({
  contract_no: '', customer: null, lead: null, biz_type: 'AGENCY', title: '',
  amount: 0, pay_type: 'FULL', service_period: '', sales: null, status: 'PENDING',
  signed_date: '', start_date: '', end_date: '', remark: ''
})
const form = reactive(blankForm())

const bizTypeOptions = [
  { value: 'REGISTER', label: '公司注册' }, { value: 'AGENCY', label: '代理记账' },
  { value: 'TAX', label: '税务申报' }, { value: 'CHANGE', label: '工商变更' },
  { value: 'CANCEL', label: '公司注销' }, { value: 'ADDRESS', label: '地址挂靠' },
  { value: 'SOCIAL', label: '社保代理' }, { value: 'AUDIT', label: '审计验资' },
  { value: 'OTHER', label: '其他' },
]
const statusOptions = [
  { value: 'PENDING', label: '待付款' }, { value: 'PAID', label: '已付款' },
  { value: 'EXECUTING', label: '服务中' }, { value: 'FINISHED', label: '已完成' },
  { value: 'REFUNDED', label: '已退款' }, { value: 'CANCELED', label: '已作废' },
]
const payTypeOptions = [
  { value: 'FULL', label: '全款' }, { value: 'DEPOSIT', label: '定金+尾款' },
  { value: 'INSTALLMENT', label: '分期' }, { value: 'MONTHLY', label: '月付' },
]

// 下拉选项
const customerOptions = ref([])
const leadOptions = ref([])
const salesOptions = ref([])
const loadingCustomer = ref(false)
const loadingLead = ref(false)

// 付款截图上传
const paymentUploadRef = ref(null)
const paymentFileList = ref([])
const paymentFile = ref(null)
const currentPaymentUrl = ref('')

async function searchCustomers(kw) {
  loadingCustomer.value = true
  try {
    const r = await salesApi.customers({ search: kw || '', page_size: 50 })
    customerOptions.value = r?.results || r || []
  } catch (e) {
    customerOptions.value = []
  } finally {
    loadingCustomer.value = false
  }
}
async function searchLeads(kw) {
  loadingLead.value = true
  try {
    const r = await salesApi.leads({ search: kw || '', page_size: 50 })
    leadOptions.value = r?.results || r || []
  } catch (e) {
    leadOptions.value = []
  } finally {
    loadingLead.value = false
  }
}
async function loadSales() {
  try {
    const r = await orgApi.users({ page_size: 200 })
    salesOptions.value = Array.isArray(r) ? r : (r.results || [])
  } catch (e) {
    salesOptions.value = []
  }
}

function onPaymentChange(file) {
  paymentFile.value = file.raw || null
  paymentFileList.value = file ? [file] : []
}
function onPaymentExceed(files) {
  const f = files[0]
  paymentFile.value = f.raw || f
  paymentFileList.value = [f]
}

function onOpen() {
  Object.assign(form, blankForm())
  paymentFileList.value = []
  paymentFile.value = null
  loadSales()
  if (props.mode === 'edit' && props.row) {
    const r = props.row
    form.contract_no = r.contract_no || ''
    form.customer = r.customer || null
    form.lead = r.lead || null
    form.biz_type = r.biz_type || 'AGENCY'
    form.title = r.title || ''
    form.amount = Number(r.amount) || 0
    form.pay_type = r.pay_type || 'FULL'
    form.service_period = r.service_period || ''
    form.sales = r.sales || null
    form.status = r.status || 'PENDING'
    form.signed_date = r.signed_date || ''
    form.start_date = r.start_date || ''
    form.end_date = r.end_date || ''
    form.remark = r.remark || ''
    currentPaymentUrl.value = r.payment_screenshot_url || ''
    // 预置下拉当前值，避免编辑时下拉为空
    customerOptions.value = r.customer ? [{ id: r.customer, name: r.customer_name }] : []
    leadOptions.value = r.lead ? [{ id: r.lead, name: r.lead_name, phone: r.lead_phone }] : []
    salesOptions.value = r.sales ? [{ id: r.sales, display_name: r.sales_name, username: r.sales_name }] : []
  } else {
    currentPaymentUrl.value = ''
    // 新增时默认签单销售为当前登录人（普通销售自建合同）
    form.sales = store.userInfo?.id || null
  }
}

function onClosed() {
  paymentFileList.value = []
  paymentFile.value = null
  currentPaymentUrl.value = ''
}

function close() {
  emit('update:modelValue', false)
}

function buildPayload() {
  const p = { ...form }
  p.amount = Number(p.amount) || 0
  return p
}

async function uploadFiles(id) {
  if (paymentFile.value) {
    await salesApi.uploadContractPaymentScreenshot(id, paymentFile.value)
  }
}

const saving = ref(false)
async function handleSave() {
  if (!form.customer) return ElMessage.warning('请选择客户')
  if (!form.title) return ElMessage.warning('请填写合同标题')
  saving.value = true
  try {
    let id
    if (props.mode === 'create') {
      const resp = await salesApi.createContract(buildPayload())
      id = resp?.id ?? resp?.data?.id
    } else {
      id = props.row.id
      await http.patch(`/sales/contracts/${id}/`, buildPayload())
    }
    await uploadFiles(id)
    ElMessage.success('保存成功')
    emit('saved')
    close()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || e?.response?.data?.msg || '保存失败，请检查字段')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.tip { color: #909399; font-size: 12px; line-height: 1.6; }
.link { color: #409eff; font-size: 13px; text-decoration: underline; }
</style>
