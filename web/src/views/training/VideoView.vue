<template>
  <div class="train">
    <div class="t-left">
      <div class="t-left-head">
        <el-select v-model="category" placeholder="全部分类" clearable size="small" @change="load" style="flex:1">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-button type="primary" size="small" @click="openCreate">新增视频</el-button>
      </div>
      <div class="t-list">
        <div v-for="v in videos" :key="v.id" class="t-card" :class="{ active: current && current.id === v.id }" @click="play(v)">
          <div class="t-card-title">{{ v.title }}</div>
          <div class="t-card-meta">
            <el-tag size="small" effect="plain">{{ v.category }}</el-tag>
            <span class="t-dur">{{ v.duration }}</span>
          </div>
          <div class="t-card-ops">
            <el-button link type="primary" size="small" @click.stop="openEdit(v)">编辑</el-button>
            <el-button link type="danger" size="small" @click.stop="remove(v)">删除</el-button>
          </div>
        </div>
        <el-empty v-if="!videos.length" description="暂无视频，点击右上角新增" :image-size="80" />
      </div>
    </div>

    <div class="t-right" v-if="current">
      <div class="t-player">
        <video v-if="current.type !== 'bilibili'" :src="current.src" controls autoplay style="width:100%;max-height:420px;background:#000" />
        <iframe v-else :src="'https://player.bilibili.com/player.html?bvid=' + current.src + '&autoplay=0'" style="width:100%;height:420px;border:0" allowfullscreen />
      </div>
      <div class="t-info">
        <h3>{{ current.title }}</h3>
        <p class="t-desc">{{ current.desc }}</p>
        <div class="t-tags">
          <el-tag size="small" effect="plain">{{ current.category }}</el-tag>
          <el-tag size="small" effect="plain">时长 {{ current.duration }}</el-tag>
          <el-tag size="small" effect="plain" v-if="current.type === 'bilibili'">B站嵌入</el-tag>
          <el-tag size="small" effect="plain" v-else>视频链接</el-tag>
        </div>
      </div>
    </div>
    <div class="t-right t-empty" v-else>
      <el-empty description="从左侧选择视频开始学习" />
    </div>

    <el-dialog v-model="visible" :title="editingId ? '编辑视频' : '新增视频'" width="520px" @closed="reset">
      <el-form :model="form" label-width="84px">
        <el-form-item label="标题" required><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" allow-create filterable placeholder="选择或输入分类" style="width:100%">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="form.type">
            <el-radio value="file">视频文件/链接</el-radio>
            <el-radio value="bilibili">B站视频(BV)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="视频地址" required>
          <el-input v-model="form.src" :placeholder="form.type === 'bilibili' ? '填入 BV 号，如 BV1xx...' : '填入 mp4 直链地址'" />
        </el-form-item>
        <el-form-item label="时长"><el-input v-model="form.duration" placeholder="如 12:30" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="form.desc" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { integrationApi } from '@/api'

const videos = ref([])
const categories = ref(['财税知识', '销售技巧', '软件操作', '合规风控'])
const category = ref('')
const current = ref(null)
const visible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const form = reactive({ title: '', category: '财税知识', type: 'file', src: '', duration: '', desc: '' })

async function load() {
  try {
    const r = await integrationApi.trainingVideos({ category: category.value })
    const list = Array.isArray(r.data) ? r.data : (r.data?.data || [])
    videos.value = list
    if (!current.value && list.length) current.value = list[0]
  } catch (e) {}
}
function play(v) { current.value = v }
function reset() {
  form.title = ''; form.category = '财税知识'; form.type = 'file'; form.src = ''; form.duration = ''; form.desc = ''
}
function openCreate() { reset(); editingId.value = null; visible.value = true }
function openEdit(v) { reset(); Object.assign(form, v); editingId.value = v.id; visible.value = true }
async function submit() {
  saving.value = true
  try {
    if (editingId.value) await integrationApi.updateTrainingVideo(editingId.value, { ...form })
    else await integrationApi.createTrainingVideo({ ...form })
    ElMessage.success('已保存'); visible.value = false; await load()
  } catch (e) { ElMessage.error('保存失败，请检查字段') } finally { saving.value = false }
}
async function remove(v) {
  try { await ElMessageBox.confirm('确认删除该视频？', '提示', { type: 'warning' }) } catch { return }
  try {
    await integrationApi.deleteTrainingVideo(v.id)
    ElMessage.success('已删除'); if (current.value?.id === v.id) current.value = null; await load()
  } catch (e) { ElMessage.error('删除失败') }
}
onMounted(load)
</script>

<style scoped>
.train { display: flex; gap: 16px; height: 100%; }
.t-left { width: 320px; display: flex; flex-direction: column; background: #fff; border-radius: 10px; padding: 12px; }
.t-left-head { display: flex; gap: 8px; margin-bottom: 10px; }
.t-list { flex: 1; overflow-y: auto; }
.t-card { padding: 10px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 8px; cursor: pointer; transition: .15s; }
.t-card:hover { border-color: var(--primary); }
.t-card.active { border-color: var(--primary); background: var(--primary-50); }
.t-card-title { font-weight: 600; font-size: 14px; margin-bottom: 6px; }
.t-card-meta { display: flex; align-items: center; gap: 8px; }
.t-dur { font-size: 12px; color: var(--text-sub); }
.t-card-ops { margin-top: 6px; text-align: right; }
.t-right { flex: 1; background: #fff; border-radius: 10px; padding: 16px; overflow-y: auto; }
.t-player { background: #000; border-radius: 8px; overflow: hidden; display: flex; justify-content: center; }
.t-info { margin-top: 14px; }
.t-info h3 { margin: 0 0 8px; }
.t-desc { color: var(--text-sub); font-size: 13px; line-height: 1.7; }
.t-tags { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.t-empty { display: flex; align-items: center; justify-content: center; }
</style>
