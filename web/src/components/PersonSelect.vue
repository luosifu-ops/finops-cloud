<template>
  <div class="person-select">
    <el-select
      :model-value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :size="size"
      :clearable="clearable"
      :filterable="true"
      :filter-method="onFilter"
      @update:model-value="onPick"
      @visible-change="onVisible"
      style="width:100%"
    >
      <el-option
        v-for="u in filtered"
        :key="u.id"
        :label="labelOf(u)"
        :value="u.id"
      >
        <span class="ps-name">{{ labelOf(u) }}</span>
        <span class="ps-meta">{{ metaOf(u) }}</span>
      </el-option>

      <!-- 搜索无结果时：支持直接输入姓名新增人员 -->
      <el-option v-if="createTip" :value="CREATE_PREFIX + query.trim()" :label="query.trim()">
        <span class="ps-create">{{ createTip }}</span>
      </el-option>
    </el-select>

    <!-- 快速新增人员 -->
    <el-dialog v-model="dialogVisible" title="新增人员" width="440px" append-to-body destroy-on-close>
      <el-form :model="form" label-width="76px" size="default">
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" maxlength="20" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="手机号" required>
          <el-input v-model="form.phone" maxlength="11" placeholder="11 位手机号，同时作为登录账号" />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="form.department" clearable placeholder="可留空" style="width:100%">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width:100%">
            <el-option label="员工" value="EMPLOYEE" />
            <el-option label="主管" value="LEADER" />
            <el-option label="经理" value="MANAGER" />
            <el-option label="人事" value="HR" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width:100%">
            <el-option label="试用期" value="PROBATION" />
            <el-option label="正式" value="REGULAR" />
            <el-option label="实习" value="INTERN" />
          </el-select>
        </el-form-item>
        <el-alert type="info" :closable="false" show-icon
          title="初始密码 123456，创建后可在此直接选中；建议提醒本人尽快修改" />
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建并选中</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 统一人员选择器
 *
 * - 下拉选人（可按姓名 / 手机号 / 部门搜索）
 * - 列表内找不到对应人员时，直接输入姓名即可「一键新增人员」并自动选中
 * - 无新增权限的账号（非人事/老板）会给出提示：
 *     includeFreeText=true 时按姓名文本留存（用于只存姓名的字段）
 */
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { orgApi } from '@/api/index'
import { useUserStore } from '@/store/user'

const props = defineProps({
  modelValue: { type: [Number, String, null], default: null },
  placeholder: { type: String, default: '选择人员，或输入姓名新增' },
  disabled: Boolean,
  clearable: { type: Boolean, default: true },
  size: { type: String, default: 'default' },
  /** 只显示某个部门（传部门名称，如「电销部」） */
  deptName: { type: String, default: '' },
  /** 只显示某个角色（BOSS/MANAGER/LEADER/HR/EMPLOYEE） */
  role: { type: String, default: '' },
  /** 允许以「姓名文本」形式留存（无新增权限时使用） */
  includeFreeText: { type: Boolean, default: false },
  /** 是否自动加载（父级已传全量列表时可关掉） */
  autoLoad: { type: Boolean, default: true }
})
const emit = defineEmits(['update:modelValue', 'change'])

const store = useUserStore()
const CREATE_PREFIX = '__CREATE__:'

const users = ref([])
const departments = ref([])
const query = ref('')
const loaded = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({ name: '', phone: '', department: null, role: 'EMPLOYEE', status: 'PROBATION' })

const canCreate = computed(() => !!(store.isBoss || store.isHR || store.isAdmin || store.isSuper))

const scoped = computed(() => {
  let list = users.value
  if (props.deptName) list = list.filter(u => (u.department_name || '') === props.deptName)
  if (props.role) list = list.filter(u => u.role === props.role)
  return list
})

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return scoped.value.slice(0, 300)
  return scoped.value.filter(u => {
    const hay = `${u.display_name || ''}${u.username || ''}${u.phone || ''}${u.department_name || ''}`.toLowerCase()
    return hay.includes(q)
  }).slice(0, 300)
})

const exactMatch = computed(() => {
  const q = query.value.trim()
  if (!q) return true
  return scoped.value.some(u => (u.display_name || '') === q || (u.username || '') === q || (u.phone || '') === q)
})

const createTip = computed(() => {
  const q = query.value.trim()
  if (!q || exactMatch.value) return ''
  if (canCreate.value) return `+ 新增人员「${q}」`
  if (props.includeFreeText) return `+ 以「${q}」直接填入（无新增权限）`
  return ''
})

function labelOf(u) {
  return u.display_name || u.username || ('用户' + u.id)
}
function metaOf(u) {
  return [u.department_name, u.role_name].filter(Boolean).join(' · ')
}

function onFilter(q) { query.value = q || '' }
function onVisible(v) { if (!v) query.value = '' }

async function load() {
  if (!props.autoLoad || loaded.value) return
  try {
    const r = await orgApi.users({ page_size: 500, for_assign: 1 })
    users.value = Array.isArray(r) ? r : (r.results || r.data?.results || r.data || [])
    loaded.value = true
  } catch (e) { /* 静默：无权限时仅不可搜索 */ }
}

async function loadDepartments() {
  if (departments.value.length) return
  try {
    const r = await orgApi.departments({ page_size: 100 })
    departments.value = Array.isArray(r) ? r : (r.results || r.data?.results || [])
  } catch (e) {}
}

function onPick(val) {
  if (val === null || val === undefined || val === '') {
    emit('update:modelValue', null)
    emit('change', null)
    return
  }
  const s = String(val)
  if (s.startsWith(CREATE_PREFIX)) {
    const name = s.slice(CREATE_PREFIX.length).trim()
    if (canCreate.value) {
      form.value = { name, phone: '', department: null, role: 'EMPLOYEE', status: 'PROBATION' }
      loadDepartments()
      dialogVisible.value = true
    } else {
      // 无新增权限：按姓名文本留存
      emit('update:modelValue', name)
      emit('change', { display_name: name, free_text: true })
      ElMessage.info(`已按姓名「${name}」填入`)
    }
    return
  }
  const id = Number(s)
  const u = users.value.find(x => x.id === id)
  emit('update:modelValue', id)
  emit('change', u || null)
}

async function submitCreate() {
  const name = (form.value.name || '').trim()
  const phone = (form.value.phone || '').trim()
  if (!name) return ElMessage.warning('请输入姓名')
  if (!/^1\d{10}$/.test(phone)) return ElMessage.warning('请输入正确的 11 位手机号')
  saving.value = true
  try {
    const payload = {
      username: phone,
      password: '123456',
      first_name: name,
      phone,
      role: form.value.role,
      status: form.value.status
    }
    if (form.value.department) payload.department = form.value.department
    const r = await orgApi.createUser(payload)
    const created = r?.data || r
    users.value = [{ ...created, display_name: created.display_name || name }, ...users.value]
    emit('update:modelValue', created.id)
    emit('change', created)
    dialogVisible.value = false
    ElMessage.success(`已新增人员「${name}」，初始密码 123456`)
  } catch (e) {
    // 错误提示已由 http 拦截器统一处理
  } finally {
    saving.value = false
  }
}

watch(() => props.autoLoad, () => load())
onMounted(load)

defineExpose({ reload: () => { loaded.value = false; load() } })
</script>

<style scoped>
.person-select { width: 100%; }
.ps-name { float: left; }
.ps-meta { float: right; color: var(--text-weak); font-size: 12px; margin-left: 12px; }
.ps-create { color: var(--primary); font-weight: 600; }
</style>
