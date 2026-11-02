<template>
  <el-dialog
    :model-value="modelValue"
    title="合同订单流转外勤"
    width="580px"
    @update:model-value="$emit('update:modelValue', $event)"
    @closed="reset"
  >
    <el-alert type="info" :closable="false" show-icon :title="`来源：${sourceType} · ${sourceOrderNo || '—'}`" />
    <el-form :model="form" label-width="110px" style="margin-top:12px">
      <el-form-item label="客户名称" required>
        <el-input v-model="form.customer_name" placeholder="客户 / 企业名称" />
      </el-form-item>
      <el-form-item label="客户类型">
        <el-select v-model="form.customer_type" style="width:100%">
          <el-option label="企业" value="ENTERPRISE" />
          <el-option label="个体工商户" value="INDIVIDUAL" />
          <el-option label="个人" value="PERSONAL" />
        </el-select>
      </el-form-item>
      <el-form-item label="业务类型" required>
        <el-select v-model="form.business_type" style="width:100%" @change="onBusinessTypeChange">
          <el-option v-for="b in businessTypeOptions" :key="b.value" :label="b.label" :value="b.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="任务类型" required>
        <el-input v-model="form.task_type" placeholder="如：工商注册 / 异常处理 / 注销 / 税务报到 / 地址异常" />
      </el-form-item>
      <el-form-item label="办理地点">
        <el-input v-model="form.address" placeholder="外勤办理地址（可选）" />
      </el-form-item>
      <el-form-item label="要求完成时间">
        <el-date-picker
          v-model="form.due_at"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          placeholder="可选"
          style="width:100%"
        />
      </el-form-item>
      <el-form-item label="下发外勤人员">
        <el-select
          v-model="form.assignee"
          placeholder="留空则进入外勤任务池，由外勤主管派单"
          clearable
          filterable
          :loading="staffLoading"
          style="width:100%"
        >
          <el-option v-for="u in staffOptions" :key="u.id" :label="u.name" :value="u.id">
            <span>{{ u.name }}</span>
            <span class="opt-dept">{{ u.dept }}</span>
          </el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填，如：客户要求本周内办结" />
      </el-form-item>
      <el-alert
        type="success"
        :closable="false"
        show-icon
        :title="form.assignee ? '已选择外勤人员：生成后直接出现在该外勤的任务池并留痕' : '未指定外勤：生成后进入外勤任务池，等待派单或外勤自行接单'"
      />
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">生成外勤任务</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '@/api'
import { orgApi } from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  customerName: { type: String, default: '' },
  sourceOrderNo: { type: String, default: '' },
  sourceType: { type: String, default: '业务单' },
})
const emit = defineEmits(['update:modelValue', 'transferred'])

const businessTypeOptions = [
  { label: '工商注册', value: 'REGISTER' },
  { label: '公司注销', value: 'CANCEL' },
  { label: '工商变更', value: 'CHANGE' },
  { label: '地址异常', value: 'ADDRESS_ABNORMAL' },
  { label: '税务报到', value: 'TAX_REGISTER' },
  { label: '异常处理', value: 'ABNORMAL' },
  { label: '通用', value: 'GENERAL' },
]

const form = reactive({
  customer_name: '',
  customer_type: 'ENTERPRISE',
  business_type: 'REGISTER',
  task_type: '工商注册',
  address: '',
  due_at: '',
  assignee: null,
  remark: '',
})
const submitting = ref(false)

// 下发人员名单：真实在职员工（后端已过滤 is_active）
const staffOptions = ref([])
const staffLoading = ref(false)

async function loadStaff() {
  if (staffOptions.value.length || staffLoading.value) return
  staffLoading.value = true
  try {
    const res = await orgApi.users({ page_size: 500 })
    const rows = Array.isArray(res) ? res : (res.results || [])
    staffOptions.value = rows.map((u) => ({
      id: u.id,
      name: u.display_name || u.first_name || u.username,
      dept: u.department_name || '',
    }))
  } catch (e) {
    staffOptions.value = []
  } finally {
    staffLoading.value = false
  }
}

function onBusinessTypeChange(v) {
  const hit = businessTypeOptions.find((b) => b.value === v)
  if (hit) form.task_type = hit.label
}

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      form.customer_name = props.customerName || ''
      form.customer_type = 'ENTERPRISE'
      form.business_type = 'REGISTER'
      form.task_type = '工商注册'
      form.address = ''
      form.due_at = ''
      form.assignee = null
      form.remark = ''
      loadStaff()
    }
  }
)

function reset() {}

async function submit() {
  if (!form.customer_name) return ElMessage.warning('请填写客户名称')
  if (!form.task_type) return ElMessage.warning('请填写任务类型')
  submitting.value = true
  try {
    const payload = {
      title: `${form.customer_name} · ${form.task_type}`,
      customer_name: form.customer_name,
      customer_type: form.customer_type,
      business_type: form.business_type,
      task_type: form.task_type,
      from_order_no: props.sourceOrderNo || '',
      address: form.address || '',
      due_at: form.due_at || null,
      remark: form.remark || '',
    }
    if (form.assignee) payload.assignee = form.assignee
    const res = await http.post('/growth/field-tasks/', payload)
    const no = res?.task_no ? `（派单号 ${res.task_no}）` : ''
    ElMessage.success(
      form.assignee
        ? `已下发外勤${no}，该外勤任务池即时可见`
        : `已转接外勤${no}，外勤任务池将收到该任务`
    )
    emit('transferred')
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error('流转失败，请重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.opt-dept { float: right; color: #a8abb2; font-size: 12px; }
</style>
