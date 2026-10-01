<template>
  <div class="page about-page">
    <div class="page-header">
      <h2 class="page-title">关于我们</h2>
      <el-button v-if="canEdit" type="primary" :icon="Edit" @click="openEdit">编辑内容</el-button>
    </div>

    <el-card shadow="never" class="about-card">
      <h1 class="about-h1">云南财税通集团公司简介</h1>

      <section class="about-section">
        <div class="section-title">公司简介</div>
        <p class="section-body">{{ c.intro || '（暂未填写公司简介）' }}</p>
      </section>

      <section class="about-section">
        <div class="section-title">企业文化</div>
        <p class="section-body">{{ c.culture || '（暂未填写企业文化）' }}</p>
      </section>
    </el-card>

    <el-dialog v-model="visible" title="编辑关于我们内容" width="760px" @closed="resetForm">
      <el-form :model="form" label-width="90px">
        <el-form-item label="公司简介">
          <el-input v-model="form.intro" type="textarea" :rows="6" placeholder="粘贴公司简介原文，保留换行" />
        </el-form-item>
        <el-form-item label="企业文化">
          <el-input v-model="form.culture" type="textarea" :rows="16" placeholder="粘贴企业文化原文，保留换行" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存并发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit } from '@element-plus/icons-vue'
import { companyApi } from '@/api'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const canEdit = userStore.isBoss || userStore.isHR

const c = ref({})
const visible = ref(false)
const saving = ref(false)
const form = reactive({ intro: '', culture: '' })

async function load() {
  try { const r = await companyApi.get(); c.value = r.data || {} } catch (e) {}
}
function resetForm() { form.intro = c.value.intro || ''; form.culture = c.value.culture || '' }
function openEdit() { resetForm(); visible.value = true }
async function save() {
  saving.value = true
  try {
    const r = await companyApi.save({ intro: form.intro || '', culture: form.culture || '' })
    c.value = r.data || {}
    ElMessage.success('已保存并发布')
    visible.value = false
  } catch (e) { ElMessage.error('保存失败') }
  finally { saving.value = false }
}
onMounted(load)
</script>

<style scoped>
.about-h1 {
  font-size: 26px;
  font-weight: 800;
  text-align: center;
  margin: 4px 0 28px;
  color: #1f2329;
  letter-spacing: 1px;
}
.about-card { max-width: 920px; margin: 0 auto; }
.about-section { margin-bottom: 26px; }
.section-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 4px solid var(--primary, #2f6fed);
  color: #1f2329;
}
.section-body {
  white-space: pre-wrap;
  line-height: 2;
  font-size: 15px;
  color: #2b2f36;
  margin: 0;
}
</style>
