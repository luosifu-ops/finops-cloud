<template>
  <div class="sysinteg-page">
    <!-- 顶部指标 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">已对接资源</div>
          <div class="mini-value">{{ total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">腾讯云</div>
          <div class="mini-value primary">{{ countByProvider('TENCENT') }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">阿里云</div>
          <div class="mini-value success">{{ countByProvider('ALI') }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="mini-card">
          <div class="mini-label">健康异常</div>
          <div class="mini-value" :class="{ warn: badCount > 0 }">{{ badCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-tabs v-model="activeTab">
      <!-- Tab1 资源列表 -->
      <el-tab-pane label="资源对接" name="list">
        <el-card shadow="never" class="main-card">
          <template #header>
            <div class="card-header">
              <span>云资源对接 · 域名 / 存储 / 服务器（仅官方渠道）</span>
              <div>
                <el-button type="primary" @click="openAdd">+ 新增对接</el-button>
                <el-button @click="loadAll">刷新</el-button>
              </div>
            </div>
          </template>

          <el-table :data="list" v-loading="loading" border stripe size="default">
            <el-table-column label="厂商" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="row.provider === 'TENCENT' ? 'primary' : 'success'">
                  {{ row.provider_label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                {{ row.resource_type_label }}
              </template>
            </el-table-column>
            <el-table-column prop="name" label="资源名" min-width="160" />
            <el-table-column prop="endpoint" label="官方接入点" min-width="240" />
            <el-table-column prop="region" label="地域" width="120" />
            <el-table-column prop="bucket_or_instance" label="桶/实例" min-width="160" />
            <el-table-column label="容量" width="110">
              <template #default="{ row }">
                <span v-if="row.capacity_gb">{{ row.capacity_gb }}GB<small v-if="row.capacity_max_gb"> / {{ row.capacity_max_gb }}GB</small></span>
                <span v-else class="muted">-</span>
              </template>
            </el-table-column>
            <el-table-column label="最近检测" width="200">
              <template #default="{ row }">
                <template v-if="row.last_check_at">
                  <el-tag size="small" :type="row.last_check_ok ? 'success' : 'danger'">
                    {{ row.last_check_ok ? '✓ 通' : '✗ 断' }}
                  </el-tag>
                  <span class="muted" style="margin-left:6px">{{ row.last_check_msg?.slice(0,18) }}</span>
                </template>
                <span v-else class="muted">未检测</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="doCheck(row)">检测</el-button>
                <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                <el-button link type="danger" @click="doDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="!loading && !list.length" description="尚未配置任何云资源" />
        </el-card>
      </el-tab-pane>

      <!-- Tab2 容量分布 -->
      <el-tab-pane label="容量分布" name="capacity">
        <el-card shadow="never" class="main-card">
          <template #header>
            <span>容量分布与按需扩容 · 官方云资源总览</span>
          </template>
          <el-table :data="capacity" border stripe size="default">
            <el-table-column label="厂商" width="120">
              <template #default="{ row }">
                <el-tag size="small" :type="row.provider === 'TENCENT' ? 'primary' : 'success'">
                  {{ row.provider === 'TENCENT' ? '腾讯云' : '阿里云' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="资源类型" width="120">
              <template #default="{ row }">
                <span v-if="row.resource_type==='STORAGE'">对象存储</span>
                <span v-else-if="row.resource_type==='SERVER'">云服务器</span>
                <span v-else-if="row.resource_type==='DATABASE'">云数据库</span>
                <span v-else>域名 DNS</span>
              </template>
            </el-table-column>
            <el-table-column prop="count" label="资源数" width="120" align="right" />
            <el-table-column prop="used_gb" label="当前用量(GB)" width="160" align="right" />
            <el-table-column prop="max_gb" label="可扩容量(GB)" width="160" align="right" />
            <el-table-column label="是否可扩容" width="140">
              <template #default="{ row }">
                <el-tag v-if="row.expandable" type="success" size="small">✓ 可扩容</el-tag>
                <el-tag v-else type="danger" size="small">✗ 已达上限</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="占用率">
              <template #default="{ row }">
                <el-progress v-if="row.max_gb > 0" :percentage="Math.round(row.used_gb / row.max_gb * 100)" :color="row.used_gb / row.max_gb > 0.8 ? '#e6a23c' : '#67c23a'" />
                <span v-else class="muted">无限制</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="formVisible" :title="editing ? '编辑云资源配置' : '新增云资源对接（仅官方）'" width="640px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="云厂商" required>
          <el-radio-group v-model="form.provider">
            <el-radio-button label="TENCENT">腾讯云</el-radio-button>
            <el-radio-button label="ALI">阿里云</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="资源类型" required>
          <el-select v-model="form.resource_type" placeholder="选择类型" style="width:100%">
            <el-option label="域名 DNS" value="DOMAIN" />
            <el-option label="对象存储" value="STORAGE" />
            <el-option label="云服务器" value="SERVER" />
            <el-option label="云数据库" value="DATABASE" />
          </el-select>
        </el-form-item>
        <el-form-item label="资源名" required>
          <el-input v-model="form.name" placeholder="如：财税企管云主桶" />
        </el-form-item>
        <el-form-item label="官方接入点" required>
          <el-input v-model="form.endpoint" placeholder="https://cos.ap-guangzhou.myqcloud.com">
            <template #append>
              <el-button @click="form.endpoint = ''">清空</el-button>
            </template>
          </el-input>
          <span style="font-size:12px;color:#909399;line-height:1.4">
            只允许腾讯云 / 阿里云官方 endpoint，例如：tencent.com.cn / myqcloud.com / dnspod.cn / qcloud.com / aliyuncs.com / aliyun.com / alidns.com
          </span>
        </el-form-item>
        <el-form-item label="地域">
          <el-input v-model="form.region" placeholder="如 ap-guangzhou / cn-hangzhou" />
        </el-form-item>
        <el-form-item label="桶名 / 实例ID">
          <el-input v-model="form.bucket_or_instance" placeholder="对象存储桶名 或 云服务器实例 ID" />
        </el-form-item>
        <el-form-item label="访问密钥 ID">
          <el-input v-model="form.access_key_id" placeholder="AKID..." />
        </el-form-item>
        <el-form-item label="访问密钥 Secret">
          <el-input v-model="form.access_key_secret_enc" type="password" show-password placeholder="服务端加密存储，仅返回脱敏后 4 位" />
        </el-form-item>
        <el-form-item label="当前容量(GB)">
          <el-input-number v-model="form.capacity_gb" :min="0" :step="100" style="width:200px" />
          <span style="margin-left:8px;color:#909399;font-size:12px">域名/服务器可填 0</span>
        </el-form-item>
        <el-form-item label="最大可扩容(GB)">
          <el-input-number v-model="form.capacity_max_gb" :min="0" :step="100" style="width:200px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
        <el-alert v-if="!editing" type="warning" :closable="false" show-icon
                  title="Boss 2026-09-07 指示：所有云资源必须直连腾讯云/阿里云官方渠道，禁止使用任何第三方中间商。" />
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">{{ editing ? '保存' : '新增' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const list = ref([])
const capacity = ref([])
const loading = ref(false)
const submitting = ref(false)
const activeTab = ref('list')
const formVisible = ref(false)
const editing = ref(false)

const form = reactive({
  id: null, provider: 'TENCENT', resource_type: 'STORAGE',
  name: '', endpoint: '', region: '', access_key_id: '', access_key_secret_enc: '',
  bucket_or_instance: '', capacity_gb: 0, capacity_max_gb: 0, notes: '',
})

function http() {
  const h = axios.create({ baseURL: '/api', timeout: 30000 })
  const t = localStorage.getItem('token')
  if (t) h.defaults.headers.Authorization = 'Bearer ' + t
  return h
}

const total = computed(() => list.value.length)
function countByProvider(p) { return list.value.filter(r => r.provider === p).length }
const badCount = computed(() => list.value.filter(r => r.last_check_at && !r.last_check_ok).length)

async function loadAll() {
  loading.value = true
  try {
    const res = await http().get('/integrations/resources/')
    const raw = res.data
    list.value = Array.isArray(raw?.results) ? raw.results : (Array.isArray(raw) ? raw : [])
  } finally { loading.value = false }
}

async function loadCapacity() {
  try {
    const res = await http().get('/integrations/resources/capacity/')
    const raw = res.data
    capacity.value = Array.isArray(raw) ? raw : (Array.isArray(raw?.results) ? raw.results : [])
  } catch (e) { capacity.value = [] }
}

async function doCheck(row) {
  try {
    const res = await http().post(`/integrations/resources/${row.id}/check/`)
    if (res.data.ok) ElMessage.success('检测通过：' + res.data.msg)
    else ElMessage.warning('检测失败：' + res.data.msg)
    loadAll()
  } catch (e) {}
}

function openAdd() {
  editing.value = false
  Object.assign(form, {
    id: null, provider: 'TENCENT', resource_type: 'STORAGE',
    name: '', endpoint: '', region: '', access_key_id: '', access_key_secret_enc: '',
    bucket_or_instance: '', capacity_gb: 0, capacity_max_gb: 0, notes: '',
  })
  formVisible.value = true
}

function openEdit(row) {
  editing.value = true
  Object.assign(form, {
    id: row.id,
    provider: row.provider, resource_type: row.resource_type,
    name: row.name, endpoint: row.endpoint, region: row.region,
    access_key_id: row.access_key_id, access_key_secret_enc: '',
    bucket_or_instance: row.bucket_or_instance,
    capacity_gb: row.capacity_gb, capacity_max_gb: row.capacity_max_gb,
    notes: row.notes,
  })
  formVisible.value = true
}

async function submitForm() {
  if (!form.name) return ElMessage.warning('请填写资源名')
  if (!form.endpoint) return ElMessage.warning('请填写官方接入点')
  submitting.value = true
  try {
    const payload = { ...form }
    delete payload.id
    // 创建时若密钥为空就跳过该字段；编辑时若密钥为空也不覆盖
    if (!form.access_key_secret_enc) delete payload.access_key_secret_enc
    if (editing.value) {
      await http().patch(`/integrations/resources/${form.id}/`, payload)
      ElMessage.success('已保存')
    } else {
      await http().post('/integrations/resources/', payload)
      ElMessage.success('已新增')
    }
    formVisible.value = false
    loadAll()
  } catch (e) {} finally { submitting.value = false }
}

async function doDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除 ${row.provider_label} ${row.resource_type_label} - ${row.name}？`, '删除', { type: 'warning' })
    await http().delete(`/integrations/resources/${row.id}/`)
    ElMessage.success('已删除')
    loadAll()
  } catch (e) {}
}

onMounted(() => { loadAll(); loadCapacity() })
</script>

<style scoped>
.sysinteg-page { padding: 4px; }
.stat-row { margin-bottom: 14px; }
.mini-card { text-align: center; }
.mini-label { font-size: 13px; color: #909399; }
.mini-value { font-size: 24px; font-weight: 600; margin-top: 6px; color: #303133; }
.mini-value.primary { color: #2a4fd4; }
.mini-value.success { color: #ff6600; }
.mini-value.warn { color: #e6a23c; }
.main-card { margin-top: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.muted { color: #909399; font-size: 12px; }
</style>
