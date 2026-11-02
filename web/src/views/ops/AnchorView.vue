<template>
  <div class="anchor">
    <el-tabs v-model="activeTab" class="anchor-tabs" @tab-change="onTab">
      <!-- ========== 主播管理（原有，保留） ========== -->
      <el-tab-pane label="主播管理" name="manage">
        <div class="anchor-kpis">
          <el-row :gutter="14">
            <el-col :span="6" v-for="k in stats" :key="k.label">
              <el-card shadow="hover">
                <div class="kpi"><div class="num">{{ k.value }}</div><div class="lab">{{ k.label }}</div></div>
              </el-card>
            </el-col>
          </el-row>
        </div>
        <el-row :gutter="14" class="anchor-main">
          <el-col :span="17">
            <BaseListView
              title="主播管理"
              base-url="/sales/streamers/"
              :columns="columns"
              :form-fields="formFields"
              :search-fields="searchFields"
            />
          </el-col>
          <el-col :span="7">
            <el-card shadow="never" header="本月 GMV 排行">
              <div v-for="(a, i) in rank" :key="a.id || a.name" class="rank-item">
                <span class="rank-no" :class="{ top: i < 3 }">{{ i + 1 }}</span>
                <span class="rank-name">{{ a.name }}</span>
                <span class="rank-gmv">¥{{ fmt(a.gmv) }}</span>
              </div>
              <el-empty v-if="!rank.length" description="暂无数据" :image-size="70" />
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- ========== 每日数据报表 ========== -->
      <el-tab-pane label="每日数据报表" name="report">
        <div class="block-bar">
          <el-date-picker v-model="reportDate" type="date" value-format="YYYY-MM-DD"
                          size="default" style="width: 170px" @change="loadReport" />
          <el-button type="primary" @click="loadReport">查询</el-button>
          <el-button @click="exportReport">导出日报</el-button>
          <span class="block-tip">数据权限：员工看自己 / 主管看本部门 / 老板看全部</span>
        </div>

        <!-- 今日客资汇总 -->
        <el-card class="sum-card" shadow="never" header="今日客资汇总">
          <el-row :gutter="14">
            <el-col :span="s.total ? 6 : 3" v-for="s in summaryCards" :key="s.label">
              <div class="sum-item" :class="{ 'sum-item-total': s.total }">
                <div class="sum-num">{{ s.value }}</div>
                <div class="sum-lab">{{ s.label }}</div>
              </div>
            </el-col>
          </el-row>
        </el-card>

        <!-- 渠道付费投放：分平台统计 -->
        <el-card class="paid-card" shadow="hover">
          <template #header>
            <div class="ch-head">
              <span class="ch-title">渠道获客（付费投放）· 分平台统计</span>
              <el-button link type="primary" @click="openReport('PAID')">＋ 新增平台</el-button>
            </div>
          </template>
          <el-table :data="paidRows" size="small" show-summary :summary-method="paidSummary" style="width:100%">
            <el-table-column prop="anchor_name" label="平台" min-width="110" />
            <el-table-column prop="cost" label="消耗(元)" width="110" align="right">
              <template #default="{ row }">{{ fmtMoney(row.cost) }}</template>
            </el-table-column>
            <el-table-column prop="lead_count" label="线索数量" width="100" align="right" />
            <el-table-column prop="acquisition_cost" label="获客成本(元)" width="125" align="right">
              <template #default="{ row }">{{ fmtMoney(safeDiv(row.cost, row.lead_count)) }}</template>
            </el-table-column>
            <el-table-column prop="account_setup" label="账户搭建" width="90" align="center" />
            <el-table-column prop="product_content" label="产品内容" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ row.product_content || '—' }}</template>
            </el-table-column>
            <el-table-column prop="remark" label="其他" min-width="120" show-overflow-tooltip>
              <template #default="{ row }">{{ row.remark || '—' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openReport('PAID', row)">编辑</el-button>
                <el-button link type="danger" @click="removeReport(row)">删除</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无数据，点击右上角「＋新增平台」录入" :image-size="70" /></template>
          </el-table>
        </el-card>

        <!-- 其余四大板块 -->
        <div class="channel-grid">
          <el-card v-for="c in otherBlocks" :key="c.key" class="ch-card" shadow="hover">
            <template #header>
              <div class="ch-head">
                <span class="ch-title">{{ c.label }}</span>
                <el-button link type="primary" @click="openReport(c.key)">{{ c.has ? '编辑' : '录入' }}</el-button>
              </div>
            </template>
            <div class="ch-rows">
              <div class="ch-row"><span>消耗</span><b>{{ fmtMoney(c.cost) }}</b></div>
              <div class="ch-row"><span>线索数量</span><b>{{ fmtNum(c.lead_count) }}</b></div>
              <div class="ch-row"><span>有效线索</span><b>{{ fmtNum(c.valid_lead) }}</b></div>
              <div class="ch-row"><span>获客成本</span><b>{{ fmtMoney(c.acquisition_cost) }}</b></div>
              <div class="ch-row"><span>账户搭建</span><b class="txt">{{ c.account_setup || '—' }}</b></div>
              <div class="ch-row"><span>产品内容</span><b class="txt">{{ c.product_content || '—' }}</b></div>
              <template v-if="c.key === 'LIVE'">
                <el-divider>直播专属</el-divider>
                <div class="ch-row"><span>直播曝光人数</span><b>{{ fmtNum(c.exposure) }}</b></div>
                <div class="ch-row"><span>直播进房人数</span><b>{{ fmtNum(c.enter_room) }}</b></div>
                <div class="ch-row"><span>进房率</span><b>{{ fmtRate(c.enter_rate) }}</b></div>
                <div class="ch-row"><span>平均在线人数</span><b>{{ fmtNum(c.avg_online) }}</b></div>
                <div class="ch-row"><span>人均停留(分)</span><b>{{ fmtNum(c.avg_stay) }}</b></div>
                <div class="ch-row"><span>直播时长(分)</span><b>{{ fmtNum(c.live_duration) }}</b></div>
                <div class="ch-row"><span>投流消耗</span><b>{{ fmtMoney(c.live_cost) }}</b></div>
                <div class="ch-row"><span>留资数</span><b>{{ fmtNum(c.live_lead) }}</b></div>
                <div class="ch-row"><span>有效留资数</span><b>{{ fmtNum(c.live_valid_lead) }}</b></div>
                <div class="ch-row"><span>留资成本</span><b>{{ fmtMoney(c.lead_cost) }}</b></div>
              </template>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ========== 留资明细台账 ========== -->
      <el-tab-pane label="留资明细台账" name="ledger">
        <div class="block-bar">
          <el-button type="primary" @click="openLedger()">新增留资</el-button>
          <el-button @click="exportLedger">导出台账</el-button>
          <span class="block-tip">录入后自动汇总到上方「每日数据报表」的总留资</span>
        </div>
        <el-card shadow="never">
          <el-table :data="ledgerList" v-loading="ledgerLoading" style="width: 100%">
            <el-table-column prop="channel_name" label="渠道" width="150" />
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="customer_name" label="客户姓名" width="120" />
            <el-table-column prop="contact" label="联系方式" width="140" />
            <el-table-column prop="need" label="客户需求" min-width="140" show-overflow-tooltip />
            <el-table-column prop="address" label="客户地址" min-width="140" show-overflow-tooltip />
            <el-table-column prop="follower_name" label="跟进人员" width="110" />
            <el-table-column label="是否通过" width="90">
              <template #default="{ row }"><el-tag :type="row.is_passed ? 'success' : 'info'" size="small">{{ row.is_passed ? '通过' : '未通过' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="detail" label="备注" min-width="140" show-overflow-tooltip />
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openLedger(row)">编辑</el-button>
                <el-button link type="danger" @click="removeLedger(row)">删除</el-button>
              </template>
            </el-table-column>
            <template #empty><el-empty description="暂无数据" :image-size="80" /></template>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ========== 直播投流统计 ========== -->
      <el-tab-pane label="直播投流统计" name="adstat">
        <div class="block-bar">
          <el-date-picker v-model="adStatDate" type="date" value-format="YYYY-MM-DD"
                          size="default" style="width: 170px" @change="loadAdStat" />
          <el-button type="primary" @click="loadAdStat">查询</el-button>
        </div>
        <div class="adstat-grid">
          <el-card v-for="a in adStatBlocks" :key="a.key" shadow="hover" class="ad-card">
            <template #header><span class="ch-title">{{ a.label }}</span></template>
            <el-button class="ad-add" size="small" type="primary" plain @click="openAd(a.key)">录入</el-button>
            <div class="ch-rows">
              <div class="ch-row"><span>消耗金额</span><b>{{ fmtMoney(a.cost) }}</b>
                <i class="ring" :class="trendCls(a.cost_rate)">{{ trendTxt(a.cost_rate) }}</i></div>
              <div class="ch-row"><span>展示次数</span><b>{{ fmtNum(a.impression) }}</b>
                <i class="ring" :class="trendCls(a.impression_rate)">{{ trendTxt(a.impression_rate) }}</i></div>
              <div class="ch-row"><span>点击次数</span><b>{{ fmtNum(a.click) }}</b>
                <i class="ring" :class="trendCls(a.click_rate)">{{ trendTxt(a.click_rate) }}</i></div>
              <div class="ch-row"><span>私信咨询数</span><b>{{ fmtNum(a.private_msg) }}</b>
                <i class="ring" :class="trendCls(a.private_msg_rate)">{{ trendTxt(a.private_msg_rate) }}</i></div>
              <div class="ch-row"><span>线索留资数</span><b>{{ fmtNum(a.lead_count) }}</b>
                <i class="ring" :class="trendCls(a.lead_count_rate)">{{ trendTxt(a.lead_count_rate) }}</i></div>
              <div class="ch-row"><span>留资成本</span><b>{{ fmtMoney(a.lead_cost) }}</b></div>
            </div>
            <el-table :data="adStatRows(a.key)" size="small" class="ad-sub" max-height="220">
              <el-table-column prop="platform" label="平台" width="100" />
              <el-table-column prop="cost" label="消耗" width="90" />
              <el-table-column prop="impression" label="展示" width="80" />
              <el-table-column prop="click" label="点击" width="70" />
              <el-table-column prop="lead_count" label="线索" width="70" />
              <el-table-column label="操作" width="110">
                <template #default="{ row }">
                  <el-button link type="primary" @click="openAd(a.key, row)">编辑</el-button>
                  <el-button link type="danger" @click="removeAd(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 每日数据报表录入弹窗 -->
    <el-dialog v-model="reportVisible" :title="reportTitle" width="640px" @closed="resetReport">
      <el-form :model="reportForm" label-width="120px">
        <el-form-item label="获客板块"><el-input :value="channelLabel(reportForm.channel_type)" disabled /></el-form-item>
        <el-form-item label="日期"><el-date-picker v-model="reportForm.date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item :label="reportForm.channel_type === 'PAID' ? '平台' : '主播/账号'">
          <el-select v-model="reportForm.anchor_name" filterable allow-create default-first-option clearable
                     :placeholder="reportForm.channel_type === 'PAID' ? '选择或输入新增平台' : '可输入新增'" style="width:100%">
            <el-option v-for="o in reportAnchorOptions" :key="o" :label="o" :value="o" />
          </el-select>
        </el-form-item>
        <el-form-item label="消耗(元)"><el-input-number v-model="reportForm.cost" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="线索数量"><el-input-number v-model="reportForm.lead_count" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="有效线索"><el-input-number v-model="reportForm.valid_lead" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="获客成本(元)"><el-input-number v-model="reportForm.acquisition_cost" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="账户搭建"><el-input v-model="reportForm.account_setup" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="产品内容"><el-input v-model="reportForm.product_content" type="textarea" :rows="2" /></el-form-item>
        <template v-if="reportForm.channel_type === 'LIVE'">
          <el-divider>直播专属</el-divider>
          <el-form-item label="直播曝光人数"><el-input-number v-model="reportForm.exposure" :min="0" style="width:100%" /></el-form-item>
          <el-form-item label="直播进房人数"><el-input-number v-model="reportForm.enter_room" :min="0" style="width:100%" /></el-form-item>
          <el-form-item label="平均在线人数"><el-input-number v-model="reportForm.avg_online" :min="0" :precision="2" style="width:100%" /></el-form-item>
          <el-form-item label="人均停留(分)"><el-input-number v-model="reportForm.avg_stay" :min="0" :precision="2" style="width:100%" /></el-form-item>
          <el-form-item label="直播时长(分)"><el-input-number v-model="reportForm.live_duration" :min="0" :precision="2" style="width:100%" /></el-form-item>
          <el-form-item label="投流消耗(元)"><el-input-number v-model="reportForm.live_cost" :min="0" :precision="2" style="width:100%" /></el-form-item>
          <el-form-item label="留资数"><el-input-number v-model="reportForm.live_lead" :min="0" style="width:100%" /></el-form-item>
          <el-form-item label="有效留资数"><el-input-number v-model="reportForm.live_valid_lead" :min="0" style="width:100%" /></el-form-item>
          <el-form-item label="留资成本(元)"><el-input-number v-model="reportForm.lead_cost" :min="0" :precision="2" style="width:100%" /></el-form-item>
        </template>
        <el-form-item label="备注"><el-input v-model="reportForm.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reportVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitReport">保存</el-button>
      </template>
    </el-dialog>

    <!-- 留资明细录入弹窗 -->
    <el-dialog v-model="ledgerVisible" :title="ledgerEditingId ? '编辑留资' : '新增留资'" width="600px" @closed="resetLedger">
      <el-form :model="ledgerForm" label-width="110px">
        <el-form-item label="渠道">
          <el-select v-model="ledgerForm.channel" style="width:100%">
            <el-option v-for="c in ledgerChannels" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期"><el-date-picker v-model="ledgerForm.date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="客户姓名"><el-input v-model="ledgerForm.customer_name" /></el-form-item>
        <el-form-item label="联系方式"><el-input v-model="ledgerForm.contact" /></el-form-item>
        <el-form-item label="客户需求"><el-input v-model="ledgerForm.need" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="客户地址"><el-input v-model="ledgerForm.address" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="跟进人员">
          <el-select v-model="ledgerForm.follower" filterable clearable placeholder="选择系统账号" style="width:100%">
            <el-option v-for="u in userOptions" :key="u.value" :label="u.label" :value="u.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否通过"><el-switch v-model="ledgerForm.is_passed" /></el-form-item>
        <el-form-item label="详情备注"><el-input v-model="ledgerForm.detail" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ledgerVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitLedger">保存</el-button>
      </template>
    </el-dialog>

    <!-- 直播投流录入弹窗 -->
    <el-dialog v-model="adVisible" :title="adTitle" width="560px" @closed="resetAd">
      <el-form :model="adForm" label-width="110px">
        <el-form-item label="投流类型"><el-input :value="adTypeLabel(adForm.ad_type)" disabled /></el-form-item>
        <el-form-item label="日期"><el-date-picker v-model="adForm.date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="投放平台">
          <el-select v-model="adForm.platform" filterable allow-create default-first-option clearable placeholder="可输入新增" style="width:100%">
            <el-option v-for="o in platformOptions" :key="o" :label="o" :value="o" />
          </el-select>
        </el-form-item>
        <el-form-item label="消耗金额(元)"><el-input-number v-model="adForm.cost" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="展示次数"><el-input-number v-model="adForm.impression" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="点击次数"><el-input-number v-model="adForm.click" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="私信咨询数"><el-input-number v-model="adForm.private_msg" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="线索留资数"><el-input-number v-model="adForm.lead_count" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="adForm.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitAd">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import BaseListView from '@/components/BaseListView.vue'
import http from '@/api'
import { orgApi, salesApi } from '@/api'

const activeTab = ref('manage')
const reportDate = ref(today())
const adStatDate = ref(today())
const userOptions = ref([])
const anchorOptions = ref([])
const platformOptions = ref(['抖音', '快手', '视频号', '小红书', '闲鱼', '本地推'])
// 付费投放分平台预设（陈鑫日报口径，支持手动输入新增）
const PAID_PLATFORMS = ['58同城', '百度投放', '高德地图', '美团团购', '咸鱼']

const saving = ref(false)

// ---------------- 主播管理（原有） ----------------
const deptOptions = ref([])
const all = ref([])
const columns = [
  { prop: 'name', label: '主播昵称', width: 120 },
  { prop: 'platform_name', label: '平台', width: 80 },
  { prop: 'account', label: '账号/主页ID', minWidth: 130 },
  { prop: 'department_name', label: '所属部门', width: 90 },
  { prop: 'manager_name', label: '负责人', width: 90 },
  { prop: 'status_name', label: '状态', width: 80 },
  { prop: 'fans_count', label: '粉丝数', width: 90, align: 'right' },
  { prop: 'live_count', label: '本月开播', width: 90, align: 'right' },
  { prop: 'gmv', label: '本月GMV', width: 110, align: 'right' },
  { prop: 'commission_rate', label: '提成%', width: 80, align: 'right' },
]
const searchFields = [
  { prop: 'platform', label: '平台', type: 'select', options: [
    { value: 'DOUYIN', label: '抖音' }, { value: 'KUAISHOU', label: '快手' },
    { value: 'VIDEO', label: '视频号' }, { value: 'RED', label: '小红书' }, { value: 'OTHER', label: '其他' },
  ] },
  { prop: 'status', label: '状态', type: 'select', options: [
    { value: 'ACTIVE', label: '开播中' }, { value: 'INACTIVE', label: '停播' }, { value: 'RESIGNED', label: '已离职' },
  ] },
]
const formFields = ref([
  { prop: 'name', label: '主播昵称', type: 'text', required: true },
  { prop: 'platform', label: '平台', type: 'select', required: true, options: [
    { value: 'DOUYIN', label: '抖音' }, { value: 'KUAISHOU', label: '快手' },
    { value: 'VIDEO', label: '视频号' }, { value: 'RED', label: '小红书' }, { value: 'OTHER', label: '其他' },
  ] },
  { prop: 'account', label: '账号/主页ID', type: 'text' },
  { prop: 'phone', label: '联系电话', type: 'text' },
  { prop: 'department', label: '所属部门', type: 'select', options: [] },
  { prop: 'manager', label: '负责人', type: 'select', options: [] },
  { prop: 'status', label: '状态', type: 'select', options: [
    { value: 'ACTIVE', label: '开播中' }, { value: 'INACTIVE', label: '停播' }, { value: 'RESIGNED', label: '已离职' },
  ] },
  { prop: 'entry_date', label: '入职日期', type: 'date' },
  { prop: 'fans_count', label: '粉丝数', type: 'number' },
  { prop: 'live_count', label: '本月开播场次', type: 'number' },
  { prop: 'gmv', label: '本月GMV(元)', type: 'number' },
  { prop: 'commission_rate', label: '提成比例(%)', type: 'number' },
  { prop: 'remark', label: '备注', type: 'textarea' },
])
const fmt = (n) => (n || 0).toLocaleString('zh-CN')
function unwrap(resp) {
  if (!resp) return []
  if (Array.isArray(resp)) return resp
  if (resp.results) return resp.results
  if (resp.data && Array.isArray(resp.data.results)) return resp.data.results
  if (resp.data && Array.isArray(resp.data.list)) return resp.data.list
  if (resp.data && Array.isArray(resp.data)) return resp.data
  if (resp.list) return resp.list
  return resp.data ? [resp.data] : []
}
const stats = computed(() => {
  const arr = all.value
  const totalGmv = arr.reduce((s, x) => s + (Number(x.gmv) || 0), 0)
  const totalFans = arr.reduce((s, x) => s + (Number(x.fans_count) || 0), 0)
  const liveCount = arr.filter(x => x.status === 'ACTIVE').length
  return [
    { label: '主播总数', value: arr.length },
    { label: '在播人数', value: liveCount },
    { label: '本月总GMV', value: '¥' + fmt(totalGmv) },
    { label: '总粉丝数', value: fmt(totalFans) },
  ]
})
const rank = computed(() =>
  [...all.value].sort((a, b) => (Number(b.gmv) || 0) - (Number(a.gmv) || 0)).slice(0, 8)
)
async function loadAll() {
  try { const r = await salesApi.streamers({ page_size: 500 }); all.value = unwrap(r) } catch (e) { all.value = [] }
}

// ---------------- 每日数据报表 ----------------
const CHANNELS = [
  { key: 'PAID', label: '渠道获客（付费投放）' },
  { key: 'LIVE', label: '直播获客' },
  { key: 'LOCAL_PUSH', label: '本地推投流获客' },
  { key: 'AI', label: 'AI获客' },
  { key: 'SOCIAL', label: '视频号/小红书/闲鱼获客' },
]
const dailyReports = ref([])
const summary = ref(null)
const reportVisible = ref(false)
const reportForm = reactive({})
const reportEditingKey = ref(null)
const reportEditingId = ref(null)

const channelBlocks = computed(() => CHANNELS.map(c => {
  const rows = dailyReports.value.filter(r => r.channel_type === c.key)
  const sum = (f) => rows.reduce((s, r) => s + (Number(r[f]) || 0), 0)
  const cost = sum('cost')
  const lead = sum('lead_count')
  const valid = sum('valid_lead')
  const liveLead = sum('live_lead')
  const liveCost = sum('live_cost')
  const exposure = sum('exposure')
  const enter = sum('enter_room')
  return {
    ...c,
    has: rows.length > 0,
    cost, lead_count: lead, valid_lead: valid,
    acquisition_cost: safeDiv(cost, lead),
    account_setup: rows.map(r => r.account_setup).filter(Boolean).join('；') || '',
    product_content: rows.map(r => r.product_content).filter(Boolean).join('；') || '',
    exposure, enter_room: enter,
    enter_rate: safeDiv(enter, exposure),
    avg_online: sum('avg_online'), avg_stay: sum('avg_stay'),
    live_duration: sum('live_duration'),
    live_cost: liveCost, live_lead: liveLead, live_valid_lead: sum('live_valid_lead'),
    lead_cost: safeDiv(liveCost, liveLead),
  }
}))
const paidRows = computed(() => dailyReports.value.filter(r => r.channel_type === 'PAID'))
const otherBlocks = computed(() => channelBlocks.value.filter(c => c.key !== 'PAID'))
function paidSummary({ columns }) {
  const rows = paidRows.value
  const sum = (f) => rows.reduce((s, r) => s + (Number(r[f]) || 0), 0)
  const totalCost = sum('cost')
  const totalLead = sum('lead_count')
  return columns.map((col, i) => {
    if (i === 0) return '总和'
    if (col.property === 'cost') return fmtMoney(totalCost)
    if (col.property === 'lead_count') return fmtNum(totalLead)
    if (col.property === 'acquisition_cost') return fmtMoney(safeDiv(totalCost, totalLead))
    if (col.property === 'product_content') return rows.map(r => r.product_content).filter(Boolean).join('；')
    return ''
  })
}
const summaryCards = computed(() => {
  const s = summary.value || {}
  const b = (k) => s[k] || { valid_lead: 0, live_lead: 0, live_valid_lead: 0, lead_count: 0 }
  const ledgerCh = s.ledger_by_channel || {}
  const n = (v) => Number(v) || 0
  const items = [
    { label: '渠道有效线索', value: n(b('PAID').valid_lead) },
    { label: '直播留资', value: n(b('LIVE').live_lead) + n(b('LIVE').live_valid_lead) },
    { label: '本地推留资', value: n(b('LOCAL_PUSH').live_lead) + n(b('LOCAL_PUSH').live_valid_lead) },
    { label: 'AI留资', value: n(b('AI').lead_count) + n(b('AI').valid_lead) },
    { label: '视频号/小红书/闲鱼留资', value: n(b('SOCIAL').lead_count) + n(ledgerCh.SOCIAL) },
    { label: '自然流量留资', value: n(ledgerCh.OTHER) },
  ]
  const total = items.reduce((t, i) => t + i.value, 0)
  return [
    ...items.map(i => ({ ...i, value: fmtNum(i.value) })),
    { label: '今日总客资', value: fmtNum(total), total: true },
  ]
})
async function loadReport() {
  try {
    const [dr, sm] = await Promise.all([
      http.get('/ops/anchor-daily-reports/', { params: { date: reportDate.value, page_size: 200 } }),
      http.get('/ops/anchor-daily-reports/daily-summary/', { params: { date: reportDate.value } }),
    ])
    dailyReports.value = dr.results || []
    summary.value = sm.data || null
  } catch (e) {}
}
function channelLabel(k) { return (CHANNELS.find(c => c.key === k) || {}).label || k }
const reportAnchorOptions = computed(() => (reportForm.channel_type === 'PAID' ? PAID_PLATFORMS : anchorOptions.value))
function openReport(key, row = null) {
  reportEditingKey.value = key
  reportEditingId.value = row ? row.id : null
  // PAID 新增时保持空白表单（不预填已有平台数据）；其余板块沿用预填首条
  let r = row
  if (!r && key !== 'PAID') r = dailyReports.value.filter(x => x.channel_type === key)[0] || {}
  if (!r) r = {}
  Object.assign(reportForm, {
    channel_type: key, date: reportDate.value, anchor_name: r.anchor_name || '',
    cost: Number(r.cost) || 0, lead_count: Number(r.lead_count) || 0, valid_lead: Number(r.valid_lead) || 0,
    acquisition_cost: Number(r.acquisition_cost) || 0, account_setup: r.account_setup || '',
    product_content: r.product_content || '', exposure: Number(r.exposure) || 0,
    enter_room: Number(r.enter_room) || 0, avg_online: Number(r.avg_online) || 0,
    avg_stay: Number(r.avg_stay) || 0, live_duration: Number(r.live_duration) || 0,
    live_cost: Number(r.live_cost) || 0, live_lead: Number(r.live_lead) || 0,
    live_valid_lead: Number(r.live_valid_lead) || 0, lead_cost: Number(r.lead_cost) || 0,
    remark: r.remark || '',
  })
  reportVisible.value = true
}
const reportTitle = computed(() => {
  if (reportForm.channel_type === 'PAID') return (reportEditingId.value ? '编辑平台数据' : '新增平台') + ' · 渠道付费投放'
  return (reportEditingId.value ? '编辑' : '录入') + ' · ' + channelLabel(reportForm.channel_type)
})
function resetReport() { for (const k in reportForm) delete reportForm[k]; reportEditingId.value = null }
async function submitReport() {
  saving.value = true
  try {
    const payload = { ...reportForm }
    // 付费投放：获客成本 = 消耗 / 线索数量，自动核算（除0时后端存0，前端展示"暂无数据"）
    if (payload.channel_type === 'PAID') payload.acquisition_cost = safeDiv(payload.cost, payload.lead_count) || 0
    if (reportEditingId.value) await http.patch(`/ops/anchor-daily-reports/${reportEditingId.value}/`, payload)
    else await http.post('/ops/anchor-daily-reports/save-or-update/', payload)
    ElMessage.success('已保存')
    reportVisible.value = false
    loadReport()
  } catch (e) { ElMessage.error('保存失败，请检查字段') } finally { saving.value = false }
}
async function removeReport(row) {
  try { await ElMessageBox.confirm(`确认删除平台「${row.anchor_name || '未命名'}」当日数据？`, '提示', { type: 'warning' }) } catch { return }
  try { await http.delete(`/ops/anchor-daily-reports/${row.id}/`); ElMessage.success('已删除'); loadReport() } catch (e) { ElMessage.error('删除失败') }
}
function exportReport() {
  const headers = [
    { prop: 'channel_type_name', label: '获客板块' }, { prop: 'date', label: '日期' },
    { prop: 'anchor_name', label: '主播' }, { prop: 'cost', label: '消耗' },
    { prop: 'lead_count', label: '线索数量' }, { prop: 'valid_lead', label: '有效线索' },
    { prop: 'acquisition_cost', label: '获客成本' }, { prop: 'exposure', label: '曝光' },
    { prop: 'enter_room', label: '进房' }, { prop: 'enter_rate', label: '进房率' },
    { prop: 'live_lead', label: '留资数' }, { prop: 'live_valid_lead', label: '有效留资' },
    { prop: 'lead_cost', label: '留资成本' },
  ]
  exportCsv(`主播获客日报_${reportDate.value}.csv`, headers, dailyReports.value)
}

// ---------------- 留资明细台账 ----------------
const ledgerList = ref([])
const ledgerLoading = ref(false)
const ledgerVisible = ref(false)
const ledgerEditingId = ref(null)
const ledgerForm = reactive({})
const ledgerChannels = [
  { value: 'PAID', label: '渠道获客-付费投放' }, { value: 'LIVE', label: '直播获客' },
  { value: 'LOCAL_PUSH', label: '本地推投流获客' }, { value: 'AI', label: 'AI获客' },
  { value: 'SOCIAL', label: '视频号/小红书/闲鱼获客' }, { value: 'OTHER', label: '其他' },
]
async function loadLedger() {
  ledgerLoading.value = true
  try {
    const r = await http.get('/ops/lead-ledgers/', { params: { page_size: 200, ordering: '-date' } })
    ledgerList.value = r.results || []
  } catch (e) {} finally { ledgerLoading.value = false }
}
function openLedger(row) {
  ledgerEditingId.value = row ? row.id : null
  Object.assign(ledgerForm, row ? {
    channel: row.channel, date: row.date, customer_name: row.customer_name,
    contact: row.contact, need: row.need, address: row.address,
    follower: row.follower, is_passed: row.is_passed, detail: row.detail,
  } : { channel: 'LIVE', date: today(), customer_name: '', contact: '', need: '', address: '', follower: '', is_passed: false, detail: '' })
  ledgerVisible.value = true
}
function resetLedger() { for (const k in ledgerForm) delete ledgerForm[k] }
async function submitLedger() {
  saving.value = true
  try {
    if (ledgerEditingId.value) await http.patch(`/ops/lead-ledgers/${ledgerEditingId.value}/`, { ...ledgerForm })
    else await http.post('/ops/lead-ledgers/', { ...ledgerForm })
    ElMessage.success('已保存')
    ledgerVisible.value = false
    loadLedger(); loadReport()
  } catch (e) { ElMessage.error('保存失败，请检查字段') } finally { saving.value = false }
}
async function removeLedger(row) {
  try { await ElMessageBox.confirm('确认删除该条留资记录？', '提示', { type: 'warning' }) } catch { return }
  try { await http.delete(`/ops/lead-ledgers/${row.id}/`); ElMessage.success('已删除'); loadLedger(); loadReport() } catch (e) { ElMessage.error('删除失败') }
}
function exportLedger() {
  const headers = [
    { prop: 'channel_name', label: '渠道' }, { prop: 'date', label: '日期' },
    { prop: 'customer_name', label: '客户姓名' }, { prop: 'contact', label: '联系方式' },
    { prop: 'need', label: '需求' }, { prop: 'address', label: '地址' },
    { prop: 'follower_name', label: '跟进人' }, { prop: 'is_passed_name', label: '是否通过' },
    { prop: 'detail', label: '备注' },
  ]
  exportCsv(`客户留资明细_${today()}.csv`, headers, ledgerList.value)
}

// ---------------- 直播投流统计 ----------------
const adStats = ref([])
const adSummary = ref(null)
const adVisible = ref(false)
const adForm = reactive({})
const adEditingId = ref(null)
const AD_TYPES = [
  { key: 'SHORT_VIDEO', label: '短视频图文投流' },
  { key: 'LIVE_ROOM', label: '直播间投流' },
]
const adStatBlocks = computed(() => AD_TYPES.map(a => {
  const cur = (adSummary.value && adSummary.value.current && adSummary.value.current[a.key]) || {}
  return { ...a, cost: cur.cost || 0, impression: cur.impression || 0, click: cur.click || 0,
    private_msg: cur.private_msg || 0, lead_count: cur.lead_count || 0,
    lead_cost: safeDiv(cur.cost, cur.lead_count),
    cost_rate: cur.cost_rate, impression_rate: cur.impression_rate, click_rate: cur.click_rate,
    private_msg_rate: cur.private_msg_rate, lead_count_rate: cur.lead_count_rate }
}))
function adStatRows(key) { return adStats.value.filter(r => r.ad_type === key) }
function adTypeLabel(k) { return (AD_TYPES.find(a => a.key === k) || {}).label || k }
const adTitle = computed(() => (adEditingId.value ? '编辑' : '录入') + ' · ' + adTypeLabel(adForm.ad_type))
async function loadAdStat() {
  try {
    const [rows, sm] = await Promise.all([
      http.get('/ops/anchor-ad-stats/', { params: { date: adStatDate.value, page_size: 200 } }),
      http.get('/ops/anchor-ad-stats/summary/', { params: { date: adStatDate.value } }),
    ])
    adStats.value = rows.results || []
    adSummary.value = sm.data || null
  } catch (e) {}
}
function openAd(key, row) {
  adEditingId.value = row ? row.id : null
  Object.assign(adForm, row ? {
    ad_type: row.ad_type, date: row.date, platform: row.platform, cost: Number(row.cost) || 0,
    impression: Number(row.impression) || 0, click: Number(row.click) || 0,
    private_msg: Number(row.private_msg) || 0, lead_count: Number(row.lead_count) || 0, remark: row.remark || '',
  } : { ad_type: key, date: adStatDate.value, platform: '', cost: 0, impression: 0, click: 0, private_msg: 0, lead_count: 0, remark: '' })
  adVisible.value = true
}
function resetAd() { for (const k in adForm) delete adForm[k] }
async function submitAd() {
  saving.value = true
  try {
    if (adEditingId.value) await http.patch(`/ops/anchor-ad-stats/${adEditingId.value}/`, { ...adForm })
    else await http.post('/ops/anchor-ad-stats/', { ...adForm })
    ElMessage.success('已保存')
    adVisible.value = false
    loadAdStat()
  } catch (e) { ElMessage.error('保存失败，请检查字段') } finally { saving.value = false }
}
async function removeAd(row) {
  try { await ElMessageBox.confirm('确认删除该条投流记录？', '提示', { type: 'warning' }) } catch { return }
  try { await http.delete(`/ops/anchor-ad-stats/${row.id}/`); ElMessage.success('已删除'); loadAdStat() } catch (e) { ElMessage.error('删除失败') }
}

// ---------------- 工具 ----------------
function today() { return new Date().toISOString().slice(0, 10) }
const safeDiv = (a, b, d = 2) => (!b ? null : +((Number(a) || 0) / b).toFixed(d))
const fmtMoney = (v) => (v === null || v === undefined || v === '') ? '暂无数据' : '¥' + Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const fmtNum = (v) => (v === null || v === undefined || v === '') ? '暂无数据' : Number(v).toLocaleString('zh-CN')
const fmtRate = (v) => (v === null || v === undefined || v === '') ? '暂无数据' : (Number(v).toFixed(2) + '%')
function trendCls(v) { if (v === null || v === undefined) return 'flat'; return v > 0 ? 'up' : (v < 0 ? 'down' : 'flat') }
function trendTxt(v) { if (v === null || v === undefined) return '—'; const a = Number(v).toFixed(1); return (a > 0 ? '↑' : a < 0 ? '↓' : '→') + Math.abs(a) + '%' }
function exportCsv(filename, headers, rows) {
  const escape = (v) => { if (v === null || v === undefined) return ''; const s = String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s }
  const lines = [headers.map(h => escape(h.label)).join(',')]
  for (const r of rows) lines.push(headers.map(h => escape(r[h.prop])).join(','))
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename; a.click()
  URL.revokeObjectURL(a.href)
}
function onTab(name) {
  if (name === 'report') loadReport()
  else if (name === 'ledger') loadLedger()
  else if (name === 'adstat') loadAdStat()
}

onMounted(async () => {
  const [d, u] = await Promise.all([
    orgApi.departments({ page_size: 50 }).catch(() => ({ results: [] })),
    orgApi.users({ page_size: 300 }).catch(() => ({ results: [] })),
  ])
  const depts = d.results || d.data || []
  const users = u.results || u.data || []
  deptOptions.value = depts.map(x => ({ value: x.id, label: x.name }))
  userOptions.value = users.map(x => ({ value: x.id, label: x.name || x.first_name || x.username }))
  anchorOptions.value = (unwrap(await salesApi.streamers({ page_size: 500 }).catch(() => []))).map(x => x.name).filter(Boolean)
  formFields.value = formFields.value.map(f => {
    if (f.prop === 'department') return { ...f, options: deptOptions.value }
    if (f.prop === 'manager') return { ...f, options: userOptions.value }
    return f
  })
  loadAll()
})
</script>

<style scoped>
.anchor-tabs { --el-tabs-header-margin-bottom: 16px; }
.anchor-kpis { margin-bottom: 14px; }
.kpi { text-align: center; padding: 4px 0; }
.kpi .num { font-size: 22px; font-weight: 700; color: var(--primary); }
.kpi .lab { color: var(--text-sub); font-size: 12px; margin-top: 4px; }
.anchor-main { align-items: flex-start; }
.rank-item { display: flex; align-items: center; gap: 10px; padding: 9px 4px; border-bottom: 1px solid var(--border); }
.rank-no { width: 22px; height: 22px; line-height: 22px; text-align: center; border-radius: 50%; background: var(--border); color: var(--text-sub); font-size: 12px; }
.rank-no.top { background: var(--primary); color: #fff; }
.rank-name { flex: 1; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-gmv { font-weight: 600; color: var(--primary); }
.block-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.block-tip { color: var(--text-sub); font-size: 12px; }
.sum-card { margin-bottom: 14px; }
.sum-item { text-align: center; padding: 6px 0; }
.sum-item-total { border-left: 1px solid var(--el-border-color, #ebeef5); }
.sum-item-total .sum-num { font-size: 26px; color: var(--el-color-primary, #409eff); }
.sum-item-total .sum-lab { font-weight: 700; }
.sum-num { font-size: 20px; font-weight: 700; color: var(--primary); }
.sum-lab { color: var(--text-sub); font-size: 12px; margin-top: 4px; }
.channel-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 14px; }
.paid-card { margin-bottom: 14px; }
.ch-head { display: flex; justify-content: space-between; align-items: center; }
.ch-title { font-weight: 700; font-size: 15px; }
.ch-rows { font-size: 13px; }
.ch-row { display: flex; justify-content: space-between; align-items: center; padding: 6px 2px; border-bottom: 1px dashed var(--border); }
.ch-row span { color: var(--text-sub); }
.ch-row b { font-weight: 600; }
.ch-row b.txt { font-weight: 400; max-width: 60%; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.adstat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px; }
.ad-add { margin-bottom: 8px; }
.ad-sub { margin-top: 8px; }
.ring { font-style: normal; font-size: 11px; margin-left: 6px; }
.ring.up { color: #f56c6c; }
.ring.down { color: #67c23a; }
.ring.flat { color: var(--text-sub); }
</style>
