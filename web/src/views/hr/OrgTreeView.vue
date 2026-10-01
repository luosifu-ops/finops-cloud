<template>
  <div class="org-tree">
    <el-row :gutter="16">
      <!-- 组织架构树 -->
      <el-col :span="8">
        <el-card shadow="never" class="tree-card">
          <template #header>
            <div class="card-header">
              <span>组织架构（钉钉式层级）</span>
              <el-button v-if="canManage" size="small" type="primary" @click="openDept(null)">+ 部门</el-button>
            </div>
          </template>
          <el-tree
            :data="tree" :props="{ label: 'name', children: 'children' }"
            node-key="id" default-expand-all highlight-current
            @current-change="onSelect">
            <template #default="{ data }">
              <span class="tree-node">{{ data.name }}
                <el-tag size="small" type="info">{{ codeLabel(data.code) }}</el-tag>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- 部门详情 -->
      <el-col :span="16">
        <el-card shadow="never" v-if="selected" class="detail-card">
          <template #header>
            <div class="card-header">
              <span>{{ selected.name }} · 部门配置</span>
              <el-button v-if="canManage" size="small" @click="openDept(selected)">编辑部门</el-button>
            </div>
          </template>

          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="部门编码">{{ codeLabel(selected.code) }}</el-descriptions-item>
            <el-descriptions-item label="上级部门">{{ parentName(selected.parent) }}</el-descriptions-item>
            <el-descriptions-item label="负责人">{{ leaderName(selected.leader) }}</el-descriptions-item>
            <el-descriptions-item label="职责">{{ selected.description || '-' }}</el-descriptions-item>
          </el-descriptions>

          <!-- 岗位 -->
          <el-divider content-position="left">
            岗位编制
            <el-button v-if="canManage" size="small" type="primary" link @click="openPos(null)">+ 新增岗位</el-button>
          </el-divider>
          <el-table :data="positions" border size="small" v-loading="posLoading" max-height="220">
            <el-table-column prop="name" label="岗位名称" />
            <el-table-column prop="level" label="职级" width="100" />
            <el-table-column prop="description" label="职责" show-overflow-tooltip />
            <el-table-column label="操作" width="120" v-if="canManage">
              <template #default="{ row }">
                <el-button link type="primary" @click="openPos(row)">编辑</el-button>
                <el-button link type="danger" @click="delPos(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!positions.length && !posLoading" description="暂无岗位" />

          <!-- 部门 / 岗位制度 -->
          <el-divider content-position="left">
            考勤 / 考核制度
            <el-button v-if="canManage" size="small" type="warning" link @click="openRule(null)">+ 新增制度</el-button>
          </el-divider>
          <el-table :data="rules" border size="small" v-loading="ruleLoading" max-height="220">
            <el-table-column label="类型" width="110">
              <template #default="{ row }"><el-tag size="small" :type="row.rule_type==='ATTENDANCE'?'primary':'success'">{{ row.rule_type_label }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="title" label="标题" width="140" />
            <el-table-column prop="position_name" label="适用岗位" width="110" />
            <el-table-column prop="content" label="内容" show-overflow-tooltip />
            <el-table-column label="操作" width="120" v-if="canManage">
              <template #default="{ row }">
                <el-button link type="primary" @click="openRule(row)">编辑</el-button>
                <el-button link type="danger" @click="delRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!rules.length && !ruleLoading" description="暂无制度，点击右上角新增" />
        </el-card>
        <el-empty v-else description="请从左侧选择部门查看配置" />
      </el-col>
    </el-row>

    <!-- 部门编辑 -->
    <el-dialog v-model="deptVisible" :title="deptForm.id ? '编辑部门' : '新增部门'" width="520px">
      <el-form :model="deptForm" label-width="100px">
        <el-form-item label="部门名称" required><el-input v-model="deptForm.name" /></el-form-item>
        <el-form-item label="部门编码" required>
          <el-select v-model="deptForm.code" style="width:100%" :disabled="!!deptForm.id">
            <el-option label="电销部" value="SALES" />
            <el-option label="会计部" value="ACCOUNT" />
            <el-option label="运营部" value="OPS" />
            <el-option label="管理层" value="MGMT" />
          </el-select>
        </el-form-item>
        <el-form-item label="上级部门">
          <el-select v-model="deptForm.parent" placeholder="无（一级部门）" clearable style="width:100%">
            <el-option v-for="d in deptOptions" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="deptForm.leader" placeholder="选择负责人" clearable style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="deptForm.order" :min="0" /></el-form-item>
        <el-form-item label="部门职责"><el-input v-model="deptForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deptVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveDept">保存</el-button>
      </template>
    </el-dialog>

    <!-- 岗位编辑 -->
    <el-dialog v-model="posVisible" :title="posForm.id ? '编辑岗位' : '新增岗位'" width="480px">
      <el-form :model="posForm" label-width="90px">
        <el-form-item label="岗位名称" required><el-input v-model="posForm.name" /></el-form-item>
        <el-form-item label="职级"><el-input v-model="posForm.level" placeholder="如：P1 / M1" /></el-form-item>
        <el-form-item label="所属部门"><el-input :model-value="selected?.name" disabled /></el-form-item>
        <el-form-item label="职责"><el-input v-model="posForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="posVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePos">保存</el-button>
      </template>
    </el-dialog>

    <!-- 制度编辑 -->
    <el-dialog v-model="ruleVisible" :title="ruleForm.id ? '编辑制度' : '新增制度'" width="520px">
      <el-form :model="ruleForm" label-width="90px">
        <el-form-item label="制度类型" required>
          <el-select v-model="ruleForm.rule_type" style="width:100%">
            <el-option label="考勤制度" value="ATTENDANCE" />
            <el-option label="考核制度" value="ASSESSMENT" />
          </el-select>
        </el-form-item>
        <el-form-item label="适用岗位">
          <el-select v-model="ruleForm.position" placeholder="全部门通用" clearable style="width:100%">
            <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" required><el-input v-model="ruleForm.title" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="ruleForm.content" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { orgApi } from '@/api/index'
import { useUserStore } from '@/store/user'

const store = useUserStore()
const canManage = computed(() => store.isBoss || store.isManager || store.isHR || store.isSuper)

const departments = ref([])
const users = ref([])
const tree = ref([])
// 部门编码 → 中文展示（仅前端展示，不改变后端编码字段）
const CODE_LABELS = {
  SALES: '电销部', ACCOUNT: '会计部', OPS: '运营部', MGMT: '管理层',
  HR: '人力资源部', FIN: '财务部', ADMIN: '行政部',
}
const codeLabel = (c) => CODE_LABELS[c] || c || '-'
// 部门/组织名称兜底：后端若返回英文系统标识（root/company 等）转中文
const NAME_LABELS = { root: '公司', ROOT: '公司', company: '公司', COMPANY: '公司', org: '组织', ORG: '组织' }
const nameLabel = (n) => NAME_LABELS[n] || n || '-'
const selected = ref(null)
const positions = ref([])
const rules = ref([])
const posLoading = ref(false)
const ruleLoading = ref(false)
const saving = ref(false)

const deptVisible = ref(false)
const posVisible = ref(false)
const ruleVisible = ref(false)

const deptForm = reactive({ id: null, name: '', code: 'SALES', parent: null, leader: null, order: 0, description: '' })
const posForm = reactive({ id: null, name: '', level: '', description: '' })
const ruleForm = reactive({ id: null, rule_type: 'ATTENDANCE', position: null, title: '', content: '' })

const deptOptions = computed(() => departments.value.filter(d => d.id !== deptForm.id))

function buildTree(list) {
  const map = {}
  list.forEach(d => (map[d.id] = { ...d, children: [] }))
  const roots = []
  list.forEach(d => {
    if (d.parent) (map[d.parent]?.children || roots).push(map[d.id])
    else roots.push(map[d.id])
  })
  return roots
}
function parentName(pid) { const d = departments.value.find(x => x.id === pid); return d ? d.name : '无（一级部门）' }
function leaderName(uid) { const u = users.value.find(x => x.id === uid); return u ? (u.display_name || u.username) : '未设置' }

async function loadDepts() {
  try {
    const r = await orgApi.departments()
    departments.value = Array.isArray(r) ? r : (r.results || [])
    tree.value = buildTree(departments.value)
  } catch (e) {}
}
async function loadUsers() {
  try { const r = await orgApi.users({ page_size: 200 }); users.value = Array.isArray(r) ? r : (r.results || []) } catch (e) {}
}
async function loadPositions(deptId) {
  posLoading.value = true
  try { const r = await orgApi.positions({ department: deptId }); positions.value = Array.isArray(r) ? r : (r.results || []) } finally { posLoading.value = false }
}
async function loadRules(deptId) {
  ruleLoading.value = true
  try { const r = await orgApi.deptRules({ department: deptId }); rules.value = Array.isArray(r) ? r : (r.results || []) } finally { ruleLoading.value = false }
}
function onSelect(node) {
  if (!node) return
  selected.value = node
  loadPositions(node.id)
  loadRules(node.id)
}

function openDept(d) {
  Object.assign(deptForm, d ? { id: d.id, name: d.name, code: d.code, parent: d.parent, leader: d.leader, order: d.order || 0, description: d.description || '' }
    : { id: null, name: '', code: 'SALES', parent: selected.value?.id || null, leader: null, order: 0, description: '' })
  deptVisible.value = true
}
async function saveDept() {
  if (!deptForm.name || !deptForm.code) return ElMessage.warning('请填写部门名称与编码')
  saving.value = true
  try {
    if (deptForm.id) await orgApi.updateDepartment(deptForm.id, { ...deptForm })
    else await orgApi.createDepartment({ ...deptForm })
    ElMessage.success('已保存')
    deptVisible.value = false
    await loadDepts()
    if (selected.value && deptForm.id) onSelect(departments.value.find(x => x.id === deptForm.id))
  } finally { saving.value = false }
}

function openPos(p) {
  Object.assign(posForm, p ? { id: p.id, name: p.name, level: p.level || '', description: p.description || '' }
    : { id: null, name: '', level: '', description: '' })
  posVisible.value = true
}
async function savePos() {
  if (!posForm.name) return ElMessage.warning('请填写岗位名称')
  saving.value = true
  try {
    const payload = { name: posForm.name, level: posForm.level, description: posForm.description, department: selected.value.id }
    if (posForm.id) await orgApi.updatePosition(posForm.id, payload)
    else await orgApi.createPosition(payload)
    ElMessage.success('已保存')
    posVisible.value = false
    loadPositions(selected.value.id)
  } finally { saving.value = false }
}
async function delPos(p) {
  const ok = await ElMessageBox.confirm('确认删除该岗位？', '提示').then(() => true).catch(() => false)
  if (!ok) return
  try { await orgApi.deletePosition(p.id); ElMessage.success('已删除'); loadPositions(selected.value.id) } catch (e) {}
}

function openRule(r) {
  Object.assign(ruleForm, r ? { id: r.id, rule_type: r.rule_type, position: r.position, title: r.title, content: r.content || '' }
    : { id: null, rule_type: 'ATTENDANCE', position: null, title: '', content: '' })
  ruleVisible.value = true
}
async function saveRule() {
  if (!ruleForm.title) return ElMessage.warning('请填写制度标题')
  saving.value = true
  try {
    const payload = { department: selected.value.id, rule_type: ruleForm.rule_type, position: ruleForm.position, title: ruleForm.title, content: ruleForm.content }
    if (ruleForm.id) await orgApi.updateDeptRule(ruleForm.id, payload)
    else await orgApi.createDeptRule(payload)
    ElMessage.success('已保存')
    ruleVisible.value = false
    loadRules(selected.value.id)
  } finally { saving.value = false }
}
async function delRule(r) {
  const ok = await ElMessageBox.confirm('确认删除该制度？', '提示').then(() => true).catch(() => false)
  if (!ok) return
  try { await orgApi.deleteDeptRule(r.id); ElMessage.success('已删除'); loadRules(selected.value.id) } catch (e) {}
}

onMounted(() => { loadDepts(); loadUsers() })
</script>

<style scoped>
.org-tree { padding: 4px; }
.tree-card { min-height: 520px; }
.detail-card { min-height: 520px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.tree-node { display: inline-flex; align-items: center; gap: 6px; }
</style>
