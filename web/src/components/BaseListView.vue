<template>
  <div class="base-list">
    <div class="bl-head">
      <h2 class="bl-title">{{ title }}</h2>
      <div class="bl-tools">
        <template v-for="f in searchFields" :key="f.prop">
          <el-input
            v-if="f.type !== 'select'"
            v-model="query[f.prop]"
            :placeholder="f.label"
            size="default"
            clearable
            style="width: 160px"
            @keyup.enter="reload"
            @clear="reload"
          />
          <el-select
            v-else
            v-model="query[f.prop]"
            :placeholder="f.label"
            size="default"
            clearable
            style="width: 160px"
            @change="reload"
          >
            <el-option v-for="o in f.options" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </template>
        <el-button v-if="searchFields.length" @click="reload">查询</el-button>
        <el-button v-if="!readOnly && effectiveFormFields.length" type="primary" @click="openCreate">
          新 增
        </el-button>
        <slot name="header-extra" />
      </div>
    </div>

    <el-table :data="list" v-loading="loading" border stripe style="width: 100%">
      <el-table-column
        v-for="c in displayColumns"
        :key="c.prop"
        :prop="c.prop"
        :label="c.label"
        :width="c.width"
        :min-width="c.minWidth || 120"
        :formatter="c.formatter"
        show-overflow-tooltip
      />
      <el-table-column v-if="!readOnly" label="操作" :width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="effectiveFormFields.length" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="canDelete" link type="danger" @click="remove(row)">删除</el-button>
          <slot name="row-actions" :row="row" />
        </template>
      </el-table-column>
    </el-table>

    <div class="bl-pager" v-if="!rawArray && total > pageSize">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPage"
      />
    </div>

    <el-dialog v-model="visible" :title="editingId ? '编辑' : '新增'" :width="dialogWidth" @closed="resetForm">
      <el-form :model="form" label-width="96px">
        <el-form-item v-for="f in effectiveFormFields" :key="f.prop" :label="f.label" :required="f.required">
          <el-input
            v-if="f.type === 'text' || f.type === 'textarea'"
            v-model="form[f.prop]"
            :type="f.type === 'textarea' ? 'textarea' : 'text'"
            :rows="f.type === 'textarea' ? 3 : undefined"
          />
          <el-input-number v-else-if="f.type === 'number'" v-model="form[f.prop]" :min="0" style="width: 100%" />
          <el-date-picker
            v-else-if="f.type === 'date'"
            v-model="form[f.prop]"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
          <el-select v-else-if="f.type === 'select'" v-model="form[f.prop]" clearable style="width: 100%">
            <el-option v-for="o in f.options" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
          <el-switch v-else-if="f.type === 'switch'" v-model="form[f.prop]" />
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
import http from '@/api'

const props = defineProps({
  title: { type: String, default: '' },
  baseUrl: { type: String, required: true },     // 例如 /accounts/users/
  columns: { type: Array, default: () => [] },     // [{prop,label,width,minWidth}]
  formFields: { type: Array, default: () => [] },  // [{prop,label,type,options,required}]
  searchFields: { type: Array, default: () => [] },// [{prop,label,type,options}]
  rawArray: { type: Boolean, default: false },     // action 返回裸数组时用
  readOnly: { type: Boolean, default: false },     // 只读列表（无新增/编辑）
  canDelete: { type: Boolean, default: true },
  autoForm: { type: Boolean, default: false },   // 自动依据接口首行数据生成新增/编辑表单字段（补齐残缺页面操作功能，仅前端）
  idField: { type: String, default: 'id' },
  dialogWidth: { type: String, default: '520px' },
  extraParams: { type: Object, default: () => ({}) }
})

const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const visible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = reactive({})
const query = reactive({})

// 未显式配置列时，按首行字段自动生成列（隐藏内部字段）
const HIDDEN = new Set(['is_deleted', 'created_by', 'updated_at', 'deleted_at'])
// 财税CRM 通用字段名 → 中文表头映射（仅前端展示，不影响后端字段）
// 已覆盖后端全部接口返回字段，未命中时再由 labelFor 后缀兜底，确保零英文表头
const FIELD_LABELS = {
  // 基础标识
  id: '编号', no: '编号', code: '编码', key: '编码', number: '编号', name: '名称', title: '标题',
  real_name: '真实姓名', display_name: '显示名', username: '用户名', nickname: '昵称', short_name: '简称',
  full_name: '全名',
  // 联系方式
  phone: '手机号', mobile: '手机号', tel: '电话', telephone: '电话',
  wechat: '微信号', wx: '微信号', email: '邮箱', mail: '邮箱', qq: 'QQ',
  // 企业信息
  company: '公司名称', firm: '公司名称', company_name: '企业名称',
  credit_code: '统一信用代码', tax_no: '税号',
  // 联系人
  contact: '联系人', contact_name: '联系人', contact_person: '对接人', contact_value: '联系内容',
  // 组织 / 人员
  department: '部门', department_name: '部门', dept: '部门',
  team: '团队', team_name: '团队', position: '岗位', job: '岗位',
  role: '角色', role_name: '角色', role_label: '角色',
  owner: '负责人', owner_name: '负责人', leader: '主管', leader_name: '主管', manager: '经理', supervisor: '上级',
  parent: '上级', parent_name: '上级', children: '下级', superior: '上级',
  employee: '员工', employee_name: '员工', staff: '员工',
  user: '用户', user_name: '用户', applicant: '申请人', applicant_name: '申请人',
  accountant: '会计', accountant_name: '会计',
  // 时间
  created_at: '创建时间', create_time: '创建时间', creation_time: '创建时间',
  updated_at: '更新时间', update_time: '更新时间',
  date: '日期', day: '日期', today: '今日',
  start_date: '开始日期', begin_date: '开始日期', end_date: '结束日期',
  expire_at: '到期时间', expire_date: '到期日期',
  signed_at: '签约时间', signed_date: '签约日期', sign_date: '签约日期',
  submitted_at: '提交时间', dealt_at: '成交时间', assigned_at: '分配时间',
  received_at: '接收时间', accepted_at: '接单时间', finished_at: '完成时间',
  due_at: '截止时间', last_check_at: '最近检测', read_at: '阅读时间', last_at: '最后时间',
  stat_date: '统计日期', effective_month: '生效月',
  month: '月份', year: '年份', quarter: '季度', period: '期间', week: '周次', year_week: '年周',
  publish_at: '发布时间', published_at: '发布时间',
  // 状态 / 类型 / 分类
  status: '状态', status_name: '状态', status_label: '状态', state: '状态',
  category: '分类', category_name: '分类',
  kind: '类型', kind_name: '类型', type: '类型', type_name: '类型',
  business_type: '业务类型', task_type: '任务类型', project_type: '项目类型',
  customer_type: '客户类型', customer_type_name: '客户类型', customer_type_label: '客户类型',
  biz_type: '业务类型', biz_type_name: '业务类型',
  source: '来源', source_name: '来源平台', source_detail: '渠道明细',
  source_account_no: '来源账号', source_platform: '来源平台',
  channel: '渠道', channel_name: '渠道', channel_no: '渠道编号',
  intention: '意向业务', intend: '意向业务',
  level: '等级', level_name: '等级', grade: '评级', rank: '排名',
  is_enabled: '是否启用', is_reserved: '是否预留', is_required: '是否必修',
  is_published: '是否已发布', published: '是否已发布',
  is_deal: '是否成交', has_wechat: '是否已加微', is_married: '是否已婚', required: '是否必填',
  // 金额 / 数量
  amount: '金额', money: '金额', price: '单价', fee: '费用', cost: '成本', cost_total: '总成本',
  count: '数量', num: '数量', total: '合计', subtotal: '小计', quantity: '数量',
  rate: '比率', percent: '百分比', conversion_rate: '转化率', completion: '完成率',
  base_salary: '底薪', performance: '业绩', commission: '提成', bonus: '奖金', deduction: '扣款',
  target: '目标', actual: '实际', score: '评分', amount_target: '金额目标',
  gmv: '成交额', fans_count: '粉丝数', live_count: '直播数', view_count: '阅读量', views: '浏览量',
  // 内容 / 文本
  remark: '备注', note: '备注', memo: '备注', description: '描述', desc: '描述',
  content: '内容', summary: '摘要', body: '正文',
  result: '结果', result_name: '结果', reason: '原因', lost_reason: '流失原因',
  today_done: '今日完成', today_data: '今日数据', problems: '存在问题',
  tomorrow_plan: '明日计划', need_help: '需协助',
  next_plan: '下步计划', self_review: '自我复盘', background: '背景', process: '过程',
  cause: '原因', improvement: '改进措施', action_plan: '行动计划',
  next_action: '下一步动作', next_at: '下次跟进', way: '方式', way_label: '方式',
  service_content: '服务内容', recv_account: '收款账户',
  regulation: '制度', regulation_title: '制度标题',
  knowledge_category: '知识分类', article: '文章', article_title: '文章标题',
  // 地址 / 地区
  industry: '行业', region: '地区', area: '地区', city: '城市', province: '省份',
  address: '地址', location: '位置',
  // 审批 / 流转
  current_step: '当前节点', steps: '审批节点', step: '节点',
  node: '节点', node_label: '节点',
  action: '动作', action_label: '动作',
  old_stage: '原阶段', new_stage: '新阶段', new_stage_label: '新阶段',
  round_no: '轮次', round_label: '轮次',
  approved_at: '通过时间', rejected_at: '驳回时间',
  // 杂项
  sort: '排序', order: '排序', order_by: '排序', order_no: '单号', contract_no: '合同号',
  record: '记录', file: '文件', file_type: '文件类型', file_type_label: '文件类型',
  url: '链接', attachment: '附件', attachments: '附件', tags: '标签', video_url: '视频链接',
  lead: '线索', lead_name: '客户', lead_phone: '电话', lead_ext: '线索扩展',
  customer: '客户', customer_name: '客户名称',
  task: '任务', project: '项目', project_type: '项目类型',
  reported_by: '上报人', reported_by_name: '上报人', signer_name: '签署人',
  returned_by_name: '退回人', claimed_by_name: '领取人',
  priority: '优先级', duration: '时长',
  content_type: '内容类型', content_type_name: '内容类型', object_id: '对象ID',
  vendor: '厂商', resource_type: '资源类型', endpoint: '接入点',
  bucket_or_instance: '桶/实例', capacity: '容量', used_gb: '已用(GB)',
  max_gb: '上限(GB)', is_scalable: '可扩容', usage_rate: '占用率',
  cover: '封面', version: '版本', platform: '平台',
  received: '已收', receivable: '应收', payment_screenshot: '付款截图', payment_screenshot_url: '付款截图',
  // —— 运营部 / 电销部 / 通用 复合字段与 *_name/*_label 显式覆盖（确保零英文表头）——
  login_url: '登录地址', account_id: '账户ID', campaign_id: '计划ID', biz_line: '业务线',
  private_msg: '私信量', has_api: '是否接入接口', lead_valid_rate: '线索有效率',
  total_wechat: '总加微', cpl: '单条线索成本', cac: '获客成本', roi: '投资回报率',
  online: '是否上线', short_name: '简称', topic: '话题', script: '脚本',
  view: '浏览量', like: '点赞量', comment: '评论量', share: '分享量',
  collect: '收藏量', follow: '关注量', copy: '文案', link: '链接', goal: '推广目标',
  daily_budget: '日预算', month_budget: '月预算', balance: '账户余额',
  impression: '曝光量', click: '点击量', click_rate: '点击率', avg_click_cost: '平均点击成本',
  lead_count: '线索数', valid_lead: '有效线索', wechat_added: '加微数',
  visit_count: '访问量', deal_count: '成交数', deal_amount: '成交金额',
  lead_target: '线索目标', deal_target: '成交目标', total_cost: '总花费',
  total_lead: '总线索', total_deal: '总成交', highlights: '亮点',
  owner_name: '负责人', accountant_name: '会计', status_name: '状态',
  customer_type_name: '客户类型', source_name: '来源平台', level_name: '等级',
  biz_type_name: '业务类型', department_name: '部门', manager_name: '负责人',
  operator_name: '操作人', platform_name: '平台', account_name: '账户名称',
  campaign_name: '计划名称', creator_name: '创建人', handler_name: '处理人',
  approver_name: '审批人', leader_name: '主管', user_name: '用户',
  applicant_name: '申请人', signer_name: '签署人', author_name: '作者',
  company_name: '企业名称', customer_name: '客户名称', lead_name: '客户',
  closer_name: '成交师', claimed_by_name: '领取人', returned_by_name: '退回人',
  reported_by_name: '上报人', from_user_name: '原用户', compensate_name: '补偿方',
  assistant_name: '助理', contact_person: '对接人', contact_value: '联系内容',
  dept_label: '部门', status_label: '状态', new_stage_label: '新阶段',
  node_label: '节点', round_label: '轮次', action_label: '动作',
  content_type_name: '内容类型', category_name: '分类', channel_name: '渠道',
  way_label: '方式', file_type_label: '文件类型', customer_type_label: '客户类型',
  contact_type_label: '联系类型', business_type_label: '业务类型',
  rule_type_name: '规则类型', scope_name: '范围', kind_name: '类型',
  code_name: '编码', team_name: '团队', group_name: '分组',
  education_name: '学历', direction_name: '方向', from_job_level_name: '原职级',
  from_position_name: '原岗位', from_department_name: '原部门',
  post_title: '作品标题', parent_name: '上级名称', children_name: '下级名称',
  read: '阅读',
  // 补充精确映射（复合字段专用词，避免逐词歧义）
  access_key_secret_masked: '密钥(已脱敏)', access_key_secret_enc: '密钥(加密)', access_key_id: '密钥ID',
  acked: '已确认', acquisition_cost: '获客成本', assignee_name: '指派人', bank_name: '银行名称',
  category_display: '分类', status_display: '状态',
  check_in: '签到', check_out: '签退', check_in_location: '签到地点', check_out_location: '签退地点',
  claimed_by: '领取人', commenter_name: '评论人', finished: '是否完成',
  handover_to: '交接至', handover_to_name: '交接人', in_pool: '是否在公海',
  lead_intention: '客户意向', made_by: '制单人', made_by_name: '制单人',
  overtime_hours: '加班时长', price_yearly: '年单价',
  review_by: '复核人', review_by_name: '复核人', reviewed_by: '复核人', reviewed_by_name: '复核人', reviewer_name: '复核人',
  sales_name: '销售', sequence_name: '序号', shift_name: '班次', stage_label: '阶段', stage_3570: '阶段',
  tax_type_name: '税种', taxpayer_type_name: '纳税人类型',
  to_department: '调入部门', to_department_name: '调入部门', to_job_level: '调入职级', to_job_level_name: '调入职级',
  to_position: '调入岗位', to_position_name: '调入岗位',   to_user: '调入用户', to_user_name: '调入用户',
  total_tax: '总税额', counterparty: '交易对手', id_card_back: '身份证背面',
  id_card_front: '身份证正面', renewal_of: '续费对象',
}

// 英文单词 → 中文（逐词翻译，覆盖绝大多数复合字段名，如 lead_count→线索数、deal_amount→成交金额）
const WORD_MAP = {
  id: '编号', no: '编号', code: '编码', num: '数量', qty: '数量', count: '数', amount: '金额',
  cost: '花费', fee: '费用', price: '单价', money: '金额', total: '总计', sum: '合计',
  balance: '余额', budget: '预算', target: '目标', rate: '率', ratio: '比',
  avg: '平均', max: '最大', min: '最小',
  lead: '线索', deal: '成交', visit: '访问', click: '点击', view: '浏览', play: '播放',
  like: '点赞', comment: '评论', share: '分享', collect: '收藏', follow: '关注', fans: '粉丝',
  wechat: '微信', add: '加', added: '加', valid: '有效', invalid: '无效',
  impression: '曝光', conversion: '转化', acquire: '获客', gmv: '成交额',
  uv: '访客', pv: '浏览', cpc: '单次点击成本', read: '阅读',
  campaign: '计划', account: '账户', platform: '平台', channel: '渠道', media: '媒体',
  customer: '客户', client: '客户', contract: '合同', order: '订单', invoice: '发票',
  user: '用户', member: '成员', employee: '员工', staff: '员工', person: '人',
  owner: '负责', manager: '主管', leader: '主管', supervisor: '上级', handler: '处理',
  approver: '审批', creator: '创建', author: '作者', applicant: '申请', signer: '签署',
  operator: '操作', assistant: '助理', closer: '成交师', accountant: '会计',
  department: '部门', dept: '部门', team: '团队', group: '组', branch: '分部',
  company: '公司', firm: '公司', org: '组织',
  name: '名称', title: '标题', label: '标签', type: '类型', kind: '类型',
  category: '分类', status: '状态', state: '状态', level: '等级', grade: '等级',
  source: '来源', biz: '业务', business: '业务', industry: '行业',
  phone: '电话', mobile: '手机', tel: '电话', email: '邮箱', mail: '邮箱',
  contact: '联系', address: '地址', region: '地区', area: '地区', city: '城市',
  province: '省份', country: '国家', location: '位置',
  date: '日期', time: '时间', day: '日', week: '周', month: '月', year: '年', quarter: '季',
  start: '开始', end: '结束', begin: '开始', expire: '到期', due: '截止', effective: '生效',
  signed: '签约', submit: '提交', approve: '审批', reject: '驳回', review: '复核',
  create: '创建', update: '更新', delete: '删除', edit: '编辑', publish: '发布',
  remark: '备注', note: '备注', memo: '备注', description: '描述', desc: '描述',
  content: '内容', summary: '摘要', body: '正文', text: '文本', topic: '话题',
  script: '脚本', copy: '文案', link: '链接', cover: '封面', file: '文件',
  attachment: '附件', url: '地址', path: '路径', image: '图片', photo: '照片',
  video: '视频', audio: '音频', document: '文档',
  online: '上线', offline: '下线', active: '启用', enabled: '启用', disabled: '停用',
  highlight: '亮点', problem: '问题', plan: '计划', result: '结果', reason: '原因',
  score: '评分', rank: '排名', sort: '排序', percent: '百分比',
  stat: '统计', daily: '每日', weekly: '每周', monthly: '每月',
  is: '是否', has: '是否', can: '可', need: '需',
  login: '登录', line: '线', post: '作品', private: '私信', msg: '消息',
  entry: '入职', probation: '试用期', regular: '转正', resign: '离职', transfer: '调岗',
  salary: '薪资', performance: '业绩', commission: '提成', bonus: '奖金',
  deduction: '扣款', attendance: '考勤', leave: '请假', overtime: '加班',
  training: '培训', knowledge: '知识', article: '文章', course: '课程',
  api: '接口', raw: '原始', confirm: '确认', claim: '领取', assign: '派单',
  finish: '完成', done: '完成', pending: '待处理', process: '处理', close: '关闭',
  current: '当前', next: '下次', prev: '上次', last: '最后', first: '首次',
  parent: '上级', child: '下级', children: '下级',
  // —— 补充词根（覆盖更多复合字段，进一步降低残留英文）——
  job: '岗位', ops: '运营', node: '节点', latest: '最新', intention: '意向',
  pay: '支付', provider: '服务商', question: '题目', rule: '规则', sales: '销售',
  sequence: '序号', shift: '班次', stage: '阶段', task: '任务', tax: '税',
  item: '项目', cycle: '周期', exam: '考试', bank: '银行', assignee: '指派',
  commenter: '评论', handover: '交接', made: '制单', profit: '利润',
  period: '周期', names: '名称', qtype: '题型', key: '密钥', secret: '密钥',
  access: '访问', masked: '脱敏', by: '由', ack: '确认', to: '转',
  reviewer: '复核人', taxpayer: '纳税人', direction: '方向', education: '学历',
  gender: '性别', field: '字段', fields: '字段', data: '数据', absent: '缺勤',
  penalty: '扣款', allow: '允许', retake: '重考', annual: '年度', answer: '答案',
  answers: '答案', approval: '审批', attempt: '尝试', attempts: '次数',
  avatar: '头像', card: '卡', img: '图片', base: '基础', bound: '绑定',
  buyer: '买方', call: '通话', manage: '管理', see: '查看', view: '查看',
  all: '全部', archives: '档案', capacity: '容量', gb: 'GB', checklist: '清单',
  cit: '企业所得税', claimed: '领取', clicks: '点击量', compensate: '补偿',
  confirmed: '已确认', credit: '信用', culture: '文化', days: '天数',
  deadline: '截止', debit: '支出', declared: '已申报', departments: '部门',
  destination: '目的地', detail: '详情', diploma: '文凭', doc: '文档',
  early: '早到', times: '次数', ele: '电子', emergency: '紧急', expected: '期望',
  expense: '费用', extra: '额外', features: '功能', feature: '功能',
  fixed: '固定', from: '原', groups: '组', happened: '发生', hours: '小时',
  impressions: '曝光量', income: '收入', intro: '简介', ip: 'IP',
  in: '在', pool: '公海', default: '默认', overdue: '逾期', renewal: '续费',
  virtual: '虚拟', items: '项', ladder: '阶梯', last: '最近', late: '迟到',
  minutes: '分钟', legal: '法人', logo: '标识', module: '模块', must: '必',
  new: '新', old: '原', value: '值', normal: '正常', notes: '备注',
  openid: 'OpenID', record: '记录', options: '选项', option: '选项',
  other: '其他', files: '文件', paid: '已付', pass: '通过', score: '分数',
  passed: '已通过', method: '方式', permissions: '权限', permission: '权限',
  personal: '个人', progress: '进度', proposed: '拟', purpose: '用途',
  qcc: '企查查', screenshot: '截图', registered: '注册', capital: '资本',
  resume: '简历', returned: '退回', reviewed: '已复核', scene: '场景',
  school: '学校', scope: '范围', seal: '印章', seller: '卖方', service: '服务',
  settled: '已结算', spec: '规格', stem: '题干', subject: '科目',
  submitted: '已提交', supplier: '供应商', surtax: '附加税', ukey: 'UKey',
  used: '已用', vat: '增值税', vice: '副', leaders: '主管', website: '网址',
  work: '工作', wx: '微信', zero: '零', declare: '申报', bureau: '局', ex: '不含',
  self: '自己', analysis: '分析', addressbook: '通讯录', password: '密码',
  position: '岗位', iit: '个税', check: '检查', ok: '正常', message: '消息',
  stamp: '印花税', template: '模板', nickname: '昵称', unionid: 'UnionID', web: '网页',
}

// 字段名 → 中文表头：
// 1) 精确命中 FIELD_LABELS 直接用；2) 未命中按 _ 拆分逐词翻译（覆盖 lead_count 等复合字段）；
// 3) 再按 _name/_label/_id/_at 等后缀兜底；4) 仍无则保留原字段名
function labelFor(k) {
  if (FIELD_LABELS[k]) return FIELD_LABELS[k]
  const parts = k.split('_').filter(Boolean)
  if (parts.length) {
    const translated = parts.map((p) => WORD_MAP[p] || null)
    if (translated.every((t) => t)) return translated.join('')
  }
  if (k.endsWith('_name')) {
    const base = FIELD_LABELS[k.slice(0, -5)] || WORD_MAP[k.slice(0, -5)]
    if (base) return base.replace(/(名称|编号|时间|类型|标签)$/, '') + '名称'
  }
  if (k.endsWith('_label')) {
    const base = FIELD_LABELS[k.slice(0, -6)] || WORD_MAP[k.slice(0, -6)]
    if (base) return base.replace(/(名称|编号|时间|类型|标签)$/, '') + '标签'
  }
  if (k.endsWith('_id')) {
    const base = FIELD_LABELS[k.slice(0, -3)] || WORD_MAP[k.slice(0, -3)]
    if (base) return base.replace(/(名称|编号|时间|类型|标签)$/, '') + '编号'
  }
  if (k.endsWith('_at')) return '时间'
  if (k.endsWith('_date')) return '日期'
  if (k.endsWith('_time')) return '时间'
  if (k.endsWith('_no')) return '编号'
  if (k.endsWith('_url')) return '地址'
  if (k.endsWith('_display')) {
    const base = k.slice(0, -8)
    const lab = labelFor(base)
    if (lab !== base) return lab
  }
  return k
}
// 单元格【枚举码 → 中文】映射：按字段精确映射（避免误伤自由文本）
// 覆盖财税代账系统常见的 status/level/category/customer_type/business_type 等英文码
const FIELD_ENUM = {
  status: {
    PENDING: '待接收', ACCEPTED: '已接收', IN_PROGRESS: '办理中', DONE: '已完成',
    CLOSED: '已关闭', REJECTED: '已驳回', APPROVED: '已通过',
    PENDING_APPROVAL: '审批中', SUBMITTED: '已提交', RETURNED: '已退回',
    DRAFT: '草稿', CANCELLED: '已取消', OPEN: '进行中', RESOLVED: '已解决',
    NEW: '新建', PROCESSING: '处理中', FINISHED: '已完成',
  },
  level: { BASIC: '入门', MIDDLE: '进阶', ADVANCED: '高阶' },
  category: {
    AGENCY: '代理记账', TAX: '税务', INVOICE: '发票', BUSINESS: '工商',
    SOCIAL: '社保', SOFTWARE: '软件', SALE: '销售话术', LAW: '财税法规', OPS: '投放运营',
  },
  customer_type: { ENTERPRISE: '企业', INDIVIDUAL: '个体工商户', PERSONAL: '个人' },
  business_type: {
    REG: '工商注册', LOGOUT: '注销', CHANGE: '变更',
    TAX_REPORT: '税务报到', EXCEPTION: '异常处理', GENERAL: '通用办理',
  },
  task_type: {
    REG: '工商注册', LOGOUT: '注销', CHANGE: '变更',
    TAX_REPORT: '税务报到', EXCEPTION: '异常处理', GENERAL: '通用办理',
  },
  gender: { MALE: '男', FEMALE: '女', UNKNOWN: '未知' },
  is_married: { true: '已婚', false: '未婚' },
}
// 全局兜底：仅收录高置信度、不可能出现在自由文本中的枚举码（状态/难度/客户类型）
const ENUM_FALLBACK = {
  // 通用状态
  PENDING: '待接收', ACCEPTED: '已接收', IN_PROGRESS: '办理中', DONE: '已完成', FINISHED: '已完成',
  CLOSED: '已关闭', REJECTED: '已驳回', APPROVED: '已通过', RESOLVED: '已解决',
  PENDING_APPROVAL: '审批中', SUBMITTED: '已提交', RETURNED: '已退回',
  DRAFT: '草稿', CANCELLED: '已取消', CANCELED: '已取消', REVOKED: '已撤销',
  WAITING: '待领取', CLAIMED: '已领取', ASSIGNED: '已派单', OPEN: '进行中', ONGOING: '进行中',
  ACTIVE: '启用', ENABLED: '启用', DISABLED: '停用', INACTIVE: '停用',
  NORMAL: '正常', VALID: '有效', INVALID: '失效', EXPIRED: '已过期', LAPSED: '已失效',
  NEW: '新客', FOLLOWING: '跟进中', WON: '已成交', LOST: '已流失',
  CONTACTED: '已联系', UNCONTACTED: '未联系', POOL: '公海',
  APPROVING: '审批中', PROCESSING: '处理中',
  // 等级
  BASIC: '入门', MIDDLE: '进阶', ADVANCED: '高阶',
  // 客户类型
  ENTERPRISE: '企业', INDIVIDUAL: '个体工商户', PERSONAL: '个人', COMPANY: '企业',
  // 来源平台
  DOUYIN: '抖音', KUAISHOU: '快手', BAIDU: '百度', WECHAT: '微信',
  XHS: '小红书', XIAOHONGSHU: '小红书', SHIPINHAO: '视频号', TOUTIAO: '头条',
  WEIBO: '微博', ZHIHU: '知乎', BILIBILI: 'B站', MEITUAN: '美团',
  // 部门编码
  SALES: '电销部', ACCOUNT: '会计部', ACCOUNTING: '会计部', OPS: '运营部', MGMT: '管理层',
  HR: '人力资源部', FIN: '财务部', ADMIN: '行政部',
  // 合同/任务类型
  LABOR: '劳动合同', INTERNSHIP: '实习协议', SERVICE: '劳务协议', OUTSOURCING: '外包协议',
  REG: '工商注册', LOGOUT: '注销', CHANGE: '变更', TAX_REPORT: '税务报到',
  EXCEPTION: '异常处理', GENERAL: '通用办理', TRANSFER: '转让',
  // 员工状态
  PROBATION: '试用期', REGULAR: '正式', RESIGNED: '已离职', ON_JOB: '在职', OFF_JOB: '离职',
  // 请假类型
  ANNUAL: '年假', SICK: '病假', PERSONAL_LEAVE: '事假', MARRIAGE: '婚假',
  MATERNITY: '产假', PATERNITY: '陪产假',
  // 性别
  MALE: '男', FEMALE: '女', UNKNOWN: '未知',
  // 布尔兜底
  TRUE: '是', FALSE: '否', YES: '是', NO: '否',
}
// 单元格值格式化：全平台统一
// 1) 布尔值 → 是/否（满足「已读/已发布 等 true/false 统一中文」要求）
// 2) 列配置了 dict/options → 按值映射中文
// 3) 枚举码（status/level/category/customer_type/business_type 等）→ 中文
function formatCell(col, val) {
  if (val === true || val === false) return val ? '是' : '否'
  if (val === null || val === undefined || val === '') return val
  if (col.dict && col.dict[val] !== undefined) return col.dict[val]
  if (col.options) {
    const hit = col.options.find((o) => o.value === val)
    if (hit) return hit.label
  }
  if (FIELD_ENUM[col.prop] && FIELD_ENUM[col.prop][val] !== undefined) return FIELD_ENUM[col.prop][val]
  if (typeof val === 'string' && ENUM_FALLBACK[val] !== undefined) return ENUM_FALLBACK[val]
  return val
}
// 自动推导表单字段：当页面未显式配置 formFields 且开启 autoForm 时，
// 依据接口首行数据生成新增/编辑表单（仅影响前端弹窗，不改后端字段/逻辑）
const AUTO_FORM_EXCLUDE = new Set([...HIDDEN, 'id', 'created_at', 'updated_at', 'deleted_at', 'is_deleted'])
function deriveFormFields(row) {
  if (!row) return []
  return Object.keys(row)
    .filter((k) => {
      if (AUTO_FORM_EXCLUDE.has(k)) return false
      if (k.endsWith('_display')) return false
      if (k.endsWith('_name') || k.endsWith('_label')) return false // 派生展示字段不进表单
      if (k.endsWith('_at') || k.endsWith('_time')) return false // 时间戳不进表单
      return true
    })
    .map((k) => {
      const v = row[k]
      const label = labelFor(k)
      if (typeof v === 'boolean') return { prop: k, label, type: 'switch' }
      if (typeof v === 'number') return { prop: k, label, type: 'number' }
      if (typeof v === 'string') {
        if (FIELD_ENUM[k]) {
          const options = Object.entries(FIELD_ENUM[k]).map(([value, lbl]) => ({ value, label: lbl }))
          return { prop: k, label, type: 'select', options }
        }
        if (/^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$/.test(v)) return { prop: k, label, type: 'date' }
        return { prop: k, label, type: 'text' }
      }
      return { prop: k, label, type: 'text' }
    })
}
const effectiveFormFields = computed(() => {
  if (props.formFields && props.formFields.length) return props.formFields
  if (props.autoForm && list.value.length) return deriveFormFields(list.value[0])
  return []
})

const displayColumns = computed(() => {
  const base = (props.columns && props.columns.length)
    ? props.columns
    : (() => {
        const row = list.value[0]
        if (!row) return []
        return Object.keys(row)
          .filter((k) => !HIDDEN.has(k))
          .map((k) => ({ prop: k, label: labelFor(k) }))
      })()
  return base.map((c) => ({ ...c, formatter: (r, col, v) => formatCell(c, v) }))
})

function buildParams() {
  const p = { ...props.extraParams }
  if (!props.rawArray) {
    p.page = page.value
    p.page_size = pageSize.value
  }
  for (const k in query) {
    if (query[k] !== '' && query[k] !== null && query[k] !== undefined) p[k] = query[k]
  }
  return p
}

async function reload() {
  loading.value = true
  try {
    const resp = await http.get(props.baseUrl, { params: buildParams() })
    const body = resp || {}
    let payload = body
    if (body && typeof body === 'object' && 'code' in body && 'data' in body) payload = body.data
    if (payload && payload.results) {
      list.value = payload.results
      total.value = payload.count || payload.results.length
    } else if (Array.isArray(payload)) {
      list.value = payload
      total.value = payload.length
    } else if (payload && typeof payload === 'object') {
      list.value = [payload]
      total.value = 1
    } else {
      list.value = []
      total.value = 0
    }
  } catch (e) {
    // 拦截器已提示
  } finally {
    loading.value = false
  }
}

function onPage(p) {
  page.value = p
  reload()
}

function resetForm() {
  for (const k in form) delete form[k]
  editingId.value = null
}

function openCreate() {
  resetForm()
  const today = new Date().toISOString().slice(0, 10)
  for (const f of effectiveFormFields.value) {
    if (f.type === 'number') form[f.prop] = 0
    else if (f.type === 'switch') form[f.prop] = false
    else if (f.type === 'date') form[f.prop] = today
    else form[f.prop] = ''
  }
  visible.value = true
}

function openEdit(row) {
  resetForm()
  for (const f of effectiveFormFields.value) form[f.prop] = row[f.prop]
  editingId.value = row[props.idField]
  visible.value = true
}

async function submit() {
  saving.value = true
  try {
    if (editingId.value) {
      await http.patch(`${props.baseUrl}${editingId.value}/`, { ...form })
      ElMessage.success('已保存')
    } else {
      await http.post(props.baseUrl, { ...form })
      ElMessage.success('已创建')
    }
    visible.value = false
    reload()
  } catch (e) {
    ElMessage.error('保存失败，请检查字段')
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm('确认删除该条记录？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await http.delete(`${props.baseUrl}${row[props.idField]}/`)
    ElMessage.success('已删除')
    reload()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(reload)

defineExpose({ reload })
</script>

<style scoped>
.base-list { padding: 4px; }
.bl-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 10px; }
.bl-title { font-size: 18px; margin: 0; }
.bl-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.bl-pager { margin-top: 14px; display: flex; justify-content: flex-end; }
</style>
