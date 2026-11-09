<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">线索公海</h2>
        <p class="page-sub">退回公海的数据可被重新领取；管理层可直接分配给指定人员，或把已领取线索再分配</p>
      </div>
      <div class="page-actions">
        <el-radio-group v-model="statusFilter" @change="loadData">
          <el-radio-button label="WAITING">待承接</el-radio-button>
          <el-radio-button label="CLAIMED">已承接</el-radio-button>
          <el-radio-button label="">全部</el-radio-button>
        </el-radio-group>
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
      </div>
    </div>

    <!-- 顶部指标 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <div class="stat-card accent-warning">
          <div class="label">待承接（公海）</div>
          <div class="value">{{ waiting }}</div>
          <div class="sub">可被成交师领取或管理层分配</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card accent-success">
          <div class="label">已承接</div>
          <div class="value">{{ claimed }}</div>
          <div class="sub">已被认领跟进</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="label">退回次数总计</div>
          <div class="value">{{ totalReturnCount }}</div>
          <div class="sub">累计被退回公海次数</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card accent-primary">
          <div class="label">我的角色</div>
          <div class="value small">{{ roleLabel }}</div>
          <div class="sub">{{ canAssign ? '可分配 / 再分配' : (canClaim ? '可领取' : '仅查看') }}</div>
        </div>
      </el-col>
    </el-row>

    <div class="card">
      <div class="toolbar">
        <el-input v-model="filters.q" placeholder="搜索客户 / 电话" clearable style="width:220px" :prefix-icon="Search" @keyup.enter="loadData" />
        <el-select v-model="filters.channel" placeholder="全部平台" clearable style="width:160px">
          <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
        <el-button text @click="resetFilters">重置</el-button>
      </div>

      <el-table :data="list" v-loading="loading" size="default" max-height="600">
        <el-table-column prop="lead_name" label="客户" min-width="130" />
        <el-table-column prop="lead_phone" label="电话" width="130" />
        <!-- 2026-11-03 Boss 指示：线索池增加「录入人」列 -->
        <el-table-column label="录入人" width="100">
          <template #default="{ row }">
            <span v-if="row.creator_name">{{ row.creator_name }}</span>
            <span v-else class="text-weak">—</span>
          </template>
        </el-table-column>
        <el-table-column label="来源平台" width="120">
          <template #default="{ row }"><el-tag size="small" effect="plain">{{ row.channel_name }}</el-tag></template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="row.status === 'WAITING' ? 'warning' : 'success'" effect="light">
              {{ row.status_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="returned_by_name" label="退回人" width="100" />
        <el-table-column label="退回原因" min-width="160">
          <template #default="{ row }">
            <span v-if="row.returned_reason">{{ row.returned_reason }}</span>
            <span v-else class="text-weak">—</span>
          </template>
        </el-table-column>
        <el-table-column label="领取次数" width="92" align="center">
          <template #default="{ row }">{{ row.claim_count || 0 }}</template>
        </el-table-column>
        <el-table-column prop="claimed_by_name" label="领取人" width="100" />
        <el-table-column label="退回时间" width="160">
          <template #default="{ row }"><span class="text-weak">{{ fmt(row.returned_at) }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'WAITING' && canClaim" link type="primary" @click="doClaim(row)">领取</el-button>
            <el-button v-if="canAssign" link type="warning" @click="openAssign(row)">
              {{ row.status === 'WAITING' ? '分配' : '再分配' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

    </div>

    <!-- 分配 / 再分配 -->
    <el-dialog v-model="assignVisible" :title="assignForm.status === 'WAITING' ? '公海分配' : '再分配'" width="480px">
      <el-form label-width="88px">
        <el-form-item label="线索">
          <span class="strong">{{ assignForm.lead_name }}</span>
          <span class="text-weak" style="margin-left:8px">{{ assignForm.lead_phone }}</span>
        </el-form-item>
        <el-form-item label="当前归属">
          <span class="text-weak">{{ assignForm.current || '公海待领取' }}</span>
        </el-form-item>
        <el-form-item label="分配给" required>
          <PersonSelect v-model="assignForm.closer_id" placeholder="选择人员，或输入姓名新增" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="assignForm.remark" type="textarea" :rows="2" placeholder="可填分配说明，如「该单属抖音渠道，指定小王跟进」" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitAssign">确认分配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { growthApi } from '@/api/growth'
import PersonSelect from '@/components/PersonSelect.vue'

const list = ref([])
const channels = ref([])
const loading = ref(false)
const submitting = ref(false)
const statusFilter = ref('WAITING')
const roleLabel = ref('未配置')
const canClaim = ref(false)
const canAssign = ref(false)

const filters = reactive({ channel: '', q: '' })
const stats = reactive({ waiting: 0, claimed: 0, ret: 0 })
const assignVisible = ref(false)
const assignForm = reactive({ lead_ext: null, lead_name: '', lead_phone: '', current: '', closer_id: null, status: 'WAITING', remark: '' })

const waiting = computed(() => stats.waiting)
const claimed = computed(() => stats.claimed)
const totalReturnCount = computed(() => stats.ret)

function fmt(t) { return t ? String(t).slice(0, 19).replace('T', ' ') : '' }

async function loadChannels() {
  try {
    const res = await growthApi.channels()
    channels.value = Array.isArray(res) ? res : (res.results || [])
  } catch (e) {}
}

async function loadStats() {
  try {
    const r = await growthApi.poolStats()
    stats.waiting = r?.waiting || 0
    stats.claimed = r?.claimed || 0
    stats.ret = r?.return_count || 0
  } catch (e) {}
}

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (filters.channel) params.channel = filters.channel
    const res = await growthApi.pool(params)
    let rows = Array.isArray(res) ? res : (res.results || [])
    const q = filters.q.trim().toLowerCase()
    if (q) rows = rows.filter(r => `${r.lead_name || ''}${r.lead_phone || ''}`.toLowerCase().includes(q))
    list.value = rows
    loadStats()
  } finally {
    loading.value = false
  }
}

async function loadRole() {
  try {
    const r = await growthApi.myRole()
    if (!r) { roleLabel.value = '未配置'; canClaim.value = false; canAssign.value = false; return }
    roleLabel.value = r.has_role ? r.role_label : (r.can_view_all ? '超级总账号' : '未配置')
    canClaim.value = (!!(r.has_role && r.role === 'CLOSER')) || !!r.can_view_all
    // 2026-11-03：管理层 或 单点授权 can_assign_leads 均可分配
    canAssign.value = !!r.can_view_all || !!r.can_assign_leads
  } catch (e) {}
}

async function doClaim(row) {
  try {
    await growthApi.claimLead(row.lead_ext)
    ElMessage.success('已承接，线索已进入我的线索池')
    loadData()
  } catch (e) {}
}

function openAssign(row) {
  Object.assign(assignForm, {
    lead_ext: row.lead_ext,
    lead_name: row.lead_name || '-',
    lead_phone: row.lead_phone || '',
    current: row.claimed_by_name || '',
    closer_id: null,
    status: row.status,
    remark: ''
  })
  assignVisible.value = true
}

async function submitAssign() {
  if (!assignForm.closer_id) return ElMessage.warning('请选择要分配的人员')
  submitting.value = true
  try {
    await growthApi.assignLead(assignForm.lead_ext, {
      closer_id: assignForm.closer_id,
      remark: assignForm.remark
    })
    ElMessage.success(assignForm.status === 'WAITING' ? '已分配，移出公海' : '已再分配')
    assignVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

function resetFilters() {
  filters.channel = ''
  filters.q = ''
  loadData()
}

onMounted(() => {
  loadChannels()
  loadRole()
  loadData()
})
</script>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 18px; }
.page-actions { display: flex; gap: 10px; align-items: center; }
.stat-row { margin-bottom: 16px; }
.stat-card .value.small { font-size: 20px; }
.strong { font-weight: 600; }
</style>
