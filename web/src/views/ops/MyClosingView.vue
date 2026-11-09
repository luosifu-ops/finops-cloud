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
              <!-- 2026-11-09 Boss 指示：增加「无需求」阶段 -->
              <el-option label="无需求" value="SN" />
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
        <el-table-column label="操作" width="430" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openFollowups(row)">跟进记录</el-button>
            <el-button link type="success" @click="openStage(row)">标记阶段</el-button>
            <el-button link type="warning" @click="openNeed(row)">编辑需求</el-button>
            <!-- 2026-11-09 Boss 指示：已承接线索池同步增加线索池的编辑功能 -->
            <el-button link type="primary" @click="openEdit(row)">编辑线索</el-button>
            <!-- 2026-11-09 二批：退回公海 / 删除线索 -->
            <el-button link type="warning" @click="doReturn(row)">退回公海</el-button>
            <el-button link type="danger" @click="removeLead(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 标记 / 修改 / 取消阶段（2026-11-09 Boss 指示：标错了可改可取消，另有「无需求」阶段） -->
    <el-dialog v-model="stageVisible" :title="stageRow?.stage_3570 ? '修改 3570 阶段' : '标记 3570 阶段'" width="360px">
      <el-alert type="info" :closable="false" show-icon style="margin-bottom: 12px"
                :title="`当前阶段：${stageRow?.stage_label || '未标记'}，标错了直接重新选一个再确认即可，系统保留变更记录`" />
      <el-radio-group v-model="stageForm.stage">
        <el-radio-button v-for="(label, val) in STAGE_3570" :key="val" :value="val">{{ label }}</el-radio-button>
      </el-radio-group>
      <template #footer>
        <el-popconfirm title="确认取消该线索的阶段标记？（变更留痕，可重新标记）"
                       confirm-button-text="确认取消" cancel-button-text="再想想"
                       @confirm="clearStage">
          <template #reference>
            <el-button v-if="stageRow?.stage_3570" type="danger" plain>取消标记</el-button>
          </template>
        </el-popconfirm>
        <el-button @click="stageVisible = false">关 闭</el-button>
        <el-button type="primary" :loading="stageSaving" @click="submitStage">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 编辑线索（2026-11-09 Boss 指示：与线索池编辑功能对齐） -->
    <el-dialog v-model="editVisible" title="编辑线索" width="620px">
      <el-alert type="info" :closable="false" show-icon
                title="仅修改录入信息；保存后写入操作日志留痕" />
      <el-form :model="editForm" label-width="110px" style="margin-top:12px">
        <el-form-item label="客户姓名" required>
          <el-input v-model="editForm.name" placeholder="客户姓名" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="editForm.phone" placeholder="联系电话" />
        </el-form-item>
        <el-form-item label="意向业务">
          <el-input v-model="editForm.intention" placeholder="如：注册公司 / 代理记账 / 注销" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="editForm.contact_person" placeholder="对接人姓名" />
        </el-form-item>
        <el-form-item label="客户需求">
          <el-input v-model="editForm.customer_need" type="textarea" :rows="2" placeholder="客户具体需求" />
        </el-form-item>
        <!-- 2026-11-09 Boss 指示：加入编辑日期（录入日期可修正） -->
        <el-form-item label="录入日期">
          <el-date-picker v-model="editForm.created_at" type="datetime" style="width: 100%"
            value-format="YYYY-MM-DDTHH:mm:ss" placeholder="修正线索的实际录入时间" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editing" @click="submitEdit">保存修改</el-button>
      </template>
    </el-dialog>

    <!-- 客户需求编辑（2026-11-09 Boss 指示：编辑需求更加完善 + 支持编辑录入日期） -->
    <el-dialog v-model="needVisible" title="编辑客户需求" width="520px">
      <el-form label-width="90px">
        <el-form-item label="客户">{{ needRow?.lead_name }}</el-form-item>
        <el-form-item label="客户需求">
          <el-input v-model="needForm.customer_need" type="textarea" :rows="4"
                    placeholder="填写客户的具体需求，如：注册公司 / 代理记账 / 注销等" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="意向业务">
          <el-input v-model="needForm.intention" placeholder="如：注册公司 / 代理记账 / 注销" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="needForm.contact_person" placeholder="对接人姓名" />
        </el-form-item>
        <el-form-item label="成交金额">
          <el-input-number v-model="needForm.deal_amount" :min="0" :precision="2" :controls="false" style="width: 200px" />
          <span class="muted" style="margin-left: 8px">元</span>
        </el-form-item>
        <el-form-item label="获客成本">
          <el-input-number v-model="needForm.acquisition_cost" :min="0" :precision="2" :controls="false" style="width: 200px" />
          <span class="muted" style="margin-left: 8px">元</span>
        </el-form-item>
        <el-form-item label="录入日期">
          <el-date-picker v-model="needForm.created_at" type="datetime" style="width: 100%"
            value-format="YYYY-MM-DDTHH:mm:ss" placeholder="修正线索的实际录入时间" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="needVisible = false">取消</el-button>
        <el-button type="primary" :loading="needSaving" @click="submitNeed">保存需求</el-button>
      </template>
    </el-dialog>

    <!-- 跟进记录（2026-11-09 Boss 指示：升级为完整跟进页面——查看/新增/编辑/删除） -->
    <el-drawer v-model="fupVisible" :title="`跟进记录 · ${fupRow?.lead_name || ''}`" size="560px">
      <div v-loading="fupLoading">
        <el-empty v-if="!fups.length && !fupLoading" description="暂无跟进记录" :image-size="80" />
        <el-timeline v-if="fups.length" style="margin-bottom: 16px">
          <el-timeline-item v-for="f in fups" :key="f.id" :timestamp="(f.follow_at || '').slice(0, 16)"
            :type="f.deal_happened ? 'success' : 'primary'">
            <div class="fup-item">
              <div class="fup-head">
                <el-tag size="small" type="info">第{{ f.round_no }}轮 · {{ WAY_LABELS[f.way] || f.way }}</el-tag>
                <el-tag v-if="f.deal_happened" size="small" type="success" style="margin-left: 6px">成交 ¥{{ f.deal_amount }}</el-tag>
                <span class="fup-ops">
                  <el-button link type="primary" size="small" @click="editFollowup(f)">编辑</el-button>
                  <el-button link type="danger" size="small" @click="removeFollowup(f)">删除</el-button>
                </span>
              </div>
              <p class="fup-content">{{ f.content }}</p>
            </div>
          </el-timeline-item>
        </el-timeline>

        <el-divider content-position="left">{{ fupEditingId ? '编辑本次跟进' : '新增跟进' }}</el-divider>
        <el-form label-width="80px" size="default">
          <el-form-item label="跟进轮次">
            <el-select v-model="fupForm.round_no" style="width: 100%">
              <el-option label="第一次跟进" :value="1" />
              <el-option label="第二次跟进" :value="2" />
              <el-option label="第三次跟进" :value="3" />
            </el-select>
          </el-form-item>
          <el-form-item label="跟进方式">
            <el-radio-group v-model="fupForm.way">
              <el-radio-button value="PHONE">电话</el-radio-button>
              <el-radio-button value="WECHAT">微信</el-radio-button>
              <el-radio-button value="VISIT">上门</el-radio-button>
              <el-radio-button value="OTHER">其他</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="跟进时间">
            <el-date-picker v-model="fupForm.follow_at" type="datetime" style="width: 100%"
              value-format="YYYY-MM-DDTHH:mm:ss" placeholder="默认当前时间" />
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
            <el-button type="primary" :loading="fupSaving" @click="saveFollowup">
              {{ fupEditingId ? '保存修改' : '保存跟进记录' }}
            </el-button>
            <el-button v-if="fupEditingId" @click="resetFollowupForm">取消编辑</el-button>
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
import { ElMessage, ElMessageBox } from 'element-plus'
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
// 2026-11-09：新增「无需求(SN)」阶段（有的客户不属于 3/5/7/0）
const STAGE_3570 = { S3: '3 阶段', S5: '5 阶段', S7: '7 阶段', S0: '0 成交', SN: '无需求' }
const WAY_LABELS = { PHONE: '电话', WECHAT: '微信', VISIT: '上门', MEETING: '会议', OTHER: '其他' }

const stageTagType = (s) => ({ S3: 'primary', S5: 'warning', S7: 'danger', S0: 'success', SN: 'danger' }[s] || 'info')

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

// 2026-11-09 Boss 指示：取消 3570 标记（标记错了可撤，变更留痕）
async function clearStage() {
  try {
    await growthApi.setStage(stageRow.value.id, { stage: '', remark: '取消标记' })
    ElMessage.success('已取消标记')
    stageVisible.value = false
    loadData()
  } catch (e) { /* 拦截器已提示 */ }
}

// ---------- 编辑线索（2026-11-09 Boss 指示：与线索池编辑功能对齐） ----------
const editVisible = ref(false)
const editing = ref(false)
const editRow = ref(null)
const editForm = reactive({
  name: '', phone: '', intention: '', contact_person: '', customer_need: '',
  created_at: '',
})

function openEdit(row) {
  if (!row) return
  editRow.value = row
  Object.assign(editForm, {
    name: row.lead_name || '',
    phone: row.lead_phone || '',
    intention: row.lead_intention || '',
    contact_person: row.contact_person || '',
    customer_need: row.customer_need || '',
    created_at: (row.created_at || '').slice(0, 19) || '',
  })
  editVisible.value = true
}

async function submitEdit() {
  if (!String(editForm.name || '').trim()) return ElMessage.warning('请填写客户姓名')
  editing.value = true
  try {
    const payload = { ...editForm }
    if (!payload.created_at) delete payload.created_at
    const r = await growthApi.updateLead(editRow.value.id, payload)
    ElMessage.success(r?.detail || '已保存修改')
    editVisible.value = false
    loadData()
  } catch (e) { /* 拦截器已提示 */ } finally {
    editing.value = false
  }
}

// ---------- 客户需求编辑（2026-11-09 Boss 指示：编辑需求更加完善 + 录入日期可修正） ----------
const needVisible = ref(false)
const needSaving = ref(false)
const needRow = ref(null)
const needForm = reactive({
  customer_need: '', intention: '', contact_person: '',
  deal_amount: 0, acquisition_cost: 0, created_at: '',
})

function openNeed(row) {
  needRow.value = row
  Object.assign(needForm, {
    customer_need: row.customer_need || '',
    intention: row.lead_intention || '',
    contact_person: row.contact_person || '',
    deal_amount: Number(row.deal_amount || 0),
    acquisition_cost: Number(row.acquisition_cost || 0),
    created_at: (row.created_at || '').slice(0, 19) || '',
  })
  needVisible.value = true
}

async function submitNeed() {
  needSaving.value = true
  try {
    const payload = {
      customer_need: needForm.customer_need,
      intention: needForm.intention,
      contact_person: needForm.contact_person,
      deal_amount: needForm.deal_amount || 0,
      acquisition_cost: needForm.acquisition_cost || 0,
    }
    if (needForm.created_at) payload.created_at = needForm.created_at
    await growthApi.updateLead(needRow.value.id, payload)
    ElMessage.success('客户需求已保存')
    needVisible.value = false
    loadData()
  } catch (e) { /* 拦截器已提示 */ } finally { needSaving.value = false }
}

// ---------- 2026-11-09 二批：退回公海 / 删除线索 ----------
async function doReturn(row) {
  const { value } = await ElMessageBox.prompt('填写退回原因', '退回公海', {
    inputPlaceholder: '如：客户失联 / 无法跟进', inputValue: '',
  }).catch(() => ({ value: null }))
  if (value === null) return
  try {
    await growthApi.returnPool(row.id, { reason: value || '无法跟进' })
    ElMessage.success('已退回公海，可二次分配')
    loadData()
  } catch (e) { /* 拦截器已提示 */ }
}

async function removeLead(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除线索「${row.lead_name || '-'}」？删除后不再出现在线索池与公海，历史留痕保留。`,
      '删除线索', { type: 'warning', confirmButtonText: '确认删除', confirmButtonClass: 'el-button--danger' }
    )
  } catch { return }
  try {
    await growthApi.deleteLead(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) { /* 拦截器已提示 */ }
}

// ---------- 跟进记录（2026-11-09 升级：查看/新增/编辑/删除，与线索池跟进对齐） ----------
const fupVisible = ref(false)
const fupRow = ref(null)
const fups = ref([])
const fupLoading = ref(false)
const fupSaving = ref(false)
const fupEditingId = ref(null)
const fupForm = reactive({
  round_no: 1, way: 'PHONE', follow_at: '', content: '',
  deal_happened: false, deal_amount: 0,
})

async function openFollowups(row) {
  fupRow.value = row
  fupVisible.value = true
  fupLoading.value = true
  fupEditingId.value = null
  try {
    const res = await growthApi.followups({ lead_ext: row.id, page_size: 50 })
    fups.value = Array.isArray(res) ? res : (res.results || [])
  } catch { fups.value = [] } finally { fupLoading.value = false }
  resetFollowupForm()
}

function resetFollowupForm() {
  fupEditingId.value = null
  fupForm.round_no = fups.value.length ? Math.min(fups.value.length + 1, 3) : 1
  fupForm.way = 'PHONE'
  fupForm.follow_at = ''
  fupForm.content = ''
  fupForm.deal_happened = false
  fupForm.deal_amount = 0
}

function editFollowup(f) {
  fupEditingId.value = f.id
  fupForm.round_no = f.round_no
  fupForm.way = f.way
  fupForm.follow_at = f.follow_at || ''
  fupForm.content = f.content
  fupForm.deal_happened = !!f.deal_happened
  fupForm.deal_amount = Number(f.deal_amount || 0)
}

async function saveFollowup() {
  if (!fupForm.content.trim()) { ElMessage.warning('请填写跟进内容'); return }
  fupSaving.value = true
  try {
    const payload = {
      lead_ext: fupRow.value.id,
      round_no: fupForm.round_no,
      way: fupForm.way,
      content: fupForm.content.trim(),
      follow_at: fupForm.follow_at || new Date().toISOString(),
      deal_happened: fupForm.deal_happened,
      deal_amount: fupForm.deal_happened ? (fupForm.deal_amount || 0) : 0,
    }
    if (fupEditingId.value) {
      await growthApi.updateFollowup(fupEditingId.value, payload)
      ElMessage.success('跟进记录已更新')
    } else {
      await growthApi.createFollowup(payload)
      ElMessage.success('跟进记录已保存')
    }
    await openFollowups(fupRow.value)
    loadData()
  } finally { fupSaving.value = false }
}

async function removeFollowup(f) {
  try {
    await ElMessageBox.confirm('确认删除这条跟进记录？', '删除确认', { type: 'warning' })
  } catch { return }
  await growthApi.deleteFollowup(f.id)
  ElMessage.success('已删除')
  await openFollowups(fupRow.value)
  loadData()
}
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.fup-item .fup-head { display: flex; align-items: center; gap: 6px; }
.fup-item .fup-ops { margin-left: auto; }
.fup-item .fup-content { margin: 6px 0 0; color: #444; line-height: 1.6; white-space: pre-wrap; }
.muted { color: #aaa; }
</style>
