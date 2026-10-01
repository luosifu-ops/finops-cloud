/** 合同订单名录 API（电销部 / 运营部 独立核算 + 多附件上传）
 *  对应后端 /api/contracts/records/
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

export const contractApi = {
  // 合同列表（支持 ?dept=SALES|OPS&status=）
  records: (params) => http.get('/contracts/records/', { params }),
  create: (data) => http.post('/contracts/records/', data),
  // 多附件上传（file_type: RECEIPT 收款截图 / SCAN 合同扫描件 / PDF PDF电子合同）
  uploadFile: (id, file, fileType) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('file_type', fileType || 'PDF')
    return http.post(`/contracts/records/${id}/upload_file/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
  },
  deleteFile: (id, fileId) =>
    http.delete(`/contracts/records/${id}/delete_file/`, { params: { file_id: fileId } }),
  // 部门核算看板（电销 / 运营 独立）
  deptSummary: () => http.get('/contracts/records/dept_summary/')
}

export default contractApi
