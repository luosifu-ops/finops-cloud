<template>
  <div class="page">
    <h2 class="page-title">合作咨询</h2>
    <el-card class="inq-card" shadow="never">
      <el-alert type="success" :closable="false" style="margin-bottom:14px">
        财税企管云开放城市合伙 / 渠道 / 联营合作，提交后招商专员会尽快与您联系。
      </el-alert>
      <el-form :model="form" label-width="84px" style="max-width: 520px">
        <el-form-item label="姓名" required><el-input v-model="form.name" placeholder="您的称呼" /></el-form-item>
        <el-form-item label="手机号" required><el-input v-model="form.phone" placeholder="联系电话" /></el-form-item>
        <el-form-item label="公司名称"><el-input v-model="form.company" placeholder="选填" /></el-form-item>
        <el-form-item label="城市"><el-input v-model="form.city" placeholder="选填" /></el-form-item>
        <el-form-item label="留言"><el-input v-model="form.message" type="textarea" :rows="3" placeholder="选填，说明合作意向" /></el-form-item>
        <el-button type="primary" :loading="submitting" @click="submit">提交咨询</el-button>
      </el-form>
    </el-card>

    <div v-if="isAdmin" class="card">
      <div class="card-title">咨询留言管理</div>
      <div class="table-wrap">
        <el-table :data="inqs" stripe>
          <el-table-column prop="name" label="姓名" width="100" />
          <el-table-column prop="phone" label="手机" width="130" />
          <el-table-column prop="company" label="公司" min-width="140" />
          <el-table-column prop="city" label="城市" width="90" />
          <el-table-column prop="message" label="留言" min-width="160" show-overflow-tooltip />
          <el-table-column label="状态" width="120">
            <template #default="{ row }"><el-tag :type="tagType(row.status)" size="small">{{ row.status_display }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'NEW'" link type="success" @click="handle(row, 'CONTACTED')">已联系</el-button>
              <el-button v-if="row.status !== 'DONE'" link type="primary" @click="handle(row, 'DONE')">成交/结束</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { investmentApi } from '@/api'
import { useUserStore } from '@/store/user'

const store = useUserStore()
const isAdmin = computed(() => store.isAdmin)
const form = ref({ name: '', phone: '', company: '', city: '', message: '' })
const submitting = ref(false)
const inqs = ref([])
function unwrap(r) {
  if (!r) return []
  if (Array.isArray(r)) return r
  if (r.results) return r.results
  if (r.data && Array.isArray(r.data.results)) return r.data.results
  if (r.data && Array.isArray(r.data)) return r.data
  return []
}
const tagType = (s) => ({ NEW: 'warning', CONTACTED: 'primary', DONE: 'success' }[s] || 'info')
const submit = async () => {
  if (!form.value.name || !form.value.phone) return ElMessage.warning('请填写姓名和手机号')
  submitting.value = true
  try {
    await investmentApi.submitInquiry({ ...form.value })
    ElMessage.success('提交成功，招商专员会尽快与您联系')
    form.value = { name: '', phone: '', company: '', city: '', message: '' }
  } catch (e) { ElMessage.error('提交失败') }
  finally { submitting.value = false }
}
const handle = async (row, st) => {
  try { await investmentApi.handleInquiry(row.id, { status: st }); ElMessage.success('已更新'); load() } catch (e) { ElMessage.error('操作失败') }
}
const load = async () => {
  try { inqs.value = unwrap(await investmentApi.inquiries({ page_size: 500 })) } catch (e) { inqs.value = [] }
}
onMounted(load)
</script>

<style scoped>
.inq-card { max-width: 640px; border-radius: 16px; margin-bottom: 16px; }
</style>
