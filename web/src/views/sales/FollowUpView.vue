<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">线索跟进</h2>
      <span class="page-tip">记录每条线索/客户的跟进动作与下次跟进计划，待跟进任务自动汇总在上方</span>
    </div>

    <!-- 待跟进 -->
    <el-card shadow="never" class="upcoming-card">
      <div class="card-title">待跟进（今日及未来 3 天）
        <el-button text size="small" :icon="Refresh" @click="loadUpcoming" style="float:right">刷新</el-button>
      </div>
      <el-empty v-if="!upcoming.length" description="暂无待跟进任务 🎉" :image-size="70" />
      <el-table v-else :data="upcoming" size="small" stripe max-height="240">
        <el-table-column prop="next_at" label="下次跟进" width="160" />
        <el-table-column prop="next_action" label="下一步动作" min-width="160" show-overflow-tooltip />
        <el-table-column prop="lead_name" label="关联线索" width="120" />
        <el-table-column prop="customer_name" label="关联客户" width="120" />
        <el-table-column prop="user_name" label="跟进人" width="100" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{row}">
            <el-button link type="primary" size="small" @click="openCreate(row)">补记录</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 跟进记录 -->
    <el-card shadow="never" class="list-card" style="margin-top:16px">
      <div class="card-title">跟进记录
        <div style="float:right;display:flex;gap:8px">
          <el-select v-model="query.way" placeholder="跟进方式" clearable style="width:130px" @change="reload">
            <el-option v-for="w in wayOptions" :key="w.value" :label="w.label" :value="w.value" />
          </el-select>
          <el-button type="primary" :icon="Plus" @click="openCreate()">新增跟进</el-button>
        </div>
      </div>
      <el-table :data="list" v-loading="loading" size="small" stripe max-height="460" empty-text="暂无跟进记录">
        <el-table-column prop="created_at" label="跟进时间" width="160" />
        <el-table-column prop="user_name" label="跟进人" width="100" />
        <el-table-column prop="way_name" label="方式" width="90" />
        <el-table-column prop="lead_name" label="线索" width="110" />
        <el-table-column prop="customer_name" label="客户" width="110" />
        <el-table-column prop="content" label="跟进内容" min-width="220" show-overflow-tooltip />
        <el-table-column prop="next_at" label="下次跟进" width="160" />
        <el-table-column prop="next_action" label="下一步" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{row}">
            <!-- 2026-10-30 增量：跟进记录支持录错后编辑 / 删除（本人或管理层） -->
            <el-button v-if="canModify(row)" link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="canModify(row)" link type="danger" size="small" @click="removeFollowup(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager" v-if="total > pageSize">
        <el-pagination background layout="total, prev, pager, next" :total="total"
                       :page-size="pageSize" :current-page="page" @current-change="onPage" />
      </div>
    </el-card>

    <!-- 新增/编辑 -->
    <el-dialog v-model="visible" :title="editingId ? '编辑跟进' : '新增跟进'" width="560px" @closed="resetForm">
      <el-form :model="form" label-width="92px">
        <el-form-item label="关联线索">
          <el-select v-model="form.lead" filterable clearable placeholder="可选关联线索" style="width:100%"
                     :loading="leadLoading">
            <el-option v-for="l in leadOptions" :key="l.id" :label="`${l.name}（${l.phone}）`" :value="l.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联客户">
          <el-select v-model="form.customer" filterable clearable placeholder="可选关联客户" style="width:100%"
                     :loading="custLoading">
            <el-option v-for="c in custOptions" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="跟进方式" required>
          <el-select v-model="form.way" style="width:100%">
            <el-option v-for="w in wayOptions" :key="w.value" :label="w.label" :value="w.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="跟进内容" required>
          <el-input v-model="form.content" type="textarea" :rows="3" placeholder="本次沟通要点" />
        </el-form-item>
        <el-form-item label="下次跟进时间">
          <el-date-picker v-model="form.next_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss"
                          placeholder="选择时间" style="width:100%" />
        </el-form-item>
        <el-form-item label="下一步动作">
          <el-input v-model="form.next_action" placeholder="如：发送报价单 / 约上门" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { salesApi } from '@/api'
import { useUserStore } from '@/store/user'

const wayOptions = [
  { value: 'PHONE', label: '电话' }, { value: 'WECHAT', label: '微信' },
  { value: 'VISIT', label: '上门' }, { value: 'MEETING', label: '会议' }, { value: 'OTHER', label: '其他' },
]

const list = ref([])
const upcoming = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const query = reactive({ way: '' })

const visible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = reactive({ lead: null, customer: null, way: 'PHONE', content: '', next_at: '', next_action: '' })

const leadOptions = ref([])
const custOptions = ref([])
const leadLoading = ref(false)
const custLoading = ref(false)

const fmtList = (resp) => {
  const body = resp || {}
  let payload = body
  if (body && typeof body === 'object' && 'code' in body && 'data' in body) payload = body.data
  if (payload && payload.results) return { rows: payload.results, count: payload.count || payload.results.length }
  if (Array.isArray(payload)) return { rows: payload, count: payload.length }
  return { rows: [], count: 0 }
}

async function reload() {
  loading.value = true
  try {
    const resp = await salesApi.followups({ ...query, page: page.value, page_size: pageSize.value })
    const { rows, count } = fmtList(resp)
    list.value = rows; total.value = count
  } finally { loading.value = false }
}
function onPage(p) { page.value = p; reload() }

async function loadUpcoming() {
  try { const r = await salesApi.upcoming(); const { rows } = fmtList(r); upcoming.value = rows } catch (e) {}
}

async function loadLeads() {
  leadLoading.value = true
  try { const r = await salesApi.leads({ page_size: 200 }); const { rows } = fmtList(r); leadOptions.value = rows } finally { leadLoading.value = false }
}
async function loadCustomers() {
  custLoading.value = true
  try { const r = await salesApi.customers({ page_size: 200 }); const { rows } = fmtList(r); custOptions.value = rows } finally { custLoading.value = false }
}

function resetForm() {
  form.lead = null; form.customer = null; form.way = 'PHONE'; form.content = ''; form.next_at = ''; form.next_action = ''
  editingId.value = null
}
function openCreate(seed) {
  resetForm()
  if (seed && seed.lead) form.lead = seed.lead
  if (seed && seed.customer) form.customer = seed.customer
  visible.value = true
}

// —— 2026-10-30 增量：编辑 / 删除跟进记录（本人或管理层可操作）——
const store = useUserStore()
const myId = computed(() => store.userInfo?.id)
const canManageAll = computed(() => store.isBoss || store.isManager || store.isSuper)
function canModify(row) {
  if (!row) return false
  if (canManageAll.value) return true
  return !!myId.value && row.user === myId.value
}
// ISO 时间 → 'YYYY-MM-DD HH:mm:ss'（el-date-picker value-format 需要）
function normTime(v) {
  if (!v) return ''
  if (typeof v === 'string' && v.includes('T')) {
    const d = new Date(v)
    if (!isNaN(d.getTime())) {
      const p = n => String(n).padStart(2, '0')
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
    }
  }
  return v
}
function openEdit(row) {
  resetForm()
  editingId.value = row.id
  form.lead = row.lead || null
  form.customer = row.customer || null
  form.way = row.way || 'PHONE'
  form.content = row.content || ''
  form.next_at = normTime(row.next_at)
  form.next_action = row.next_action || ''
  visible.value = true
}
async function removeFollowup(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除该条跟进记录吗？（${row.content ? String(row.content).slice(0, 20) : '#' + row.id}）删除后不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
  } catch { return }
  try {
    await salesApi.deleteFollowup(row.id)
    ElMessage.success('已删除')
    reload(); loadUpcoming()
  } catch { /* 拦截器已提示 */ }
}
async function submit() {
  if (!form.content) return ElMessage.warning('请填写跟进内容')
  if (!form.way) return ElMessage.warning('请选择跟进方式')
  saving.value = true
  const payload = {
    way: form.way, content: form.content,
    next_at: form.next_at || null, next_action: form.next_action || '',
    lead: form.lead || null, customer: form.customer || null,
  }
  try {
    if (editingId.value) await salesApi.updateFollowup(editingId.value, payload)
    else await salesApi.createFollowup(payload)
    ElMessage.success('已保存')
    visible.value = false
    reload(); loadUpcoming()
  } catch (e) { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

onMounted(() => { reload(); loadUpcoming(); loadLeads(); loadCustomers() })
</script>

<style scoped>
.page-tip { font-size: 12px; color: var(--text-sub); margin-left: 10px; font-weight: 400; }
.card-title { font-weight: 700; margin-bottom: 14px; font-size: 15px; }
.pager { margin-top: 14px; display: flex; justify-content: flex-end; }
</style>
