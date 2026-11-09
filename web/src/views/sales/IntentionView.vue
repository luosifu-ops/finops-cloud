<template>
  <BaseListView title="意向用户池" baseUrl="/sales/leads/" :columns="intentionColumns" :form-fields="intentionForm"
    :search-fields="intentionSearch" :extra-params="{ status: 'INTENTION' }" auto-form>
    <template #row-actions="{ row }">
      <el-button v-if="canManage" link type="warning" @click="openAssign(row)">指派</el-button>
    </template>
  </BaseListView>

  <!-- 指派成交师 -->
  <el-dialog v-model="assignVisible" title="指派线索给成交师" width="460px" @closed="resetAssign">
    <el-form label-width="88px">
      <el-form-item label="客户">
        <span>{{ assignRow?.name }}（{{ assignRow?.phone }}）</span>
      </el-form-item>
      <el-form-item label="指派给" required>
        <PersonSelect v-model="assignUid" placeholder="选择成交师 / 销售" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="assignVisible = false">取消</el-button>
      <el-button type="primary" :loading="assigning" @click="submitAssign">确认指派</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import BaseListView from '@/components/BaseListView.vue'
import http, { salesApi } from '@/api'
import { useUserStore } from '@/store/user'
import PersonSelect from '@/components/PersonSelect.vue'

const store = useUserStore()
// 仅主管/老板/超管可见「指派」入口；2026-11-03 增加单点授权 can_assign_leads
const canManage = computed(() => store.isBoss || store.isManager || store.isSuper || store.isHR || store.canAssignLeads)

// 电销部·意向用户池：复用销售线索接口，按 status=INTENTION（高意向）过滤
// 展示字段优先用后端 *_name 中文展示字段，避免英文码
const intentionColumns = [
  { prop: 'id', label: '线索编号', width: 90 },
  { prop: 'name', label: '客户姓名', minWidth: 110 },
  { prop: 'phone', label: '手机号', width: 130 },
  { prop: 'wechat', label: '微信号', minWidth: 120 },
  { prop: 'company', label: '公司名称', minWidth: 160 },
  { prop: 'intention', label: '意向业务', minWidth: 120 },
  { prop: 'level_name', label: '客户等级', width: 100 },
  { prop: 'status_name', label: '线索状态', width: 100 },
  { prop: 'owner_name', label: '负责人', minWidth: 100 },
  { prop: 'remark', label: '备注', minWidth: 160 },
  { prop: 'created_at', label: '创建时间', width: 160 },
]

// 编辑/新增表单：状态可选全量线索状态（高意向推进到成交 / 回流到跟进中等）
const intentionForm = [
  { prop: 'name', label: '客户姓名', type: 'text', required: true },
  { prop: 'phone', label: '手机号', type: 'text', required: true },
  { prop: 'wechat', label: '微信号', type: 'text' },
  { prop: 'company', label: '公司名称', type: 'text' },
  { prop: 'intention', label: '意向业务', type: 'text' },
  {
    prop: 'level', label: '客户等级', type: 'select',
    options: [
      { value: 'A', label: 'A级' }, { value: 'B', label: 'B级' },
      { value: 'C', label: 'C级' }, { value: 'D', label: 'D级' },
    ],
  },
  {
    prop: 'status', label: '线索状态', type: 'select',
    options: [
      { value: 'NEW', label: '待分配' }, { value: 'ASSIGNED', label: '已分配' },
      { value: 'FOLLOWING', label: '跟进中' }, { value: 'INTENTION', label: '高意向' },
      { value: 'DEAL', label: '已成交' }, { value: 'LOST', label: '已流失' },
      { value: 'INVALID', label: '无效' },
    ],
  },
  { prop: 'remark', label: '备注', type: 'textarea' },
]

const intentionSearch = [
  { prop: 'name', label: '客户姓名', type: 'text' },
  { prop: 'phone', label: '手机号', type: 'text' },
  { prop: 'company', label: '公司名称', type: 'text' },
  { prop: 'intention', label: '意向业务', type: 'text' },
]

// ---- 指派逻辑（复用线索指派接口）----
const assignVisible = ref(false)
const assigning = ref(false)
const assignUid = ref(null)
const users = ref([])
const assignRow = ref(null)

function openAssign(row) {
  assignRow.value = row
  assignUid.value = null
  assignVisible.value = true
  if (!users.value.length) loadUsers()
}
function resetAssign() {
  assignUid.value = null
  assignRow.value = null
}
async function loadUsers() {
  try {
    const r = await http.get('/accounts/users/', { params: { page_size: 200, for_assign: 1 } })
    users.value = Array.isArray(r) ? r : (r.results || [])
  } catch (e) {
    users.value = []
  }
}
async function submitAssign() {
  if (!assignUid.value) return ElMessage.warning('请选择指派的成交师')
  assigning.value = true
  try {
    const resp = await salesApi.assignLeads({ ids: [assignRow.value.id], owner_id: assignUid.value })
    if (resp && resp.code === 0) {
      ElMessage.success(`已指派给 ${users.value.find(u => u.id === assignUid.value)?.display_name || '成交师'}`)
      assignVisible.value = false
    } else {
      ElMessage.warning(resp?.msg || '指派未完成')
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.msg || '指派失败，请重试')
  } finally {
    assigning.value = false
  }
}

onMounted(loadUsers)
</script>
