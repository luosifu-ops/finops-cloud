/** 增长中心 API（独立文件，不改动 api/index.js）
 *  对应后端 /api/growth/ 全部接口
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000
})

http.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = 'Bearer ' + token
  return config
})

http.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else {
      ElMessage.error(err.response?.data?.detail || err.message || '请求失败')
    }
    return Promise.reject(err)
  }
)

const G = '/growth'

export const growthApi = {
  // ---------- 渠道 ----------
  channels: (params) => http.get(`${G}/channels/`, { params }),
  allChannels: () => http.get(`${G}/channels/`, { params: { all: 1 } }),
  toggleChannel: (id) => http.post(`${G}/channels/${id}/toggle/`),

  // ---------- 线索录入与流转 ----------
  leads: (params) => http.get(`${G}/leads/`, { params }),
  createLead: (data) => http.post(`${G}/leads/`, data),
  leadDetail: (id) => http.get(`${G}/leads/${id}/`),
  acceptLead: (id) => http.post(`${G}/leads/${id}/accept/`),
  returnPool: (id, data) => http.post(`${G}/leads/${id}/return_pool/`, data),
  claimLead: (id) => http.post(`${G}/leads/${id}/claim/`),
  transferLead: (id, data) => http.post(`${G}/leads/${id}/transfer/`, data),
  assignLead: (id, data) => http.post(`${G}/leads/${id}/assign/`, data),
  bulkAssignLead: (data) => http.post(`${G}/leads/bulk-assign/`, data),
  setStage: (id, data) => http.post(`${G}/leads/${id}/set_stage/`, data),
  leadFlows: (id) => http.get(`${G}/leads/${id}/flows/`),
  stageLogs: (id) => http.get(`${G}/leads/${id}/stage_logs/`),
  // 2026-10-30 增量：运营部线索池支持录入出错后修改 / 删除
  updateLead: (id, data) => http.patch(`${G}/leads/${id}/`, data),
  deleteLead: (id) => http.delete(`${G}/leads/${id}/`),

  // ---------- 公海 ----------
  pool: (params) => http.get(`${G}/pool/`, { params }),
  poolStats: () => http.get(`${G}/pool/stats/`),
  flows: (params) => http.get(`${G}/flows/`, { params }),

  // ---------- 成交师 × 平台 专项分配 ----------
  closerChannels: (params) => http.get(`${G}/closer-channels/`, { params }),
  createCloserChannel: (data) => http.post(`${G}/closer-channels/`, data),
  updateCloserChannel: (id, data) => http.patch(`${G}/closer-channels/${id}/`, data),
  deleteCloserChannel: (id) => http.delete(`${G}/closer-channels/${id}/`),
  closerChannelMatrix: () => http.get(`${G}/closer-channels/matrix/`),

  // ---------- 外勤 ----------
  fieldTasks: (params) => http.get(`${G}/field-tasks/`, { params }),
  createFieldTask: (data) => http.post(`${G}/field-tasks/`, data),
  acceptFieldTask: (id) => http.post(`${G}/field-tasks/${id}/accept/`),
  reportProgress: (id, data) => http.post(`${G}/field-tasks/${id}/report/`, data),
  taskProgresses: (id) => http.get(`${G}/field-tasks/${id}/progresses/`),

  // ---------- 增值业务部 ----------
  projects: (params) => http.get(`${G}/value-added/`, { params }),
  createProject: (data) => http.post(`${G}/value-added/`, data),
  updateProject: (id, data) => http.patch(`${G}/value-added/${id}/`, data),
  // 2026-10-31 增量：增值项目删除
  deleteProject: (id) => http.delete(`${G}/value-added/${id}/`),

  // ---------- 投放消耗 ----------
  adSpends: (params) => http.get(`${G}/ad-spend/`, { params }),
  createAdSpend: (data) => http.post(`${G}/ad-spend/`, data),

  // ---------- 角色 ----------
  growthRoles: (params) => http.get(`${G}/roles/`, { params }),
  createGrowthRole: (data) => http.post(`${G}/roles/`, data),
  updateGrowthRole: (id, data) => http.patch(`${G}/roles/${id}/`, data),
  deleteGrowthRole: (id) => http.delete(`${G}/roles/${id}/`),
  myRole: () => http.get(`${G}/roles/me/`),

  // ---------- 统计面板 ----------
  statsOverview: (params) => http.get(`${G}/stats/overview/`, { params }),
  statsByPlatform: (params) => http.get(`${G}/stats/by_platform/`, { params }),
  statsMy: (params) => http.get(`${G}/stats/my/`, { params }),
  statsDept: (params) => http.get(`${G}/stats/dept/`, { params }),
  statsPool: () => http.get(`${G}/stats/pool/`),

  // ---------- 穿透查看：按人员汇总其全部平台/账号线索与转化 ----------
  byPerson: (userId, params) => http.get(`${G}/leads/by_person/`, {
    params: Object.assign({ user_id: userId }, params || {})
  }),

  // ---------- 线索多次跟进（第一次 / 二次 / 三次）----------
followups: (params) => http.get(`${G}/followups/`, { params }),
createFollowup: (data) => http.post(`${G}/followups/`, data),
updateFollowup: (id, data) => http.patch(`${G}/followups/${id}/`, data),
// 2026-11-02 增量：跟进记录删除（软删，is_deleted）
deleteFollowup: (id) => http.delete(`${G}/followups/${id}/`),

  // ---------- 外勤精细化进度节点 ----------
  fieldNodes: (params) => http.get(`${G}/field-nodes/`, { params }),
  createFieldNode: (data) => http.post(`${G}/field-nodes/`, data),
  updateFieldNode: (id, data) => http.patch(`${G}/field-nodes/${id}/`, data),

  // ---------- 外勤主管派单 / 成交单自动流转 / 节点点选 ----------
  assignFieldTask: (id, data) => http.post(`${G}/field-tasks/${id}/assign/`, data),
  fromDeal: (data) => http.post(`${G}/field-tasks/from_deal/`, data),
  fieldTaskNodeChoices: () => http.get(`${G}/field-tasks/node_choices/`),
  addFieldNode: (id, data) => http.post(`${G}/field-tasks/${id}/add_node/`, data),
  // 2026-10-30 增量：跨部门订单转接至外勤任务池 / 外勤任务编辑修改 / 外勤任务删除
  transferInFieldTask: (data) => http.post(`${G}/field-tasks/transfer-in/`, data),
  updateFieldTask: (id, data) => http.patch(`${G}/field-tasks/${id}/`, data),
  deleteFieldTask: (id) => http.delete(`${G}/field-tasks/${id}/`),
  // 2026-10-31 增量：外勤回退（把派给自己的任务退回任务池）
  returnBackFieldTask: (id, data) => http.post(`${G}/field-tasks/${id}/return_back/`, data),

  // ---------- 增值业务合同上传（续费 / 上门拜访）----------
  uploadVaContract: (id, file) => {
    const fd = new FormData()
    fd.append('contract', file)
    return http.post(`${G}/value-added/${id}/upload_contract/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  }
}

export default growthApi
