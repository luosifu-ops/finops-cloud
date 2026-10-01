<template>
  <div class="stat-page">
    <div class="page-head">
      <h2 class="page-title">考勤统计</h2>
      <div class="head-tools">
        <el-date-picker
          v-model="month"
          type="month"
          value-format="YYYY-MM"
          placeholder="选择统计月份"
          style="width: 160px"
          @change="load"
        />
        <el-button type="primary" @click="load">查询</el-button>
        <span class="tip">团队考勤统计（出勤 / 迟到 / 早退 / 旷工），数据来自打卡记录聚合</span>
      </div>
    </div>

    <!-- 汇总卡片 -->
    <div class="summary-row" v-loading="loading">
      <el-card shadow="hover" class="summary-card">
        <div class="s-label">统计人数</div>
        <div class="s-value">{{ summary.people }}<span class="s-unit">人</span></div>
      </el-card>
      <el-card shadow="hover" class="summary-card">
        <div class="s-label">出勤总人次</div>
        <div class="s-value">{{ summary.days }}<span class="s-unit">次</span></div>
      </el-card>
      <el-card shadow="hover" class="summary-card warn">
        <div class="s-label">迟到合计</div>
        <div class="s-value">{{ summary.late }}<span class="s-unit">次</span></div>
      </el-card>
      <el-card shadow="hover" class="summary-card warn">
        <div class="s-label">早退合计</div>
        <div class="s-value">{{ summary.early }}<span class="s-unit">次</span></div>
      </el-card>
      <el-card shadow="hover" class="summary-card danger">
        <div class="s-label">旷工合计</div>
        <div class="s-value">{{ summary.absent }}<span class="s-unit">次</span></div>
      </el-card>
    </div>

    <!-- 明细表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="list" v-loading="loading" border stripe style="width: 100%">
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column prop="user_name" label="员工" min-width="120" />
        <el-table-column prop="department_name" label="部门" min-width="140" show-overflow-tooltip />
        <el-table-column prop="days" label="出勤天数" width="110" sortable />
        <el-table-column prop="late_times" label="迟到次数" width="110" sortable>
          <template #default="{ row }">
            <span :class="row.late_times > 0 ? 'cell-warn' : ''">{{ row.late_times }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="early_times" label="早退次数" width="110" sortable>
          <template #default="{ row }">
            <span :class="row.early_times > 0 ? 'cell-warn' : ''">{{ row.early_times }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="absent_times" label="旷工次数" width="110" sortable>
          <template #default="{ row }">
            <span :class="row.absent_times > 0 ? 'cell-danger' : ''">{{ row.absent_times }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && list.length === 0" description="该月份暂无考勤统计数据，可切换其他月份查看" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import http from '@/api'

// 默认指向种子数据富集月份（2026-08 有 535 条打卡记录），boss 可随时切换
const month = ref('2026-08')
const list = ref([])
const loading = ref(false)

const summary = computed(() => {
  const s = { people: list.value.length, days: 0, late: 0, early: 0, absent: 0 }
  for (const r of list.value) {
    s.days += Number(r.days) || 0
    s.late += Number(r.late_times) || 0
    s.early += Number(r.early_times) || 0
    s.absent += Number(r.absent_times) || 0
  }
  return s
})

async function load() {
  loading.value = true
  try {
    const r = await http.get('/hr/attendances/team-stat/', { params: { month: month.value } })
    const data = r && r.data ? r.data : {}
    list.value = Array.isArray(data.list) ? data.list : []
  } catch (e) {
    list.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.stat-page { padding: 4px; }
.page-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px; flex-wrap: wrap; gap: 10px;
}
.page-title { font-size: 18px; margin: 0; }
.head-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.tip { color: #909399; font-size: 12px; }
.summary-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }
.summary-card { border-radius: 10px; }
.summary-card .s-label { color: #909399; font-size: 13px; }
.summary-card .s-value { font-size: 26px; font-weight: 700; margin-top: 6px; }
.s-unit { font-size: 13px; font-weight: 400; margin-left: 4px; color: #909399; }
.summary-card.warn .s-value { color: #e6a23c; }
.summary-card.danger .s-value { color: #f56c6c; }
.table-card { border-radius: 10px; }
.cell-warn { color: #e6a23c; font-weight: 600; }
.cell-danger { color: #f56c6c; font-weight: 600; }
@media (max-width: 900px) { .summary-row { grid-template-columns: repeat(2, 1fr); } }
</style>
