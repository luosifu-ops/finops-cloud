<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">公司介绍</h2>
      <el-button v-if="canEdit" type="primary" :icon="Edit" @click="openEdit">完善资料</el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="10">
        <el-card shadow="never" class="info-card">
          <div class="logo-box" v-if="c.logo">
            <img :src="c.logo" alt="logo" class="logo" />
          </div>
          <h3 class="cname">{{ c.name || '（尚未完善公司名称）' }}</h3>
          <p class="cshort" v-if="c.short_name">简称：{{ c.short_name }}</p>

          <el-descriptions :column="1" border size="small" class="cdesc">
            <el-descriptions-item label="统一社会信用代码">{{ c.credit_code || '—' }}</el-descriptions-item>
            <el-descriptions-item label="法定代表人">{{ c.legal_person || '—' }}</el-descriptions-item>
            <el-descriptions-item label="注册资本">{{ c.registered_capital || '—' }}</el-descriptions-item>
            <el-descriptions-item label="成立日期">{{ c.established_date || '—' }}</el-descriptions-item>
            <el-descriptions-item label="注册地址">{{ c.address || '—' }}</el-descriptions-item>
          </el-descriptions>

          <div class="contact">
            <div class="ctitle">联系方式</div>
            <div class="crow"><el-icon><Phone /></el-icon> 电话：{{ c.phone || '—' }}</div>
            <div class="crow"><el-icon><Message /></el-icon> 邮箱：{{ c.email || '—' }}</div>
            <div class="crow"><el-icon><ChatDotRound /></el-icon> 微信/客服：{{ c.wechat || '—' }}</div>
            <div class="crow"><el-icon><Link /></el-icon> 官网：{{ c.website || '—' }}</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card shadow="never" class="intro-card">
          <div class="card-title">公司简介</div>
          <p class="intro-text">{{ c.intro || '（暂未填写公司简介，点击右上角「完善资料」补充）' }}</p>

          <div class="card-title" style="margin-top:18px">经营范围</div>
          <p class="scope-text">{{ c.business_scope || '—' }}</p>

          <div class="card-title" style="margin-top:18px" v-if="c.qcc_screenshot">企查查截图</div>
          <img v-if="c.qcc_screenshot" :src="c.qcc_screenshot" class="qcc" alt="企查查截图" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 编辑 -->
    <el-dialog v-model="visible" title="完善公司资料" width="640px" @closed="resetForm">
      <el-form :model="form" label-width="120px">
        <el-form-item label="公司全称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="简称"><el-input v-model="form.short_name" /></el-form-item>
        <el-form-item label="统一社会信用代码"><el-input v-model="form.credit_code" /></el-form-item>
        <el-form-item label="法定代表人"><el-input v-model="form.legal_person" /></el-form-item>
        <el-form-item label="注册资本"><el-input v-model="form.registered_capital" /></el-form-item>
        <el-form-item label="成立日期"><el-input v-model="form.established_date" placeholder="如 2019-03-12" /></el-form-item>
        <el-form-item label="注册地址"><el-input v-model="form.address" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.phone" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="微信/客服"><el-input v-model="form.wechat" /></el-form-item>
        <el-form-item label="官网"><el-input v-model="form.website" /></el-form-item>
        <el-form-item label="企查查截图地址"><el-input v-model="form.qcc_screenshot" placeholder="图片地址" /></el-form-item>
        <el-form-item label="Logo 地址"><el-input v-model="form.logo" placeholder="图片地址" /></el-form-item>
        <el-form-item label="公司简介"><el-input v-model="form.intro" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="经营范围"><el-input v-model="form.business_scope" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit, Phone, Message, ChatDotRound, Link } from '@element-plus/icons-vue'
import { companyApi } from '@/api'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const canEdit = userStore.isBoss || userStore.isHR

const c = ref({})
const visible = ref(false)
const saving = ref(false)
const form = reactive({})

const fields = ['name','short_name','credit_code','legal_person','registered_capital','established_date',
  'address','phone','email','wechat','website','qcc_screenshot','logo','intro','business_scope']

async function load() {
  try { const r = await companyApi.get(); c.value = r.data || {} } catch (e) {}
}
function resetForm() { fields.forEach(f => { form[f] = c.value[f] || '' }) }
function openEdit() { resetForm(); visible.value = true }
async function save() {
  saving.value = true
  try {
    const payload = {}
    fields.forEach(f => { payload[f] = form[f] || '' })
    const r = await companyApi.save(payload)
    c.value = r.data || {}
    ElMessage.success('已保存公司资料')
    visible.value = false
  } catch (e) { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

onMounted(load)
</script>

<style scoped>
.cname { font-size: 20px; margin: 8px 0 4px; }
.cshort { color: var(--text-sub); font-size: 13px; margin: 0 0 12px; }
.logo-box { text-align: center; }
.logo { max-height: 80px; object-fit: contain; }
.cdesc { margin-bottom: 14px; }
.contact { background: var(--bg-sub, #f6f7f9); border-radius: 8px; padding: 12px 14px; }
.ctitle { font-weight: 700; margin-bottom: 8px; font-size: 14px; }
.crow { display: flex; align-items: center; gap: 6px; font-size: 13px; margin-bottom: 6px; color: #1f2329; }
.intro-text, .scope-text { line-height: 1.8; color: #1f2329; white-space: pre-wrap; }
.qcc { max-width: 100%; border-radius: 8px; border: 1px solid var(--border); margin-top: 8px; }
.card-title { font-weight: 700; margin-bottom: 10px; font-size: 15px; }
</style>
