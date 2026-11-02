<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">考勤打卡</h2>
      <el-button type="primary" plain :icon="Link" @click="openDingTalk">跳转钉钉打卡</el-button>
    </div>

    <!-- 出勤规则 -->
    <el-card shadow="never" class="rule-card">
      <div class="card-title">出勤规则</div>
      <el-row :gutter="14">
        <el-col :span="8" v-for="r in rules" :key="r.label">
          <div class="rule-item">
            <div class="rule-icon"><el-icon><component :is="r.icon" /></el-icon></div>
            <div>
              <div class="rule-label">{{ r.label }}</div>
              <div class="rule-value">{{ r.value }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
      <el-alert type="info" :closable="false" show-icon class="rule-tip"
                title="本司统一使用「钉钉」进行上下班打卡，迟到/早退/缺卡以钉钉记录为准；补卡请在钉钉提交审批。" />
    </el-card>

    <!-- 今日打卡 -->
    <el-card shadow="never" class="punch-card">
      <div class="card-title">今日打卡（{{ today }}）</div>
      <div class="punch-body">
        <div class="punch-clock">
          <el-icon class="punch-icon" :class="statusClass"><Clock /></el-icon>
          <div class="punch-status">{{ todayStatus.status_name || '未打卡' }}</div>
          <div class="punch-time" v-if="todayStatus.check_in">上班 {{ fmtTime(todayStatus.check_in) }}</div>
          <div class="punch-time" v-if="todayStatus.check_out">下班 {{ fmtTime(todayStatus.check_out) }}</div>
          <div class="punch-time dim" v-if="todayStatus.work_hours">工时 {{ todayStatus.work_hours }} 小时</div>
        </div>
        <div class="punch-actions">
          <el-button type="success" size="large" :disabled="todayStatus.checked_in" :loading="punching" @click="doCheckIn">
            <el-icon><TopRight /></el-icon>&nbsp;上班打卡
          </el-button>
          <el-button type="warning" size="large" :disabled="!todayStatus.checked_in || todayStatus.checked_out" :loading="punching" @click="doCheckOut">
            <el-icon><BottomLeft /></el-icon>&nbsp;下班打卡
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 当月打卡明细 -->
    <el-card shadow="never" class="detail-card">
      <div class="card-title">我的当月打卡明细</div>
      <el-table :data="records" size="small" stripe max-height="360" empty-text="本月暂无打卡记录">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column label="上班" width="100"><template #default="{row}">{{ row.check_in ? fmtTime(row.check_in) : '—' }}</template></el-table-column>
        <el-table-column label="下班" width="100"><template #default="{row}">{{ row.check_out ? fmtTime(row.check_out) : '—' }}</template></el-table-column>
        <el-table-column prop="work_hours" label="工时" width="90" align="center"><template #default="{row}">{{ row.work_hours || '—' }}</template></el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{row}">
            <el-tag size="small" :type="statusTag(row.status)">{{ row.status_name || '—' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Clock, Link, TopRight, BottomLeft, Timer, Calendar, Promotion } from '@element-plus/icons-vue'
import { hrApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const punching = ref(false)
const today = dayjs().format('YYYY-MM-DD')
const todayStatus = ref({})
const records = ref([])

const rules = [
  { label: '上班时间', value: '早 09:00', icon: Timer },
  { label: '下班时间', value: '晚 18:00（可提前 10 分钟，17:50 起可打卡）', icon: Clock },
  { label: '休息安排', value: '周末双休（周六、周日）', icon: Calendar },
  { label: '打卡方式', value: '钉钉 App 人脸 / 地理位置打卡', icon: Promotion },
]

const statusClass = computed(() => {
  const s = todayStatus.value.status
  if (s === 'LATE') return 'late'
  if (s === 'EARLY') return 'early'
  if (todayStatus.value.checked_in) return 'done'
  return 'none'
})

const fmtTime = (t) => dayjs(t).format('HH:mm:ss')

const statusTag = (s) => {
  if (s === 'LATE') return 'danger'
  if (s === 'EARLY') return 'warning'
  if (s === 'LEAVE') return 'info'
  if (s === 'NORMAL' || s === 'ABSENT') return s === 'NORMAL' ? 'success' : 'danger'
  return 'info'
}

const openDingTalk = () => {
  const DING_APP = 'dingtalk://'                 // 钉钉客户端自定义协议（桌面端已安装时唤起）
  const DING_WEB = 'https://oa.dingtalk.com'    // 钉钉网页版工作台（兜底，保证一定能打开）
  // 1) 尝试唤起钉钉客户端：用隐藏 iframe 触发自定义协议，无客户端时静默失败、不残留空白页/不抢焦点
  const iframe = document.createElement('iframe')
  iframe.style.display = 'none'
  iframe.src = DING_APP
  document.body.appendChild(iframe)
  setTimeout(() => { if (iframe.parentNode) iframe.parentNode.removeChild(iframe) }, 1500)
  // 2) 兜底：始终打开钉钉网页版工作台，确保点击「跳转钉钉打卡」一定能跳到可用页面
  const win = window.open(DING_WEB, '_blank', 'noopener')
  if (!win) ElMessage.error('浏览器拦截了新窗口，请允许弹出窗口后重试')
  ElMessage.info('已打开钉钉网页版工作台；若本机已安装钉钉客户端，也可直接在 App 内完成打卡')
}

const loadToday = async () => {
  try { const r = await hrApi.todayStatus(); todayStatus.value = r.data || {} } catch (e) {}
}
const loadRecords = async () => {
  try { const r = await hrApi.myAttendance({ month: dayjs().format('YYYY-MM'), page_size: 60 }); records.value = r.data || [] } catch (e) {}
}
const doCheckIn = async () => {
  punching.value = true
  try { await hrApi.checkIn({}); ElMessage.success('上班打卡成功'); await loadToday() } catch (e) {} finally { punching.value = false }
}
const doCheckOut = async () => {
  punching.value = true
  try { await hrApi.checkOut({}); ElMessage.success('下班打卡成功'); await loadToday() } catch (e) {} finally { punching.value = false }
}

onMounted(async () => { loading.value = true; await Promise.all([loadToday(), loadRecords()]); loading.value = false })
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.rule-card, .punch-card, .detail-card { border-radius: 10px; border: 1px solid var(--border); margin-bottom: 14px; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
.rule-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
.rule-icon { width: 38px; height: 38px; border-radius: 10px; background: #eef3ff; color: #2a4fd4; display: flex; align-items: center; justify-content: center; font-size: 20px; }
.rule-label { font-size: 12px; color: var(--text-sub); }
.rule-value { font-size: 14px; font-weight: 600; margin-top: 2px; }
.rule-tip { margin-top: 12px; }
.punch-body { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; }
.punch-clock { display: flex; flex-direction: column; gap: 4px; }
.punch-icon { font-size: 40px; color: #c0c4cc; }
.punch-icon.done { color: #12865a; }
.punch-icon.late { color: #c3372c; }
.punch-icon.early { color: #c07a12; }
.punch-status { font-size: 18px; font-weight: 700; }
.punch-time { font-size: 13px; color: var(--text-sub); }
.punch-time.dim { color: #909399; }
.punch-actions { display: flex; gap: 14px; }
</style>
