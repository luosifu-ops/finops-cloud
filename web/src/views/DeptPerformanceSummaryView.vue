<template>
  <div class="page" v-loading="loading">
    <div class="page-head">
      <div>
        <div class="page-title">部门业绩核算</div>
        <div class="page-sub">
          各部门业绩按月自动汇总，逐级向上汇总到老板 / 总经理账号
          <el-tag v-if="!isCompany" size="small" type="warning" style="margin-left:8px">
            仅显示本部门
          </el-tag>
        </div>
      </div>
      <div class="page-actions">
        <el-date-picker v-model="month" type="month" value-format="YYYY-MM"
                        placeholder="选择月份" style="width: 150px" @change="load" />
        <el-button :loading="loading" @click="load">刷新</el-button>
      </div>
    </div>

    <!-- 公司合计 -->
    <el-row :gutter="14" class="stat-row">
      <el-col :xs="24" :sm="12" :md="6" v-for="c in companyCards" :key="c.label">
        <el-card shadow="never" class="stat-card">
          <div class="stat-label">{{ c.label }}</div>
          <div class="stat-value" :style="{ color: c.color || 'var(--text-main)' }">{{ c.value }}</div>
          <div v-if="c.sub" class="stat-sub">{{ c.sub }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 各部门业绩 -->
    <el-card shadow="never" class="block">
      <div class="block-title">
        各部门业绩明细
        <span class="block-tip">（点击部门可下钻到部门业绩总览）</span>
      </div>
      <el-table :data="departments" size="default" stripe border
                empty-text="本月暂无业绩数据" @row-click="drill">
        <el-table-column prop="name" label="部门" width="150" />
        <el-table-column label="签约金额" align="right" width="180">
          <template #default="{ row }">
            <span class="money">¥{{ fmt(row.signed_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="回款金额" align="right" width="170">
          <template #default="{ row }">¥{{ fmt(row.received_amount) }}</template>
        </el-table-column>
        <el-table-column label="目标金额" align="right" width="170">
          <template #default="{ row }">¥{{ fmt(row.target_amount) }}</template>
        </el-table-column>
        <el-table-column label="完成率" align="center" min-width="200">
          <template #default="{ row }">
            <el-progress :percentage="Math.min(row.completion_rate || 0, 100)"
                         :stroke-width="10" :show-text="false"
                         :color="rateColor(row.completion_rate)" />
            <div class="rate-text">{{ row.completion_rate || 0 }}%</div>
          </template>
        </el-table-column>
        <el-table-column prop="member_count" label="在编人数" align="center" width="110" />
      </el-table>

      <!-- 合计行 -->
      <div class="total-row" v-if="departments.length">
        <span class="total-label">合计</span>
        <span class="total-item">签约 <b class="money">¥{{ fmt(company.signed_amount) }}</b></span>
        <span class="total-item">回款 ¥{{ fmt(company.received_amount) }}</span>
        <span class="total-item">目标 ¥{{ fmt(company.target_amount) }}</span>
        <span class="total-item">完成率 <b>{{ company.completion_rate || 0 }}%</b></span>
      </div>
    </el-card>

    <!-- 业绩排行 -->
    <el-card shadow="never" class="block" v-if="performers.length">
      <div class="block-title">个人业绩排行（本月签约金额 TOP 10）</div>
      <el-table :data="performers" size="small" stripe>
        <el-table-column type="index" label="#" width="52" align="center" />
        <el-table-column prop="name" label="姓名" min-width="110" />
        <el-table-column prop="department" label="部门" min-width="100" />
        <el-table-column label="签约金额" align="right" min-width="130">
          <template #default="{ row }"><span class="money">¥{{ fmt(row.signed_amount) }}</span></template>
        </el-table-column>
        <el-table-column label="完成率" align="center" min-width="90">
          <template #default="{ row }">{{ row.completion_rate || 0 }}%</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { dashApi } from '@/api'

const router = useRouter()
const month = ref(dayjs().format('YYYY-MM'))
const loading = ref(false)
const scopeCode = ref('COMPANY')
const company = ref({})
const departments = ref([])
const performers = ref([])

const isCompany = computed(() => scopeCode.value === 'COMPANY')

const fmt = (n) => Number(n || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
const wan = (n) => {
  const v = Number(n || 0)
  return v >= 10000 ? (v / 10000).toFixed(2) + ' 万' : fmt(v)
}
const rateColor = (r) => (r >= 100 ? '#12865a' : r >= 60 ? '#c07a12' : '#c3372c')

const companyCards = computed(() => {
  const c = company.value || {}
  const mine = isCompany.value ? '全公司' : '本部门'
  return [
    { label: `${mine}签约金额`, value: '¥' + wan(c.signed_amount), color: '#c3372c',
      sub: `合同 ${fmt(c.contract_count)} 单` },
    { label: `${mine}回款金额`, value: '¥' + wan(c.received_amount) },
    { label: '目标金额', value: '¥' + wan(c.target_amount) },
    { label: '目标完成率', value: (c.completion_rate || 0) + '%', color: rateColor(c.completion_rate) },
  ]
})

const load = async () => {
  loading.value = true
  try {
    const r = await dashApi.companyPerformance({ month: month.value })
    const d = r?.data || r || {}
    scopeCode.value = d.scope || 'COMPANY'
    company.value = d.company || {}
    departments.value = d.departments || []
    performers.value = d.top_performers || []
  } catch (e) {
    company.value = {}
    departments.value = []
    performers.value = []
  } finally {
    loading.value = false
  }
}

// 下钻：跳到对应部门业绩总览（后端会校验是否本部门，越权返回 403）
const drill = (row) => {
  const map = { SALES: '/sales/overview', ACCOUNT: '/accounting/overview', OPS: '/ops/performance' }
  const to = map[row.code]
  if (to) router.push(to)
}

onMounted(load)
</script>

<style scoped>
.stat-row { margin-bottom: 14px; }
.stat-card { border-radius: var(--radius); border: 1px solid var(--border); }
.stat-label { font-size: 13px; color: var(--text-sub); }
.stat-value { font-size: 22px; font-weight: 700; margin-top: 6px; letter-spacing: .3px; }
.stat-sub { font-size: 12px; color: var(--text-sub); margin-top: 4px; }
.block { border-radius: var(--radius); border: 1px solid var(--border); margin-bottom: 14px; }
.block-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
.block-tip { font-size: 12px; font-weight: 400; color: var(--text-sub); }
.money { color: #c3372c; font-weight: 600; }
.rate-text { font-size: 12px; color: var(--text-sub); margin-top: 2px; }
.total-row {
  display: flex; align-items: center; gap: 26px; flex-wrap: wrap;
  margin-top: 12px; padding: 12px 14px;
  background: var(--surface-2); border-radius: 10px;
}
.total-label { font-weight: 700; }
.total-item { font-size: 13px; color: var(--text-sub); }
.total-item b { color: var(--text-main); }
</style>
