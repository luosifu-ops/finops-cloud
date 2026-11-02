<template>
  <BaseListView title="线索池" baseUrl="/sales/leads/" :columns="leadColumns" :search-fields="leadSearch" auto-form>
    <template #row-actions="{ row }">
      <el-button link type="primary" @click="openDetail(row)">详情</el-button>
      <el-button link type="success" @click="openFollow(row)">跟进</el-button>
      <el-button v-if="canManage" link type="warning" @click="openAssign(row)">指派</el-button>
    </template>
  </BaseListView>

  <!-- 穿透详情抽屉：基础信息 + 全流程时间线 -->
  <el-drawer v-model="detailVisible" :title="`线索详情 · ${detailRow?.name || ''}`" size="42%">
    <div v-loading="detailLoading">
      <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
        <el-descriptions-item label="客户">{{ detailRow?.name }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ detailRow?.phone }}</el-descriptions-item>
        <el-descriptions-item label="来源">{{ detailRow?.source_name || detailRow?.source }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ detailRow?.status_name || detailRow?.status }}</el-descriptions-item>
        <el-descriptions-item label="负责人">{{ detailRow?.owner_name || '公海' }}</el-descriptions-item>
        <el-descriptions-item label="等级">{{ detailRow?.level_name || detailRow?.level }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-if="!timeline.length" description="暂无流转记录" :image-size="70" />
      <el-timeline v-else style="padding-left:6px">
        <el-timeline-item v-for="(t, i) in timeline" :key="i" :timestamp="t.time" placement="top"
          :type="{ '创建': 'primary', '成交': 'success', '流失': 'danger' }[t.action]">
          <b>{{ t.action }}</b>
          <span style="color:#909399;font-size:12px;margin-left:8px">{{ t.who }}</span>
          <div style="font-size:13px;color:#303133;margin-top:2px;white-space:pre-wrap">{{ t.detail }}</div>
        </el-timeline-item>
      </el-timeline>
    </div>
  </el-drawer>

  <!-- 跟进记录抽屉：在运营部线索池内直接查看/补录该线索的跟进记录 -->
  <el-drawer v-model="followVisible" :title="`跟进记录 · ${followRow?.name || ''}`" size="46%" @closed="resetFollow">
    <template #header>
      <div>
        <span style="font-size:16px;font-weight:700">跟进记录 · {{ followRow?.name || '' }}</span>
        <span style="margin-left:8px;color:#909399;font-size:12px">{{ followRow?.phone }}</span>
      </div>
    </template>

    <div v-loading="followLoading">
      <el-empty v-if="!followList.length" description="暂无跟进记录，点击下方新增" :image-size="70" />
      <el-timeline v-else style="padding-left:6px">
        <el-timeline-item
          v-for="f in followList"
          :key="f.id"
          :timestamp="f.created_at"
          placement="top"
        >
          <div class="fu-card">
            <div class="fu-meta">
              <el-tag size="small" effect="plain">{{ f.way_name }}</el-tag>
              <span class="fu-user">{{ f.user_name }}</span>
              <el-tag v-if="f.next_at" size="small" type="warning" effect="plain">下次：{{ f.next_at }}</el-tag>
            </div>
            <div class="fu-content">{{ f.content }}</div>
            <div v-if="f.next_action" class="fu-next">下一步：{{ f.next_action }}</div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>

    <el-divider>新增跟进</el-divider>
    <el-form :model="fuForm" label-width="84px">
      <el-form-item label="跟进方式" required>
        <el-select v-model="fuForm.way" style="width:100%">
          <el-option v-for="w in wayOptions" :key="w.value" :label="w.label" :value="w.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="跟进内容" required>
        <el-input v-model="fuForm.content" type="textarea" :rows="3" placeholder="本次沟通要点" />
      </el-form-item>
      <el-form-item label="下次跟进">
        <el-date-picker v-model="fuForm.next_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss"
                        placeholder="选择时间" style="width:100%" />
      </el-form-item>
      <el-form-item label="下一步">
        <el-input v-model="fuForm.next_action" placeholder="如：发送报价单 / 约上门" />
      </el-form-item>
      <el-button type="primary" :loading="fuSaving" style="width:100%" @click="submitFollow">保存跟进</el-button>
    </el-form>
  </el-drawer>

  <!-- 指派成交师 -->
  <el-dialog v-model="assignVisible" title="指派线索给成交师" width="460px" @closed="resetAssign">
    <el-form label-width="88px">
      <el-form-item label="线索客户">
        <span>{{ assignRow?.name }}（{{ assignRow?.phone }}）</span>
      </el-form-item>
      <el-form-item label="指派给" required>
        <PersonSelect v-model="assignUid" placeholder="选择成交师 / 销售，或输入姓名新增" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="assignVisible = false">取消</el-button>
      <el-button type="primary" :loading="assigning" @click="submitAssign">确认指派</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import BaseListView from '@/components/BaseListView.vue'
import http, { salesApi } from '@/api'
import { useUserStore } from '@/store/user'
import PersonSelect from '@/components/PersonSelect.vue'

const store = useUserStore()
// 仅主管/老板/超管可见「指派」入口
const canManage = computed(() => store.isBoss || store.isManager || store.isSuper || store.isHR)

// 财税CRM 线索池表头：英文接口字段 → 中文业务名（仅前端展示，不改后端字段）
const leadColumns = [
  { prop: 'id', label: '线索编号', width: 90 },
  { prop: 'lead_no', label: '线索单号', width: 130 },
  { prop: 'name', label: '客户姓名', minWidth: 110 },
  { prop: 'phone', label: '手机号', width: 130 },
  { prop: 'wechat', label: '微信号', minWidth: 120 },
  { prop: 'company', label: '公司名称', minWidth: 160 },
  { prop: 'source', label: '来源类型', width: 110 },
  { prop: 'source_name', label: '来源平台', minWidth: 120 },
  { prop: 'source_detail', label: '渠道明细', minWidth: 130 },
  { prop: 'intention', label: '意向业务', minWidth: 120 },
  { prop: 'level', label: '客户等级', width: 100 },
  { prop: 'level_name', label: '等级名称', width: 100 },
  { prop: 'status', label: '线索状态', width: 100 },
  { prop: 'status_name', label: '状态名称', width: 100 },
  { prop: 'owner_name', label: '负责人', minWidth: 100 },
  { prop: 'remark', label: '备注', minWidth: 160 },
  { prop: 'lost_reason', label: '流失原因', minWidth: 130 },
  { prop: 'assigned_at', label: '分配时间', width: 160 },
  { prop: 'dealt_at', label: '成交时间', width: 160 },
  { prop: 'created_at', label: '创建时间', width: 160 },
]

const leadSearch = [
  { prop: 'name', label: '客户姓名', type: 'text' },
  { prop: 'phone', label: '手机号', type: 'text' },
  { prop: 'company', label: '公司名称', type: 'text' },
  { prop: 'source', label: '来源类型', type: 'text' },
  { prop: 'intention', label: '意向业务', type: 'text' },
]

// ---- 跟进记录（增量功能，复用现有 FollowUp 后端）----
const followVisible = ref(false)
const followLoading = ref(false)
const followList = ref([])
const followRow = ref(null)
const fuSaving = ref(false)
const fuForm = reactive({ way: 'PHONE', content: '', next_at: '', next_action: '' })
const wayOptions = [
  { value: 'PHONE', label: '电话' }, { value: 'WECHAT', label: '微信' },
  { value: 'VISIT', label: '上门' }, { value: 'MEETING', label: '会议' }, { value: 'OTHER', label: '其他' },
]

function extractRows(resp) {
  const body = resp || {}
  let payload = body
  if (body && typeof body === 'object' && 'code' in body && 'data' in body) payload = body.data
  if (payload && payload.results) return payload.results
  if (Array.isArray(payload)) return payload
  return []
}

async function openFollow(row) {
  followRow.value = row
  followVisible.value = true
  await loadFollow(row.id)
}
async function loadFollow(leadId) {
  followLoading.value = true
  try {
    const resp = await salesApi.followups({ lead: leadId, page_size: 100, ordering: '-created_at' })
    followList.value = extractRows(resp)
  } catch (e) {
    followList.value = []
  } finally {
    followLoading.value = false
  }
}
function resetFollow() {
  followRow.value = null
  followList.value = []
  fuForm.way = 'PHONE'; fuForm.content = ''; fuForm.next_at = ''; fuForm.next_action = ''
}
async function submitFollow() {
  if (!followRow.value) return
  if (!fuForm.content) return ElMessage.warning('请填写跟进内容')
  if (!fuForm.way) return ElMessage.warning('请选择跟进方式')
  fuSaving.value = true
  try {
    await salesApi.createFollowup({
      lead: followRow.value.id,
      way: fuForm.way,
      content: fuForm.content,
      next_at: fuForm.next_at || null,
      next_action: fuForm.next_action || '',
    })
    ElMessage.success('已保存跟进')
    fuForm.content = ''; fuForm.next_at = ''; fuForm.next_action = ''
    await loadFollow(followRow.value.id)
  } catch (e) {
    ElMessage.error('保存失败，请重试')
  } finally {
    fuSaving.value = false
  }
}

// ---- 穿透详情（2026-10-29 Boss 专项：创建/分配/跟进/成交全时间线）----
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailRow = ref(null)
const timeline = ref([])
async function openDetail(row) {
  detailRow.value = row
  detailVisible.value = true
  detailLoading.value = true
  timeline.value = []
  try {
    const r = await salesApi.leadTimeline(row.id)
    const d = r?.data || r || {}
    timeline.value = d.timeline || []
    if (d.name) detailRow.value = { ...detailRow.value, ...d }
  } catch (e) { /* 拦截器已提示 */ } finally { detailLoading.value = false }
}

// ---- 指派逻辑 ----
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
    const r = await http.get('/accounts/users/', { params: { page_size: 200 } })
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

<style scoped>
.fu-card { background: #f7f8fa; border-radius: 8px; padding: 10px 12px; }
.fu-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.fu-user { font-size: 12px; color: #606266; }
.fu-content { font-size: 13px; color: #303133; white-space: pre-wrap; }
.fu-next { font-size: 12px; color: #909399; margin-top: 4px; }
</style>
