<template>
  <div class="growth-page">
    <el-tabs v-model="activeTab">
      <!-- Tab1: 渠道字典与启用开关 -->
      <el-tab-pane label="渠道字典" name="channels">
        <el-card shadow="never" class="main-card">
          <template #header>
            <div class="card-header">
              <span>渠道字典 · 已启用与预留扩展位</span>
              <div>
                <el-button v-if="isAdmin && pendingReserveCount > 0" type="primary" @click="batchToggle" :loading="batchLoading">
                  一键开启预留位 {{ pendingReserveCount }} 个
                </el-button>
                <el-button @click="loadChannels">刷新</el-button>
              </div>
            </div>
            <!-- 数据自动核算：渠道启用情况实时统计 -->
            <div class="auto-stats">
              <el-tag size="small" type="info">自动核算</el-tag>
              <span class="stat-item">已启用 <b>{{ enabledCount }}</b> 个</span>
              <span class="stat-item">已停用 <b>{{ disabledCount }}</b> 个</span>
              <span class="stat-item">预留位 <b>{{ reservedCount }}</b> 个</span>
            </div>
          </template>

          <el-table :data="channels" v-loading="loading" border stripe size="default">
            <el-table-column prop="name" label="平台名称" width="160" />
            <el-table-column prop="code" label="平台编码" width="120"><template #default="{ row }">{{ codeLabel(row.code) }}</template></el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-switch
                  v-if="isAdmin && !row.is_reserved"
                  v-model="row.is_enabled"
                  @change="quickToggle(row)"
                  active-text="启用"
                  inactive-text="停用" />
                <el-tag v-else-if="row.is_reserved" type="warning" size="small">预留位</el-tag>
                <el-tag v-else :type="row.is_enabled ? 'success' : 'info'" size="small">
                  {{ row.is_enabled ? '已启用' : '已停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.is_reserved" type="warning" size="small">预留（可一键开启）</el-tag>
                <el-tag v-else type="success" size="small">已上线</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="sort" label="排序" width="80" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">{{ fmt(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button v-if="isAdmin" link type="primary" @click="openReserve(row)">
                  {{ row.is_reserved ? '一键开启' : '查看' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!loading && !channels.length" description="暂无渠道数据" />
        </el-card>
      </el-tab-pane>

      <!-- Tab2: 成交师 × 平台 专项分配 -->
      <el-tab-pane label="成交师专项分配" name="closer-matrix">
        <el-card shadow="never" class="main-card">
          <template #header>
            <div class="card-header">
              <span>成交师 × 平台 专项绑定（按平台派单的绑定关系）</span>
              <div>
                <el-button v-if="isAdmin" type="primary" @click="openAddBinding">+ 新增绑定</el-button>
                <el-button @click="loadCloserChannels">刷新</el-button>
              </div>
            </div>
          </template>

          <el-alert type="info" :closable="false" show-icon
                    title="说明：仅成交师有专项绑定时，该平台的线索会优先派给绑定人；负载相同则按优先级高者优先；无绑定则降级全平台成交师按负载分配。" />

          <el-table :data="bindings" v-loading="loadingBinding" border stripe size="default" style="margin-top: 12px">
            <el-table-column prop="user_name" label="成交师" width="140" />
            <el-table-column prop="channel_name" label="专项平台" width="140" />
            <el-table-column prop="channel_code" label="平台编码" width="120"><template #default="{ row }">{{ codeLabel(row.channel_code) }}</template></el-table-column>
            <el-table-column label="优先级" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.priority >= 5 ? 'danger' : (row.priority >= 3 ? 'warning' : 'info')">
                  P{{ row.priority }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-switch v-if="isAdmin" v-model="row.is_active" @change="toggleBinding(row)" />
                <el-tag v-else :type="row.is_active ? 'success' : 'info'" size="small">
                  {{ row.is_active ? '启用' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button v-if="isAdmin" link type="danger" @click="deleteBinding(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!loadingBinding && !bindings.length" description="暂无绑定" />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增绑定对话框 -->
    <el-dialog v-model="bindVisible" title="新增专项绑定" width="480px">
      <el-form :model="bindForm" label-width="100px">
        <el-form-item label="成交师" required>
          <el-select v-model="bindForm.user" placeholder="选择成交师" filterable style="width:100%">
            <el-option v-for="u in closerUsers" :key="u.id" :label="u.display_name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="专项平台" required>
          <el-select v-model="bindForm.channel" placeholder="选择平台" style="width:100%">
            <el-option v-for="c in channels" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="bindForm.priority" :min="1" :max="9" />
          <span style="margin-left:8px;color:#909399;font-size:12px">数字越大越优先</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBinding">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { growthApi } from '@/api/growth'
import { useUserStore } from '@/store/user'
import axios from 'axios'

const store = useUserStore()
const isAdmin = computed(() => store.isAdmin || store.isBoss || store.isSuper)

const activeTab = ref('channels')
const channels = ref([])
const bindings = ref([])
const loading = ref(false)
const loadingBinding = ref(false)
const batchLoading = ref(false)

// ---------- 数据自动核算（实时统计） ----------
const enabledCount = computed(() => channels.value.filter(c => c.is_enabled && !c.is_reserved).length)
const disabledCount = computed(() => channels.value.filter(c => !c.is_enabled && !c.is_reserved).length)
const reservedCount = computed(() => channels.value.filter(c => c.is_reserved).length)
const pendingReserveCount = computed(() => channels.value.filter(c => c.is_reserved && !c.is_enabled).length)

const bindVisible = ref(false)
const bindForm = reactive({ user: null, channel: null, priority: 5 })
const closerUsers = ref([])

function fmt(t) { return t ? String(t).slice(0, 19).replace('T', ' ') : '' }
// 平台编码 → 中文展示（仅前端展示，不改变后端字段）
const PLATFORM_CODE = {
  DOUYIN: '抖音', KUAISHOU: '快手', BAIDU: '百度', WECHAT: '微信',
  XHS: '小红书', SHIPINHAO: '视频号', TOUTIAO: '头条', WEIBO: '微博',
  ZHIHU: '知乎', BILIBILI: 'B站', DOUYINXIAOCHENGXU: '抖音小程序',
  MEITUAN: '美团', DianPING: '大众点评', XIAOHONGSHU: '小红书',
}
const codeLabel = (c) => PLATFORM_CODE[c] || c || '-'

async function loadChannels() {
  loading.value = true
  try {
    const res = await growthApi.allChannels()
    channels.value = Array.isArray(res) ? res : (res.results || [])
  } finally {
    loading.value = false
  }
}

async function loadCloserChannels() {
  loadingBinding.value = true
  try {
    const res = await growthApi.closerChannels()
    bindings.value = Array.isArray(res) ? res : (res.results || [])
  } finally {
    loadingBinding.value = false
  }
}

// ---------- 开关即时保存（拨动即生效，不再依赖批量按钮） ----------
async function quickToggle(row) {
  try {
    const res = await growthApi.toggleChannel(row.id)
    row.is_enabled = !!res.is_enabled
    ElMessage.success(`【${row.name}】已${row.is_enabled ? '启用' : '停用'}`)
  } catch (e) {
    row.is_enabled = !row.is_enabled   // 失败回滚 UI
  }
}

// ---------- 批量：一键开启全部预留位 ----------
async function batchToggle() {
  const targets = channels.value.filter(c => c.is_reserved && !c.is_enabled)
  if (!targets.length) {
    ElMessage.info('当前没有待开启的预留平台')
    return
  }
  try {
    await ElMessageBox.confirm(
      `将一键开启 ${targets.length} 个预留平台（${targets.map(t => t.name).join('、')}），是否继续？`,
      '一键开启预留平台', { type: 'warning' })
    batchLoading.value = true
    for (const t of targets) {
      await growthApi.toggleChannel(t.id)
    }
    ElMessage.success('已开启，可前往线索工作台使用')
    loadChannels()
  } catch (e) {} finally {
    batchLoading.value = false
  }
}

async function openReserve(row) {
  try {
    await ElMessageBox.confirm(
      `确认【${row.name}】${row.is_enabled ? '停用' : '启用'}？`,
      '渠道开关', { type: 'warning' })
    await growthApi.toggleChannel(row.id)
    ElMessage.success('已更新')
    loadChannels()
  } catch (e) {}
}

async function loadCloserUsers() {
  try {
    const http2 = axios.create({ baseURL: '/api', timeout: 20000 })
    const token = localStorage.getItem('token')
    if (token) http2.defaults.headers.Authorization = 'Bearer ' + token
    const res = await http2.get('/accounts/users/', { params: { page_size: 200 } })
    const raw = res.data
    const list = Array.isArray(raw?.results) ? raw.results : (Array.isArray(raw) ? raw : [])
    // 仅列出含 CLOSER 角色的人 + 名字包含"成交"
    closerUsers.value = list.filter(u => u && u.is_active !== false)
  } catch (e) {
    closerUsers.value = []
  }
}

function openAddBinding() {
  Object.assign(bindForm, { user: null, channel: null, priority: 5 })
  if (!closerUsers.value.length) loadCloserUsers()
  bindVisible.value = true
}

async function submitBinding() {
  if (!bindForm.user) return ElMessage.warning('请选择成交师')
  if (!bindForm.channel) return ElMessage.warning('请选择平台')
  try {
    await growthApi.createCloserChannel({ ...bindForm, is_active: true })
    ElMessage.success('已绑定')
    bindVisible.value = false
    loadCloserChannels()
  } catch (e) {}
}

async function toggleBinding(row) {
  try {
    await growthApi.updateCloserChannel(row.id, { is_active: row.is_active })
    ElMessage.success('已更新')
  } catch (e) {
    row.is_active = !row.is_active
  }
}

async function deleteBinding(row) {
  try {
    await ElMessageBox.confirm(`确认删除 ${row.user_name} 绑定 ${row.channel_name}？`, '删除绑定', { type: 'warning' })
    await growthApi.deleteCloserChannel(row.id)
    ElMessage.success('已删除')
    loadCloserChannels()
  } catch (e) {}
}

onMounted(() => {
  loadChannels()
  loadCloserChannels()
})
</script>

<style scoped>
.growth-page { padding: 4px; }
.main-card { margin-top: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.auto-stats {
  display: flex; align-items: center; gap: 16px;
  margin-top: 10px; padding: 8px 12px;
  background: #f5f7fa; border-radius: 8px; font-size: 13px; color: #606266;
}
.auto-stats .stat-item b { color: #303133; }
</style>
