<template>
  <div>
    <!-- ========== 已承接线索池（2026-11-03 Boss 指示：成交师专属，展示本人承接的全部线索） ========== -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>已承接线索池 · {{ viewAll ? '全部承接线索' : '我承接的线索' }}（{{ total }} 条）</span>
          <div>
            <el-select v-model="stageFilter" placeholder="全部阶段" clearable style="width: 140px" @change="loadData">
              <!-- 2026-11-05 修复：值必须用后端真实编码 S3/S5/S7/S0（原 0/1/3/5/7 全部筛不出数据） -->
              <el-option label="3 阶段" value="S3" />
              <el-option label="5 阶段" value="S5" />
              <el-option label="7 阶段" value="S7" />
              <el-option label="0 成交" value="S0" />
            </el-select>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" size="default" max-height="600">
        <el-table-column prop="lead_name" label="客户" min-width="130" />
        <el-table-column prop="lead_phone" label="电话" width="130" />
        <el-table-column label="来源平台" width="120">
          <template #default="{ row }"><el-tag size="small">{{ row.channel_name }}</el-tag></template>
        </el-table-column>
        <el-table-column label="录入人" width="100">
          <template #default="{ row }">
            <span v-if="row.creator_name">{{ row.creator_name }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="录入日期" width="150">
          <template #default="{ row }">{{ (row.created_at || '').slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="3570阶段" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.stage_3570" :type="stageTagType(row.stage_3570)" size="small">
              {{ row.stage_label }}
            </el-tag>
            <span v-else class="muted">未标记</span>
          </template>
        </el-table-column>
        <el-table-column prop="customer_need" label="客户需求" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.customer_need">{{ row.customer_need }}</span>
            <span v-else class="muted">未填写（点右侧编辑）</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="270" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openFollowups(row)">跟进记录</el-button>
            <el-button link type="success" @click="openStage(row)">标记阶段</el-button>
            <el-button link type="warning" @click="openNeed(row)">编辑需求</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 标记 / 修改阶段（2026-11-05 Boss 指示：标错了可以改） -->
    <el-dialog v-model="stageVisible" :title="stageRow?.stage_3570 ? '修改 3570 阶段' : '标记 3570 阶段'" width="360px">
      <el-alert type="info" :closable="false" show-icon style="margin-bottom: 12px"
                :title="`当前阶段：${stageRow?.stage_label || '未标记'}，标错了直接重新选一个再确认即可，系统保留变更记录`" />
      <el-radio-group v-model="stageForm.stage">
        <el-radio-button v-for="(label, val) in STAGE_3570" :key="val" :value="val">{{ label }}</el-radio-button>
      </el-radio-group>
      <template #footer>
        <el-button @click="stageVisible = false">取消</el-button>
        <el-button type="primary" :loading="stageSaving" @click="submitStage">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 客户需求编辑（2026-11-05 Boss 指示：需求列原来只读，现支持修改） -->
    <el-dialog v-model="needVisible" title="编辑客户需求" width="480px">
      <el-form label-width="80px">
        <el-form-item label="客户">{{ needRow?.lead_name }}</el-form-item>
        <el-form-item label="客户需求">
          <el-input v-model="needForm.customer_need" type="textarea" :rows="4"
                    placeholder="填写客户的具体需求，如：注册公司 / 代理记账 / 注销等" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="needVisible = false">取消</el-button>
        <el-button type="primary" :loading="needSaving" @click="submitNeed">保存需求</el-button>
      </template>
    </el-dialog>

    <!-- 跟进记录 -->
    <el-drawer v-model="fupVisible" :title="`跟进记录 · ${fupRow?.lead_name || ''}`" size="520px">
      <div v-loading="fupLoading">
        <el-empty v-if="!fups.length && !fupLoading" description="暂无跟进记录" :image-size="80" />
        <el-timeline v-if="fups.length" style="margin-bottom: 16px">
          <el-timeline-item v-for="f in fups" :key="f.id" :timestamp="(f.follow_at || '').slice(0, 16)">
            <div class="fup-item">
              <el-tag size="small" type="info">第{{ f.round_no }}轮 · {{ WAY_LABELS[f.way] || f.way }}</el-tag>
              <el-tag v-if="f.deal_happened" size="small" type="success" style="margin-left: 6px">成交 ¥{{ f.deal_amount }}</el-tag>
              <p class="fup-content">{{ f.content }}</p>
            </div>
          </el-timeline-item>
        </el-timeline>

        <el-divider content-position="left">新增跟进</el-divider>
        <el-form label-width="80px" size="default">
          <el-form-item label="跟进方式">
            <el-radio-group v-model="fupForm.way">
              <el-radio-button value="PHONE">电话</el-radio-button>
              <el-radio-button value="WECHAT">微信</el-radio-button>
              <el-radio-button value="VISIT">上门</el-radio-button>
              <el-radio-button value="OTHER">其他</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="跟进内容">
            <el-input v-model="fupForm.content" type="textarea" :rows="3" placeholder="本次沟通要点" />
          </el-form-item>
          <el-form-item label="是否成交">
            <el-switch v-model="fupForm.deal_happened" />
            <template v-if="fupForm.deal_happened">
              <el-input-number v-model="fupForm.deal_amount" :min="0" :controls="false"
                placeholder="成交金额" style="width: 140px; margin-left: 10px" />
              <span class="muted" style="margin-left: 6px">元</span>
            </template>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="fupSaving" @click="saveFollowup">保存跟进记录</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
// 2026-11-03 Boss 指示：成交师「已承接线索池」——只看本人承接（closer=我）的线索。
// 数据源复用 /growth/leads/（后端 scope_leads 权限隔离在前，closer 过滤在后，天然不越权）。
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { growthApi } from '@/api/growth'
import { useUserStore } from '@/store/user'

const store = useUserStore()

const list = ref([])
const loading = ref(false)
const total = ref(0)
const stageFilter = ref('')
// 管理层（can_view_all）可看全部承接线索；成交师仅看自己的
const viewAll = ref(false)

// 2026-11-05 修复「阶段值非法」：必须用后端 LeadExt.STAGE_3570 真实编码 S0/S3/S5/S7，
// 原来发的是 '0/1/3/5/7'，后端不识别直接 400；且后端本无「1 阶段」，一并移除。
const STAGE_3570 = { S3: '3 阶段', S5: '5 阶段', S7: '7 阶段', S0: '0 成交' }
const WAY_LABELS = { PHONE: '电话', WECHAT: '微信', VISIT: '上门', OTHER: '其他' }

const stageTagType = (s) => ({ S3: 'primary', S5: 'warning', S7: 'danger', S0: 'success' }[s] || 'info')

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (!viewAll.value) params.closer = store.userInfo?.id
    if (stageFilter.value) params.stage = stageFilter.value
    const res = await growthApi.leads(params)
    const body = Array.isArray(res) ? { results: res } : (res || {})
    list.value = body.results || []
    total.value = body.count ?? list.value.length
  } catch (e) { /* 拦截器已提示 */ } finally { loading.value = false }
}

// 2026-11-05 Boss 指示：承接池同样 30 秒轮询实时同步（页面隐藏时暂停）
let pollTimer = null
function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (document.visibilityState === 'visible' && !loading.value) loadData()
  }, 30000)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(async () => {
  try {
    const r = await growthApi.myRole()
    viewAll.value = !!r && !!r.can_view_all
  } catch (e) { /* ignore */ }
  loadData()
  startPolling()
})

onBeforeUnmount(stopPolling)

// ---------- 标记阶段 ----------
const stageVisible = ref(false)
const stageSaving = ref(false)
const stageRow = ref(null)
const stageForm = reactive({ stage: '' })

function openStage(row) {
  stageRow.value = row
  stageForm.stage = row.stage_3570 || ''
  stageVisible.value = true
}

async function submitStage() {
  if (!stageForm.stage) { ElMessage.warning('请选择阶段'); return }
  stageSaving.value = true
  try {
    await growthApi.setStage(stageRow.value.id, { stage: stageForm.stage })
    ElMessage.success('阶段已更新')
    stageVisible.value = false
    loadData()
  } catch (e) { /* 拦截器已提示 */ } finally { stageSaving.value = false }
}

// ---------- 客户需求编辑（2026-11-05 Boss 指示） ----------
const needVisible = ref(false)
const needSaving = ref(false)
const needRow = ref(null)
const needForm = reactive({ customer_need: '' })

function openNeed(row) {
  needRow.value = row
  needForm.customer_need = row.customer_need || ''
  needVisible.value = true
}

async function submitNeed() {
  needSaving.value = true
  try {
    await growthApi.updateLead(needRow.value.id, { customer_need: needForm.customer_need })
    ElMessage.success('客户需求已保存')
    needVisible.value = false
    loadData()
  } catch (e) { /* 拦截器已提示 */ } finally { needSaving.value = false }
}

// ---------- 跟进记录（查看 + 新增） ----------
const fupVisible = ref(false)
const fupRow = ref(null)
const fups = ref([])
const fupLoading = ref(false)
const fupSaving = ref(false)
const fupForm = reactive({ way: 'PHONE', content: '', deal_happened: false, deal_amount: 0 })

async function openFollowups(row) {
  fupRow.value = row
  fupVisible.value = true
  fupLoading.value = true
  try {
    const res = await growthApi.followups({ lead_ext: row.id, page_size: 50 })
    fups.value = Array.isArray(res) ? res : (res.results || [])
  } catch { fups.value = [] } finally { fupLoading.value = false }
  fupForm.way = 'PHONE'
  fupForm.content = ''
  fupForm.deal_happened = false
  fupForm.deal_amount = 0
}

async function saveFollowup() {
  if (!fupForm.content.trim()) { ElMessage.warning('请填写跟进内容'); return }
  fupSaving.value = true
  try {
    await growthApi.createFollowup({
      lead_ext: fupRow.value.id,
      round_no: Math.min((fups.value.length || 0) + 1, 3),
      way: fupForm.way,
      content: fupForm.content.trim(),
      follow_at: new Date().toISOString(),
      deal_happened: fupForm.deal_happened,
      deal_amount: fupForm.deal_happened ? (fupForm.deal_amount || 0) : 0,
    })
    ElMessage.success('跟进记录已保存')
    await openFollowups(fupRow.value)
  } finally { fupSaving.value = false }
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.fup-item .fup-content { margin: 6px 0 0; color: #444; line-height: 1.6; }
.muted { color: #aaa; }
</style>
