<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <h2 class="page-title">数据储存与备份</h2>
      <el-button type="primary" :icon="Download" :loading="exporting" @click="exportAll">一键导出全部备份</el-button>
    </div>

    <el-alert type="info" :closable="false" show-icon class="top-tip"
              :title="`数据存储于本地数据库（SQLite），当前记录总量约 ${totalCount.toLocaleString('zh-CN')} 条`"
              description="下方统计各业务模块的数据规模；点击「导出」可将对应模块数据下载为 JSON 文件，用于本地备份或迁移。" />

    <el-row :gutter="14">
      <el-col :span="8" v-for="m in modules" :key="m.key">
        <el-card shadow="never" class="mod-card">
          <div class="mod-icon" :style="{ background: m.bg }"><el-icon><component :is="m.icon" /></el-icon></div>
          <div class="mod-name">{{ m.label }}</div>
          <div class="mod-count">{{ (m.count ?? '—').toLocaleString('zh-CN') }} <span>条</span></div>
          <el-button size="small" plain :icon="Download" :loading="m.loading" @click="exportOne(m)">导出</el-button>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="note-card">
      <div class="card-title">存储说明</div>
      <ul class="note-list">
        <li>业务数据统一落库于后端关系型数据库（Django + SQLite），由系统守护进程持续运行与自动持久化。</li>
        <li>导出的 JSON 备份为「快照」，可用于数据迁移、审计留痕或离线分析，导入恢复请由管理员在后端执行。</li>
        <li>敏感字段（身份证号、银行卡号、手机号）已脱敏展示，导出文件请妥善保管。</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, User, OfficeBuilding, Document, Connection, Tickets, Clock, Calendar, Notebook } from '@element-plus/icons-vue'
import { orgApi, accApi, salesApi, hrApi, reportApi } from '@/api'

const loading = ref(false)
const exporting = ref(false)

const modules = ref([
  { key: 'users', label: '员工档案', icon: User, bg: '#eef3ff', api: (p) => orgApi.users(p), count: null, loading: false },
  { key: 'clients', label: '代账客户', icon: OfficeBuilding, bg: '#e8f7ee', api: (p) => accApi.clients(p), count: null, loading: false },
  { key: 'contracts', label: '合同订单', icon: Document, bg: '#fdeceb', api: (p) => salesApi.contracts(p), count: null, loading: false },
  { key: 'leads', label: '销售线索', icon: Connection, bg: '#f3eefe', api: (p) => salesApi.leads(p), count: null, loading: false },
  { key: 'tasks', label: '做账任务', icon: Tickets, bg: '#fff4e6', api: (p) => accApi.tasks(p), count: null, loading: false },
  { key: 'attendances', label: '考勤记录', icon: Clock, bg: '#e6f7f9', api: (p) => hrApi.attendances(p), count: null, loading: false },
  { key: 'leaves', label: '请假记录', icon: Calendar, bg: '#f0f4ff', api: (p) => hrApi.leaves(p), count: null, loading: false },
  { key: 'dailies', label: '工作日报', icon: Notebook, bg: '#fef0f0', api: (p) => reportApi.dailies(p), count: null, loading: false },
])

const totalCount = computed(() => modules.value.reduce((s, m) => s + (m.count || 0), 0))

const downloadJSON = (filename, data) => {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const exportOne = async (m) => {
  m.loading = true
  try {
    const r = await m.api({ page_size: 1000 })
    downloadJSON(`finops-${m.key}-${new Date().toISOString().slice(0, 10)}.json`, r.results || r.data || [])
    ElMessage.success(`已导出「${m.label}」`)
  } catch (e) { ElMessage.error('导出失败') } finally { m.loading = false }
}

const exportAll = async () => {
  exporting.value = true
  try {
    const out = {}
    await Promise.all(modules.value.map(async (m) => {
      const r = await m.api({ page_size: 1000 })
      out[m.key] = r.results || r.data || []
    }))
    downloadJSON(`finops-backup-${new Date().toISOString().slice(0, 10)}.json`, out)
    ElMessage.success('全部备份已导出')
  } catch (e) { ElMessage.error('导出失败') } finally { exporting.value = false }
}

const loadCounts = async () => {
  loading.value = true
  await Promise.all(modules.value.map(async (m) => {
    try { const r = await m.api({ page_size: 1 }); m.count = r.count ?? (r.results ? r.results.length : 0) } catch (e) { m.count = 0 }
  }))
  loading.value = false
}

onMounted(loadCounts)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.top-tip { margin-bottom: 14px; }
.mod-card { border-radius: 10px; border: 1px solid var(--border); margin-bottom: 14px; text-align: center; }
.mod-icon { width: 40px; height: 40px; border-radius: 10px; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 20px; margin: 0 auto 8px; }
.mod-name { font-size: 14px; font-weight: 600; }
.mod-count { font-size: 22px; font-weight: 700; margin: 4px 0 10px; }
.mod-count span { font-size: 12px; color: var(--text-sub); font-weight: 400; }
.note-card { border-radius: 10px; border: 1px solid var(--border); }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.note-list { margin: 0; padding-left: 18px; color: #4e5969; font-size: 13px; line-height: 2; }
</style>
