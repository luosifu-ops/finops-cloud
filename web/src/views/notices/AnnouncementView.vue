<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">通知公告</h2>
        <span class="page-tip">公司统一发布通知 / 文件，全员可查看并「确认接收」（已读回执）</span>
      </div>
      <div class="header-actions">
        <el-tag v-if="unread > 0" type="danger" effect="dark" round>未读 {{ unread }}</el-tag>
        <el-button :disabled="!list.length" @click="markAllRead">全部已读</el-button>
        <el-button v-if="canPublish" type="primary" :icon="Plus" @click="openPublish">发布通知</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <el-empty v-if="!list.length && !loading" description="暂无通知公告" :image-size="80" />
      <el-card
        v-for="item in list"
        :key="item.id"
        shadow="hover"
        class="ann-card"
        :class="{ unread: !item.is_read }"
      >
        <div class="ann-top">
          <div class="ann-title">
            <el-tag v-if="item.pinned" size="small" type="danger" effect="plain">置顶</el-tag>
            <el-tag size="small" effect="plain">{{ item.category_name }}</el-tag>
            <span class="ann-name">{{ item.title }}</span>
            <el-tag v-if="!item.is_read" size="small" type="warning" effect="dark">未读</el-tag>
            <el-tag v-else size="small" type="success" effect="plain">已读</el-tag>
          </div>
          <div class="ann-meta">
            <span>{{ item.publisher_name }}</span>
            <span>{{ item.created_at }}</span>
            <span>已接收 {{ item.read_count }} 人</span>
          </div>
        </div>

        <div v-if="item.content" class="ann-content">{{ item.content }}</div>

        <div v-if="item.file_url" class="ann-file">
          <el-icon><Paperclip /></el-icon>
          <a :href="item.file_url" target="_blank" class="file-link">{{ item.file_name || '下载附件' }}</a>
          <span class="file-size">{{ formatSize(item.file_size) }}</span>
        </div>

        <div class="ann-actions">
          <el-button
            v-if="!item.is_read"
            type="primary" link size="small"
            @click="markRead(item)"
          >确认接收</el-button>
          <el-button v-if="canPublish" type="danger" link size="small" @click="remove(item)">删除</el-button>
        </div>
      </el-card>
    </div>

    <!-- 发布通知 -->
    <el-dialog v-model="publishVisible" title="发布通知 / 文件" width="560px" @closed="resetPublish">
      <el-form :model="pub" label-width="88px">
        <el-form-item label="标题" required>
          <el-input v-model="pub.title" placeholder="如：关于国庆放假安排的通知" maxlength="200" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="pub.category" style="width:100%">
            <el-option v-for="c in categoryOptions" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="pub.content" type="textarea" :rows="4" placeholder="通知内容" />
        </el-form-item>
        <el-form-item label="置顶">
          <el-switch v-model="pub.pinned" />
        </el-form-item>
        <el-form-item label="附件文件">
          <el-upload
            ref="pubUploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="onPubFileChange"
            :on-exceed="onPubExceed"
            :file-list="pubFileList"
            accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx,.ppt,.pptx"
          >
            <el-button>选择文件</el-button>
          </el-upload>
          <div class="tip">可选，单文件不超过 20MB</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="publishVisible = false">取消</el-button>
        <el-button type="primary" :loading="publishing" @click="submitPublish">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Paperclip } from '@element-plus/icons-vue'
import { noticeApi } from '@/api'
import { useUserStore } from '@/store/user'

const store = useUserStore()
// 发布 / 删除仅管理层(BOSS / MANAGER) 可见（与后端权限一致）
const canPublish = computed(() => store.isBoss || store.isManager)

const list = ref([])
const loading = ref(false)
const unread = ref(0)
const page = ref(1)
const pageSize = ref(50)

const categoryOptions = [
  { value: 'NOTICE', label: '通知' },
  { value: 'ANNOUNCEMENT', label: '公告' },
  { value: 'FILE', label: '文件发布' },
  { value: 'MEETING', label: '会议安排' },
]

function extractRows(resp) {
  const body = resp || {}
  let payload = body
  if (body && typeof body === 'object' && 'code' in body && 'data' in body) payload = body.data
  if (payload && payload.results) return payload.results
  if (Array.isArray(payload)) return payload
  if (payload && typeof payload === 'object') return [payload]
  return []
}

async function reload() {
  loading.value = true
  try {
    const resp = await noticeApi.list({ page: page.value, page_size: pageSize.value })
    list.value = extractRows(resp)
  } catch (e) {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function loadUnread() {
  try {
    const r = await noticeApi.unreadCount()
    const body = r || {}
    const data = ('code' in body && 'data' in body) ? body.data : body
    unread.value = data?.unread ?? 0
  } catch (e) {
    unread.value = 0
  }
}

async function markRead(item) {
  try {
    await noticeApi.markRead(item.id)
    item.is_read = true
    item.read_count = (item.read_count || 0) + 1
    unread.value = Math.max(unread.value - 1, 0)
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function markAllRead() {
  for (const item of list.value) {
    if (!item.is_read) await markRead(item)
  }
  ElMessage.success('已全部标记已读')
}

async function remove(item) {
  try {
    await ElMessageBox.confirm(`确认删除通知「${item.title}」？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await noticeApi.destroy(item.id)
    ElMessage.success('已删除')
    reload(); loadUnread()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

function formatSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

// ---- 发布 ----
const publishVisible = ref(false)
const publishing = ref(false)
const pub = reactive({ title: '', category: 'NOTICE', content: '', pinned: false })
const pubFileList = ref([])
const pubPickedFile = ref(null)
const pubUploadRef = ref(null)

function openPublish() {
  resetPublish()
  publishVisible.value = true
}
function resetPublish() {
  pub.title = ''; pub.category = 'NOTICE'; pub.content = ''; pub.pinned = false
  pubPickedFile.value = null; pubFileList.value = []
}
function onPubFileChange(file) {
  pubPickedFile.value = file.raw || null
  pubFileList.value = file ? [file] : []
}
function onPubExceed(files) {
  pubUploadRef.value?.clearFiles()
  const f = files[0]
  pubUploadRef.value?.handleStart(f)
  pubPickedFile.value = f
}

async function submitPublish() {
  if (!pub.title.trim()) return ElMessage.warning('请填写标题')
  publishing.value = true
  try {
    const resp = await noticeApi.create({
      title: pub.title.trim(),
      category: pub.category,
      content: pub.content || '',
      pinned: pub.pinned,
    })
    const id = resp?.id ?? resp?.data?.id
    if (pubPickedFile.value && id) {
      try {
        await noticeApi.uploadFile(id, pubPickedFile.value)
      } catch (e) {
        ElMessage.warning('通知已发布，但附件上传失败，可稍后重试')
      }
    }
    ElMessage.success('发布成功')
    publishVisible.value = false
    reload(); loadUnread()
  } catch (e) {
    ElMessage.error('发布失败，请重试')
  } finally {
    publishing.value = false
  }
}

onMounted(() => { reload(); loadUnread() })
</script>

<style scoped>
.page { padding: 4px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
.page-title { font-size: 18px; margin: 0; }
.page-tip { font-size: 12px; color: var(--text-sub); margin-left: 10px; font-weight: 400; }
.header-actions { display: flex; align-items: center; gap: 8px; }
.ann-card { margin-bottom: 14px; border-left: 4px solid #dcdfe6; }
.ann-card.unread { border-left-color: #e6a23c; background: #fdf6ec; }
.ann-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.ann-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ann-name { font-size: 16px; font-weight: 700; color: #303133; }
.ann-meta { font-size: 12px; color: #909399; display: flex; gap: 12px; margin-top: 4px; }
.ann-content { margin-top: 10px; font-size: 14px; color: #606266; white-space: pre-wrap; line-height: 1.7; }
.ann-file { margin-top: 10px; display: flex; align-items: center; gap: 6px; color: #909399; }
.file-link { color: #409eff; text-decoration: underline; font-size: 13px; }
.file-size { font-size: 12px; }
.ann-actions { margin-top: 10px; display: flex; gap: 4px; }
.tip { color: #909399; font-size: 12px; line-height: 1.6; }
</style>
