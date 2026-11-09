<template>
  <div class="growth-page">
    <!-- 顶部指标条 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">我的录入</div>
          <div class="mini-value">{{ total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">待承接（公海）</div>
          <div class="mini-value warn">{{ poolWaiting }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">已成交（0阶段）</div>
          <div class="mini-value ok">{{ dealCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">我的角色</div>
          <div class="mini-value small">{{ roleLabel }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作区 -->
    <el-card shadow="never" class="main-card">
      <template #header>
        <div class="card-header">
          <span>线索工作台 · 多平台录入与全链路流转</span>
          <div>
            <!-- 2026-10-30 Boss 专项：批量按钮永远可点，未勾选时点击给出引导提示（不再置灰） -->
            <!-- 2026-11-03：分配入口改由 canAssign 控制（管理层 或 单点授权 can_assign_leads） -->
            <el-button v-if="canAssign" type="warning" plain
              @click="openBulkAssign">批量分配{{ selected.length ? `(${selected.length})` : '' }}</el-button>
            <el-button v-if="canCreateLead" type="primary" @click="openCreate">+ 录入线索</el-button>
            <el-button @click="goPool">公海 →</el-button>
            <el-button @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选 -->
      <el-form :inline="true" size="default" class="filter-bar">
        <!-- 2026-11-03 Boss 指示：承接状态筛选（待承接 / 已承接） -->
        <el-form-item label="承接状态">
          <el-select v-model="filters.closing" placeholder="全部" clearable style="width:120px">
            <el-option label="待承接" value="waiting" />
            <el-option label="已承接" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="filters.channel" placeholder="全部平台" clearable style="width:140px">
            <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="3570阶段">
          <el-select v-model="filters.stage" placeholder="全部" clearable style="width:120px">
            <el-option label="3阶段" value="S3" />
            <el-option label="5阶段" value="S5" />
            <el-option label="7阶段" value="S7" />
            <el-option label="0成交" value="S0" />
            <!-- 2026-11-09 Boss 指示：有的客户不属于 3/5/7/0，增加「无需求」 -->
            <el-option label="无需求" value="SN" />
          </el-select>
        </el-form-item>
        <!-- 2026-11-09 Boss 指示：线索池增加「录入人」筛选，支持多选 -->
        <el-form-item label="录入人">
          <el-select v-model="filters.creators" placeholder="全部录入人" clearable multiple
                     collapse-tags filterable style="width:200px">
            <el-option v-for="u in creatorUsers" :key="u.id" :label="u.name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" plain @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table :data="list" v-loading="loading" border stripe size="default"
        @selection-change="(rows) => (selected = rows)">
        <el-table-column v-if="canAssign" type="selection" width="42" fixed="left" />
        <el-table-column prop="lead_name" label="客户" min-width="120" />
        <el-table-column prop="lead_phone" label="电话" width="130" />
        <!-- 2026-11-02 Boss 指示：显示录入日期（后端 created_at = 实际录入时间，存量线索自带） -->
        <el-table-column label="录入日期" width="150">
          <template #default="{ row }">
            <span>{{ (row.created_at || '').slice(0, 16) }}</span>
          </template>
        </el-table-column>
        <!-- 2026-11-03 Boss 指示：线索池增加「录入人」列 -->
        <el-table-column label="录入人" width="100">
          <template #default="{ row }">
            <span v-if="row.creator_name">{{ row.creator_name }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="来源平台" width="110">
          <template #default="{ row }">
            <el-tag size="small">{{ row.channel_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_account_no" label="来源账号" width="130" />
        <el-table-column prop="ops_owner_name" label="归属运营" width="110" />
        <el-table-column prop="closer_name" label="承接人" width="110">
          <template #default="{ row }">
            <span v-if="row.closer_name">{{ row.closer_name }}</span>
            <el-tag v-else-if="row.in_pool" type="warning" size="small">公海待承接</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="3570阶段" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.stage_3570" :type="stageTagType(row.stage_3570)" size="small">
              {{ row.stage_label }}
            </el-tag>
            <span v-else class="muted">未标记</span>
          </template>
        </el-table-column>
        <!-- 2026-11-02 Boss 指示：成交师可见——成交后显示承接成交的人 -->
        <el-table-column label="成交师" width="140">
          <template #default="{ row }">
            <template v-if="row.is_deal">
              <el-tag type="success" size="small">已成交</el-tag>
              <span class="closer-name">{{ row.closer_name || '-' }}</span>
            </template>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" :width="isOpsPool ? 520 : 410" fixed="right">
          <template #default="{ row }">
            <el-button v-if="canAssign" link type="danger" @click="openAssign(row)">分配</el-button>
            <el-button v-if="canModifyLead(row)" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="primary" @click="openStage(row)">标记阶段</el-button>
            <!-- 2026-11-02 Boss 指示：跟进记录查看/编辑（时间线 + 新增） -->
            <el-button link type="primary" @click="openFollowups(row)">跟进</el-button>
            <el-button link type="success" @click="doAccept(row)">承接</el-button>
            <el-button link type="warning" @click="doReturn(row)">退公海</el-button>
            <el-button link @click="openFlows(row)">流转</el-button>
            <el-button v-if="canModifyLead(row)" link type="danger" @click="removeLead(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 录入对话框 -->
    <el-dialog v-model="createVisible" title="录入线索（多平台）" width="620px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="来源平台" required>
          <el-select v-model="form.channel" placeholder="选择投放平台" style="width:100%">
            <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源账号编号" required>
          <el-input v-model="form.source_account_no" placeholder="如 DY-ACC-001，用于多账号区分" />
        </el-form-item>
        <el-form-item label="客户姓名" required>
          <el-input v-model="form.name" placeholder="客户姓名" />
        </el-form-item>
        <el-form-item label="联系方式" required>
          <el-select v-model="form.contact_type" style="width:110px">
            <el-option label="电话" value="PHONE" />
            <el-option label="微信" value="WECHAT" />
          </el-select>
          <el-input v-model="form.phone" placeholder="电话" style="width:150px;margin-left:8px" />
          <el-input v-model="form.wechat" placeholder="微信" style="width:150px;margin-left:8px" />
        </el-form-item>
        <el-form-item label="公司名称">
          <el-input v-model="form.company" />
        </el-form-item>
        <el-form-item label="意向业务">
          <el-input v-model="form.intention" placeholder="如：注册公司 / 代理记账 / 注销" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
        <el-alert type="info" :closable="false" show-icon
                  title="提交后线索进入公海待承接，由管理层分配或成交师自行领取（系统不再自动派单）" />
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">提交并流转</el-button>
      </template>
    </el-dialog>

    <!-- 3570 标记 / 编辑 / 取消（2026-11-09 Boss 指示：标错了可改可取消，另有「无需求」阶段） -->
    <el-dialog v-model="stageVisible" :title="current?.stage_3570 ? '编辑 3570 阶段' : '标记 3570 阶段'" width="420px">
      <el-form label-width="90px">
        <el-form-item label="客户">{{ current?.lead_name }}</el-form-item>
        <el-form-item label="阶段">
          <el-radio-group v-model="stageValue">
            <el-radio-button label="S3">3阶段</el-radio-button>
            <el-radio-button label="S5">5阶段</el-radio-button>
            <el-radio-button label="S7">7阶段</el-radio-button>
            <el-radio-button label="S0">0成交</el-radio-button>
            <el-radio-button label="SN">无需求</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="stageRemark" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-popconfirm title="确认取消该线索的阶段标记？（变更留痕，可重新标记）"
                       confirm-button-text="确认取消" cancel-button-text="再想想"
                       @confirm="clearStage">
          <template #reference>
            <el-button v-if="current?.stage_3570" type="danger" plain>取消标记</el-button>
          </template>
        </el-popconfirm>
        <el-button @click="stageVisible = false">关 闭</el-button>
        <el-button type="primary" @click="submitStage">确定</el-button>
      </template>
    </el-dialog>

    <!-- 流转记录 -->
    <el-dialog v-model="flowVisible" title="线索流转记录" width="560px">
      <el-timeline>
        <el-timeline-item v-for="f in flows" :key="f.id" :timestamp="fmt(f.created_at)" placement="top">
          <strong>{{ f.action_label }}</strong>
          <div class="muted">{{ f.from_user_name || '系统' }} → {{ f.to_user_name || '-' }} {{ f.remark ? '· ' + f.remark : '' }}</div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-if="!flows.length" description="暂无流转记录" />
    </el-dialog>

    <!-- 编辑线索（2026-10-30：运营部线索池录入出错可改） -->
    <el-dialog v-model="editVisible" title="编辑线索" width="620px">
      <el-alert type="info" :closable="false" show-icon
                title="仅修改录入信息，归属运营 / 承接人请走「分配」；保存后写入操作日志留痕" />
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
        <el-form-item label="来源平台">
          <el-select v-model="editForm.channel" placeholder="选择平台" style="width:100%">
            <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源账号编号">
          <el-input v-model="editForm.source_account_no" placeholder="如 DY-ACC-001" />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-select v-model="editForm.contact_type" style="width:110px">
            <el-option label="电话" value="PHONE" />
            <el-option label="微信" value="WECHAT" />
          </el-select>
          <el-input v-model="editForm.contact_value" placeholder="联系方式" style="width:240px;margin-left:8px" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="editForm.contact_person" placeholder="对接人姓名" />
        </el-form-item>
        <el-form-item label="客户需求">
          <el-input v-model="editForm.customer_need" type="textarea" :rows="2" placeholder="客户具体需求" />
        </el-form-item>
        <el-form-item label="成交金额">
          <el-input-number v-model="editForm.deal_amount" :min="0" :precision="2" style="width:200px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editing" @click="submitEdit">保存修改</el-button>
      </template>
    </el-dialog>

    <!-- 管理层分配 -->
    <el-dialog v-model="assignVisible" title="管理层分配线索" width="480px">
      <el-alert type="info" :closable="false" show-icon
                title="仅管理层可见：把线索指派给某运营（归属）或成交师（承接），分配后移出公海并留痕" />
      <el-form label-width="100px" style="margin-top:12px">
        <el-form-item label="客户">{{ current?.lead_name }}</el-form-item>
        <el-form-item label="归属运营">
          <el-select v-model="assignForm.owner_id" placeholder="不改动运营" clearable filterable
                     :loading="staffLoading" style="width:100%">
            <el-option v-for="u in opsUsers" :key="u.id" :label="u.name" :value="u.id">
              <span>{{ u.name }}</span>
              <span class="opt-dept">{{ u.dept }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="承接人">
          <el-select v-model="assignForm.closer_id" placeholder="不改动承接人" clearable filterable
                     :loading="staffLoading" style="width:100%">
            <el-option v-for="u in closerUsers" :key="u.id" :label="u.name" :value="u.id">
              <span>{{ u.name }}</span>
              <span class="opt-dept">{{ u.dept }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="assignForm.remark" placeholder="选填，如：转交王经理跟进" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="assigning" @click="submitAssign">确认分配</el-button>
      </template>
    </el-dialog>

    <!-- 批量分配 -->
    <el-dialog v-model="bulkVisible" title="批量分配线索" width="480px">
      <el-alert type="info" :closable="false" show-icon
                :title="`已勾选 ${selected.length} 条线索，将统一指派并移出公海、逐条留痕`" />
      <el-form label-width="100px" style="margin-top:12px">
        <el-form-item label="归属运营">
          <el-select v-model="bulkForm.owner_id" placeholder="不改动运营" clearable filterable
                     :loading="staffLoading" style="width:100%">
            <el-option v-for="u in opsUsers" :key="u.id" :label="u.name" :value="u.id">
              <span>{{ u.name }}</span>
              <span class="opt-dept">{{ u.dept }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="承接人">
          <el-select v-model="bulkForm.closer_id" placeholder="不改动承接人" clearable filterable
                     :loading="staffLoading" style="width:100%">
            <el-option v-for="u in closerUsers" :key="u.id" :label="u.name" :value="u.id">
              <span>{{ u.name }}</span>
              <span class="opt-dept">{{ u.dept }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="bulkForm.remark" placeholder="选填，如：本批新渠道线索统一交由张三" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bulkVisible = false">取消</el-button>
        <el-button type="primary" :loading="bulkAssigning" @click="submitBulkAssign">确认批量分配</el-button>
      </template>
    </el-dialog>

    <!-- 2026-11-02 Boss 指示：跟进记录抽屉（时间线查看 + 新增/编辑，管理层可见全过程） -->
    <el-drawer v-model="fupVisible" :title="`跟进记录 · ${fupRow?.lead_name || ''}`" size="560px">
      <div class="fup-wrap">
        <el-alert type="info" :closable="false" show-icon
          :title="`当前阶段：${fupRow?.stage_label || '未标记'}　承接人：${fupRow?.closer_name || '公海待承接'}　状态：${statusLabel(fupRow?.lead_status)}`" />
        <el-timeline v-loading="fupLoading" class="fup-timeline">
          <el-timeline-item v-for="f in fups" :key="f.id"
            :timestamp="`${f.follow_at || f.created_at} · ${f.way_label}`" placement="top"
            :type="f.deal_happened ? 'success' : 'primary'">
            <div class="fup-item">
              <div class="fup-head">
                <b>{{ f.round_label }}</b>
                <el-tag v-if="f.deal_happened" type="success" size="small">本次成交 ¥{{ f.deal_amount }}</el-tag>
                <span class="fup-ops">
                  <el-button link type="primary" size="small" @click="editFollowup(f)">编辑</el-button>
                  <el-button v-if="canModifyLead(fupRow)" link type="danger" size="small" @click="removeFollowup(f)">删除</el-button>
                </span>
              </div>
              <div class="fup-content">{{ f.content }}</div>
            </div>
          </el-timeline-item>
          <el-empty v-if="!fupLoading && !fups.length" description="暂无跟进记录，录入第一条" :image-size="80" />
        </el-timeline>

        <el-divider content-position="left">{{ fupEditingId ? '编辑本次跟进' : '新增跟进记录' }}</el-divider>
        <el-form label-width="86px" class="fup-form">
          <el-form-item label="跟进轮次">
            <el-select v-model="fupForm.round_no" style="width: 100%">
              <el-option label="第一次跟进" :value="1" />
              <el-option label="第二次跟进" :value="2" />
              <el-option label="第三次跟进" :value="3" />
            </el-select>
          </el-form-item>
          <el-form-item label="跟进方式">
            <el-radio-group v-model="fupForm.way">
              <el-radio-button value="PHONE">打电话</el-radio-button>
              <el-radio-button value="WECHAT">加微信/回访</el-radio-button>
              <el-radio-button value="VISIT">上门</el-radio-button>
              <el-radio-button value="MEETING">会议</el-radio-button>
              <el-radio-button value="OTHER">其他</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="跟进时间">
            <el-date-picker v-model="fupForm.follow_at" type="datetime" style="width: 100%"
              value-format="YYYY-MM-DDTHH:mm:ss" placeholder="默认当前时间" />
          </el-form-item>
          <el-form-item label="跟进内容" required>
            <el-input v-model="fupForm.content" type="textarea" :rows="3"
              placeholder="如：今天电话回访，客户对代理记账业务感兴趣，约定下周发报价" />
          </el-form-item>
          <el-form-item label="是否成交">
            <el-checkbox v-model="fupForm.deal_happened">本次跟进已成交</el-checkbox>
          </el-form-item>
          <el-form-item v-if="fupForm.deal_happened" label="签单金额">
            <el-input-number v-model="fupForm.deal_amount" :min="0" :controls="false"
              placeholder="直接输入数字" style="width: 180px" />
            <span class="fup-amount-unit">元（成交后线索自动标记为已成交，成交师=承接人）</span>
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
import { ref, reactive, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter, useRoute } from 'vue-router'
import { growthApi } from '@/api/growth'
import { orgApi } from '@/api'
import { useUserStore } from '@/store/user'

const router = useRouter()
const route = useRoute()
const store = useUserStore()

const list = ref([])
const channels = ref([])
const loading = ref(false)
const submitting = ref(false)
const total = ref(0)
const poolWaiting = ref(0)
const roleLabel = ref('未配置')

// 2026-11-09 Boss 指示：录入人多选筛选（creators 为 id 数组，后端 in 过滤）
const filters = reactive({ channel: '', stage: '', closing: '', creators: [] })
const creatorUsers = ref([])

async function loadCreatorUsers() {
  try {
    const res = await orgApi.users({ page_size: 500, for_assign: 1 })
    const rows = Array.isArray(res) ? res : (res.results || [])
    creatorUsers.value = rows
      .filter((u) => u.is_active !== false)
      .map((u) => ({
        id: u.id,
        name: u.display_name || u.first_name || u.username,
      }))
  } catch (e) { /* 拦截器已提示 */ }
}

const createVisible = ref(false)
const stageVisible = ref(false)
const flowVisible = ref(false)
const current = ref(null)
const stageValue = ref('S3')
const stageRemark = ref('')
const flows = ref([])

// 管理层分配
const assignVisible = ref(false)
const assigning = ref(false)
const roleCanViewAll = ref(false)
const roleCanAssign = ref(false)
const opsUsers = ref([])
const closerUsers = ref([])
const staffLoading = ref(false)
const assignForm = reactive({ owner_id: null, closer_id: null, remark: '' })

// 批量分配（2026-10-29 Boss 专项）
const selected = ref([])
const bulkVisible = ref(false)
const bulkAssigning = ref(false)
const bulkForm = reactive({ owner_id: null, closer_id: null, remark: '' })
function openBulkAssign() {
  if (!selected.value.length) { ElMessage.warning('请先勾选要分配的线索（点击表格左侧复选框）'); return }
  Object.assign(bulkForm, { owner_id: null, closer_id: null, remark: '' })
  bulkVisible.value = true
}
async function submitBulkAssign() {
  if (!bulkForm.owner_id && !bulkForm.closer_id) {
    return ElMessage.warning('请至少选择归属运营或承接人')
  }
  bulkAssigning.value = true
  try {
    const r = await growthApi.bulkAssignLead({
      ids: selected.value.map((s) => s.id),
      ...bulkForm,
    })
    ElMessage.success(r?.detail || r?.msg || '批量分配完成')
    bulkVisible.value = false
    selected.value = []
    loadData()
  } catch (e) { /* 拦截器已提示 */ } finally { bulkAssigning.value = false }
}

const form = reactive({
  channel: '', source_account_no: '', name: '', phone: '', wechat: '',
  company: '', intention: '', remark: '', contact_type: 'PHONE'
})

const dealCount = computed(() => list.value.filter(r => r.stage_3570 === 'S0').length)
// 录入权限（2026-11-02 与主账号对齐）：所有登录账号均可录入线索；
// 隔离不变：录入人自动=当前登录人，列表可见范围仍由后端 scope_leads 隔离。演示访客不可写。
const canCreateLead = computed(() => !store.isDemo)
// 管理层（可看全量）才拥有「分配」权限，与后端 IsGrowthAdmin(can_view_all) 对齐
const canManage = computed(() => !store.isDemo && (roleCanViewAll.value || store.isBoss || store.isManager || store.isSuper))
// 2026-11-03 Boss 指示：分配动作单点授权（后端 roles/me 返回 can_assign_leads），
// 仅控制「分配 / 批量分配」入口，不改变编辑范围与数据可见范围
const canAssign = computed(() => canManage.value || roleCanAssign.value)

// 2026-10-30 增量：仅「运营部 → 线索池」开放线索编辑 / 删除（其余页面行为保持不变）
const isOpsPool = computed(() => (route.path || '').startsWith('/ops/leads'))
const myId = computed(() => store.userInfo?.id)
function canModifyLead(row) {
  if (!isOpsPool.value || store.isDemo || !row) return false
  if (canManage.value) return true
  return row.ops_owner === myId.value || row.closer === myId.value
}

function stageTagType(s) {
  return { S3: 'info', S5: 'primary', S7: 'warning', S0: 'success', SN: 'danger' }[s] || 'info'
}
function fmt(t) {
  return t ? String(t).slice(0, 19).replace('T', ' ') : ''
}

async function loadChannels() {
  try {
    const res = await growthApi.channels()
    channels.value = Array.isArray(res) ? res : (res.results || [])
  } catch (e) { /* 拦截器已提示 */ }
}

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filters.channel) params.channel = filters.channel
    if (filters.stage) params.stage = filters.stage
    if (filters.closing) params.closing = filters.closing
    // 2026-11-09：录入人多选筛选，逗号拼接传后端
    if (filters.creators && filters.creators.length) params.creators = filters.creators.join(',')
    const res = await growthApi.leads(params)
    list.value = Array.isArray(res) ? res : (res.results || [])
    total.value = Array.isArray(res) ? res.length : (res.count || list.value.length)
    const p = await growthApi.statsPool()
    poolWaiting.value = p.waiting || 0
  } finally {
    loading.value = false
  }
}

async function loadRole() {
  try {
    const r = await growthApi.myRole()
    if (!r) { roleLabel.value = '未配置'; return }
    roleCanViewAll.value = !!r.can_view_all
    roleCanAssign.value = !!r.can_assign_leads || store.canAssignLeads
    roleLabel.value = r.has_role ? r.role_label : (r.can_view_all ? '超级总账号' : '未配置')
  } catch (e) { /* ignore */ }
}

/**
 * 分配弹窗人员名单（2026-10-30 修复）
 * 根因：原来只读 /growth/roles/，而生产未配置任何 GrowthRole，两个下拉全空 → 无法分配到个人。
 * 现在主数据源改为真实员工名单（/accounts/users/），GrowthRole 若已配置则优先采用其 OPS/CLOSER 归类；
 * 若某一列仍为空，退化为「全公司在职员工」，保证任何情况下都能选到人。
 */
function dedupeUsers(list) {
  const m = new Map()
  for (const u of list) {
    if (u && u.id != null && !m.has(u.id)) m.set(u.id, u)
  }
  return [...m.values()]
}

async function loadAssignUsers() {
  staffLoading.value = true
  try {
    let staff = []
    try {
      const res = await orgApi.users({ page_size: 500, for_assign: 1 })
      const rows = Array.isArray(res) ? res : (res.results || [])
      staff = rows
        .filter((u) => u.is_active !== false)
        .map((u) => ({
          id: u.id,
          name: u.display_name || u.first_name || u.username,
          dept: u.department_name || '',
        }))
    } catch (e) { staff = [] }

    let roleOps = []
    let roleCloser = []
    try {
      const res2 = await growthApi.growthRoles()
      const rows2 = Array.isArray(res2) ? res2 : (res2.results || [])
      roleOps = rows2.filter((r) => r.role === 'OPS')
        .map((r) => ({ id: r.user, name: r.user_name, dept: '运营部' }))
      roleCloser = rows2.filter((r) => r.role === 'CLOSER')
        .map((r) => ({ id: r.user, name: r.user_name, dept: '电销部' }))
    } catch (e) { /* 非管理层 403，忽略 */ }

    const isOps = (d) => (d || '').includes('运营')
    const isCloser = (d) => {
      const s = d || ''
      return s.includes('电销') || s.includes('销售') || s.includes('成交')
    }
    const ops = dedupeUsers([...roleOps, ...staff.filter((u) => isOps(u.dept))])
    const closers = dedupeUsers([...roleCloser, ...staff.filter((u) => isCloser(u.dept))])
    opsUsers.value = ops.length ? ops : staff
    closerUsers.value = closers.length ? closers : staff
  } finally {
    staffLoading.value = false
  }
}

function openCreate() {
  Object.assign(form, {
    channel: channels.value[0]?.id || '', source_account_no: '', name: '', phone: '',
    wechat: '', company: '', intention: '', remark: '', contact_type: 'PHONE'
  })
  createVisible.value = true
}

async function submitCreate() {
  if (!form.channel) return ElMessage.warning('请选择来源平台')
  if (!form.source_account_no) return ElMessage.warning('请填写来源账号编号')
  if (!form.name) return ElMessage.warning('请填写客户姓名')
  if (form.contact_type === 'PHONE' && !form.phone) return ElMessage.warning('联系方式为电话时必填电话')
  if (!form.phone && !form.wechat) return ElMessage.warning('电话与微信至少填一项')

  submitting.value = true
  try {
    // 2026-11-05 修复「录入不成功 / 重复录入」：明确成功与失败的反馈——
    // 成功才关弹窗并立即把新线索插到列表顶部（不等刷新，实时可见）；
    // 失败弹窗保持打开、表单内容保留，错误原因由拦截器提示，避免盲目重复录入。
    const created = await growthApi.createLead({ ...form })
    ElMessage.success(`录入成功：${created?.lead_name || form.name}（已进入待承接流程）`)
    createVisible.value = false
    if (created && created.id) {
      list.value = [created, ...list.value]
      total.value += 1
    }
    loadData()
  } catch (e) {
    // 提交失败：不做任何关闭动作，用户明确知道未成功，可修正后重试
  } finally {
    submitting.value = false
  }
}

async function doAccept(row) {
  await growthApi.acceptLead(row.id)
  ElMessage.success('已承接')
  loadData()
}

async function doReturn(row) {
  const { value } = await ElMessageBox.prompt('填写退回原因', '退回公海', {
    inputPlaceholder: '如：客户失联 / 无法跟进', inputValue: ''
  }).catch(() => ({ value: null }))
  if (value === null) return
  await growthApi.returnPool(row.id, { reason: value || '无法跟进' })
  ElMessage.success('已退回公海，可二次分配')
  loadData()
}

function openStage(row) {
  current.value = row
  stageValue.value = row.stage_3570 || 'S3'
  stageRemark.value = ''
  stageVisible.value = true
}

async function submitStage() {
  await growthApi.setStage(current.value.id, { stage: stageValue.value, remark: stageRemark.value })
  ElMessage.success('已标记')
  stageVisible.value = false
  loadData()
}

// 2026-11-09 Boss 指示：取消 3570 标记（标记错了可撤，变更留痕）
async function clearStage() {
  try {
    await growthApi.setStage(current.value.id, { stage: '', remark: '取消标记' })
    ElMessage.success('已取消标记')
    stageVisible.value = false
    loadData()
  } catch (e) { /* 拦截器已提示 */ }
}

async function openFlows(row) {
  current.value = row
  flowVisible.value = true
  flows.value = await growthApi.leadFlows(row.id) || []
}

// ---------------- 线索编辑 / 删除（运营部线索池，2026-10-30） ----------------
const editVisible = ref(false)
const editing = ref(false)
const editForm = reactive({
  id: null, name: '', phone: '', intention: '', channel: null,
  source_account_no: '', contact_type: 'PHONE', contact_value: '',
  contact_person: '', customer_need: '', deal_amount: 0,
})

function openEdit(row) {
  if (!row) return
  Object.assign(editForm, {
    id: row.id,
    name: row.lead_name || '',
    phone: row.lead_phone || '',
    intention: row.lead_intention || '',
    channel: row.channel || null,
    source_account_no: row.source_account_no || '',
    contact_type: row.contact_type || 'PHONE',
    contact_value: row.contact_value || '',
    contact_person: row.contact_person || '',
    customer_need: row.customer_need || '',
    deal_amount: Number(row.deal_amount || 0),
  })
  editVisible.value = true
}

async function submitEdit() {
  if (!String(editForm.name || '').trim()) return ElMessage.warning('请填写客户姓名')
  if (!String(editForm.contact_value || '').trim()) return ElMessage.warning('请填写联系方式')
  editing.value = true
  try {
    const r = await growthApi.updateLead(editForm.id, { ...editForm })
    ElMessage.success(r?.detail || '已保存修改')
    editVisible.value = false
    loadData()
  } catch (e) { /* 拦截器已提示 */ } finally {
    editing.value = false
  }
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

function openAssign(row) {
  if (!row || row.id == null) return ElMessage.warning('请先选择要分配的线索')
  current.value = row
  // 初值取当前归属，允许只改其中一项；分配目标必须来自真实员工名单
  assignForm.owner_id = row.ops_owner || null
  assignForm.closer_id = row.closer || null
  assignForm.remark = ''
  assignVisible.value = true
  if (!opsUsers.value.length && !closerUsers.value.length) loadAssignUsers()
}

async function submitAssign() {
  if (!current.value || current.value.id == null) {
    return ElMessage.warning('请先选择要分配的线索')
  }
  if (!assignForm.owner_id && !assignForm.closer_id) {
    return ElMessage.warning('请至少选择「归属运营」或「承接人」之一')
  }
  assigning.value = true
  try {
    await growthApi.assignLead(current.value.id, { ...assignForm })
    ElMessage.success('已分配，线索已移出公海并留痕')
    assignVisible.value = false
    loadData()
  } catch (e) { /* 拦截器已提示 */ } finally {
    assigning.value = false
  }
}

// 权限判定（角色接口 / 用户信息）完成后自动拉取人员名单，规避原先的异步竞态
// 2026-11-03：改为跟随 canAssign（含单点授权），否则黄涛这类只有分配权限的人拿不到名单
watch(canAssign, (v) => { if (v && !opsUsers.value.length && !closerUsers.value.length) loadAssignUsers() },
  { immediate: true })

// ---------- 2026-11-02 Boss 指示：跟进记录（查看/新增/编辑/删除）+ 成交师 ----------
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

const LEAD_STATUS_LABELS = {
  NEW: '待分配', ASSIGNED: '已分配', FOLLOWING: '跟进中', INTENTION: '高意向',
  DEAL: '已成交', LOST: '已流失', INVALID: '无效',
}
const statusLabel = (s) => LEAD_STATUS_LABELS[s] || s || '-'

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
  try { await ElMessageBox.confirm('确认删除这条跟进记录？', '删除确认', { type: 'warning' }) } catch { return }
  await growthApi.deleteFollowup(f.id)
  ElMessage.success('已删除')
  await openFollowups(fupRow.value)
}

// 2026-11-05 Boss 指示：列表实时同步——30 秒自动轮询刷新（页面隐藏/提交中时暂停），
// 他人录入或状态变化无需手动刷新即可看到，杜绝「过了十多分钟才发现录进去了」。
let pollTimer = null
function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (document.visibilityState === 'visible' && !loading.value && !submitting.value) loadData()
  }, 30000)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onMounted(() => {
  loadChannels()
  loadRole()
  loadCreatorUsers()
  loadData()
  startPolling()
})

onBeforeUnmount(stopPolling)
</script>

<style scoped>
.growth-page { padding: 4px; }
.stat-row { margin-bottom: 14px; }
.mini-card { text-align: center; }
.mini-label { font-size: 13px; color: #909399; }
.mini-value { font-size: 24px; font-weight: 600; margin-top: 6px; color: #303133; }
.mini-value.warn { color: #e6a23c; }
.mini-value.ok { color: #67c23a; }
.mini-value.small { font-size: 16px; }
.main-card { margin-top: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { margin-bottom: 8px; }
.muted { color: #909399; }
.opt-dept { float: right; color: #a8abb2; font-size: 12px; }
/* 2026-11-02 跟进记录抽屉 */
.fup-wrap { padding: 0 4px; }
.fup-timeline { margin-top: 14px; padding-left: 4px; }
.fup-item .fup-head { display: flex; align-items: center; gap: 8px; }
.fup-item .fup-ops { margin-left: auto; }
.fup-item .fup-content { margin-top: 4px; white-space: pre-wrap; color: #303133; line-height: 1.6; }
.fup-form { margin-top: 4px; }
.fup-amount-unit { margin-left: 8px; color: #909399; font-size: 12px; }
.closer-name { margin-left: 6px; color: #67c23a; font-weight: 600; }
</style>
