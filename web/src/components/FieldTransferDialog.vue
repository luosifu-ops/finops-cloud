<template>
  <el-dialog
    :model-value="modelValue"
    title="转接外勤任务"
    width="560px"
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
        <el-select v-model="form.business_type" style="width:100%">
          <el-option label="工商注册" value="REGISTER" />
          <el-option label="公司注销" value="CANCEL" />
          <el-option label="工商变更" value="CHANGE" />
          <el-option label="地址异常" value="ADDRESS_ABNORMAL" />
          <el-option label="税务报到" value="TAX_REGISTER" />
          <el-option label="异常处理" value="ABNORMAL" />
          <el-option label="通用" value="GENERAL" />
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
  task_type: '',
  address: '',
  due_at: '',
})
const submitting = ref(false)

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      form.customer_name = props.customerName || ''
      form.customer_type = 'ENTERPRISE'
      form.business_type = 'REGISTER'
      form.task_type = ''
      form.address = ''
      form.due_at = ''
    }
  }
)

function reset() {}

async function submit() {
  if (!form.customer_name) return ElMessage.warning('请填写客户名称')
  if (!form.task_type) return ElMessage.warning('请填写任务类型')
  submitting.value = true
  try {
    await http.post('/growth/field-tasks/', {
      title: `${form.customer_name} · ${form.task_type}`,
      customer_name: form.customer_name,
      customer_type: form.customer_type,
      business_type: form.business_type,
      task_type: form.task_type,
      from_order_no: props.sourceOrderNo || '',
      address: form.address || '',
      due_at: form.due_at || null,
    })
    ElMessage.success('已转接外勤，外勤任务池将收到该任务')
    emit('transferred')
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error('转接失败，请重试')
  } finally {
    submitting.value = false
  }
}
</script>
