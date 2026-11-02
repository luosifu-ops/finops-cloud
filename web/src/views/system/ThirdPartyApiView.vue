<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">第三方 API 配置</h2>
        <span class="page-tip">密钥可视化填写，保存后立即生效，无需改代码或重启服务</span>
      </div>
      <el-button type="primary" :loading="saving" @click="save">保存全部修改</el-button>
    </div>

    <el-card shadow="never" v-loading="loading">
      <div class="demo-row">
        <div>
          <b>演示模式</b>
          <span class="demo-tip">开启后除老板外全员只读（新增/编辑/删除被拦截），用于对外展示或新人培训，随时可关</span>
        </div>
        <el-switch v-model="demoMode" :loading="demoSaving" @change="toggleDemo" />
      </div>
      <el-divider style="margin:12px 0" />
      <el-table :data="items" border stripe>
        <el-table-column prop="name" label="配置项" width="200" />
        <el-table-column label="密钥值" min-width="260">
          <template #default="{ row }">
            <el-input v-model="form[row.key]" :placeholder="row.configured ? `已配置（${row.masked}），留空或含****则不修改` : '尚未配置，请填写'"
              show-password clearable />
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="用途说明" min-width="200" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.configured ? 'success' : 'info'" size="small">{{ row.configured ? '已配置' : '未配置' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="申请入口" width="140">
          <template #default="{ row }">
            <el-link v-if="row.frontend" type="primary" :href="row.frontend" target="_blank">前往申请</el-link>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
      <el-alert type="warning" :closable="false" show-icon style="margin-top:14px"
        title="密钥保存到服务器数据库，仅老板/管理员可见此页；展示时已脱敏。AI 大模型 Key 配置后，AI 经营助手自动从演示模式切换为真实 AI。" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { commonApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const items = ref([])
const form = reactive({})
const demoMode = ref(false)
const demoSaving = ref(false)

async function load() {
  loading.value = true
  try {
    const r = await commonApi.sysConfig()
    items.value = r?.data?.data || r?.data || r || []
    for (const it of items.value) form[it.key] = ''
    demoMode.value = !!(r?.demo_mode ?? r?.data?.demo_mode)
  } finally { loading.value = false }
}

async function toggleDemo(v) {
  demoSaving.value = true
  try {
    const r = await commonApi.saveSysConfig({ demo_mode: v })
    ElMessage.success(r?.msg || (v ? '演示模式已开启' : '演示模式已关闭'))
  } catch (e) {
    demoMode.value = !v
  } finally { demoSaving.value = false }
}

async function save() {
  saving.value = true
  try {
    const r = await commonApi.saveSysConfig({ ...form })
    ElMessage.success(r?.msg || '已保存')
    load()
  } catch (e) { /* 拦截器已提示 */ } finally { saving.value = false }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.page-tip { font-size: 12px; color: var(--text-sub); font-weight: 400; }
.muted { color: #909399; }
.demo-row { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.demo-tip { font-size: 12px; color: var(--text-sub); margin-left: 12px; }
</style>
