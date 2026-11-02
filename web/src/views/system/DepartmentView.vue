<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">组织架构管理</h2>
        <span class="page-tip">部门 / 小组的增删改查 · 公司扩张时在此新增部门，员工申请入职即可选择</span>
      </div>
      <div class="header-btns">
        <el-button type="primary" @click="openDeptDialog()">＋ 新增部门</el-button>
        <el-button @click="openTeamDialog()">＋ 新增小组</el-button>
        <el-button circle :icon="Refresh" @click="load" />
      </div>
    </div>

    <el-table :data="departments" v-loading="loading" row-key="id" border stripe>
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="expand-box">
            <div class="expand-title">「{{ row.name }}」下的小组</div>
            <el-table :data="teamsOf(row.id)" size="small" border>
              <el-table-column prop="name" label="小组名称" width="180" />
              <el-table-column prop="leader_name" label="组长" width="140">
                <template #default="{ row: t }">{{ t.leader_name || '—' }}</template>
              </el-table-column>
              <el-table-column prop="member_count" label="人数" width="80" />
              <el-table-column prop="month_target" label="月度目标(元)" width="140">
                <template #default="{ row: t }">¥{{ fmt(t.month_target) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="150">
                <template #default="{ row: t }">
                  <el-button link type="primary" size="small" @click="openTeamDialog(t)">编辑</el-button>
                  <el-button link type="danger" size="small" @click="removeTeam(t)">删除</el-button>
                </template>
              </el-table-column>
              <template #empty>该部门暂无小组</template>
            </el-table>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="部门名称" min-width="140" />
      <el-table-column prop="code" label="编码" width="110" />
      <el-table-column label="上级部门" width="130">
        <template #default="{ row }">{{ parentName(row.parent) }}</template>
      </el-table-column>
      <el-table-column prop="leader_name" label="负责人" width="120">
        <template #default="{ row }">{{ row.leader_name || '—' }}</template>
      </el-table-column>
      <el-table-column prop="member_count" label="在职人数" width="90" align="center" />
      <el-table-column prop="order" label="排序" width="70" align="center" />
      <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDeptDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="removeDept(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="还没有部门，点右上角「新增部门」创建第一个" :image-size="80" />
      </template>
    </el-table>

    <!-- 部门新增 / 编辑弹窗 -->
    <el-dialog v-model="deptDialog.visible" :title="deptDialog.id ? '编辑部门' : '新增部门'" width="520px" destroy-on-close>
      <el-form :model="deptDialog.form" label-width="100px">
        <el-form-item label="部门名称" required>
          <el-input v-model="deptDialog.form.name" placeholder="如：财税顾问一部" maxlength="50" />
        </el-form-item>
        <el-form-item label="部门编码" required>
          <el-input v-model="deptDialog.form.code" placeholder="如 SALES / ACCOUNT（唯一，建议大写英文）" maxlength="30" />
        </el-form-item>
        <el-form-item label="上级部门">
          <el-select v-model="deptDialog.form.parent" placeholder="不选则为顶级部门" clearable filterable style="width:100%">
            <el-option v-for="d in departments.filter(x => x.id !== deptDialog.id)" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人">
          <el-select v-model="deptDialog.form.leader" placeholder="选择员工" clearable filterable style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="deptDialog.form.order" :min="0" :max="999" />
          <span class="form-tip">数字越小越靠前</span>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="deptDialog.form.description" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deptDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="deptDialog.saving" @click="saveDept">保存</el-button>
      </template>
    </el-dialog>

    <!-- 小组新增 / 编辑弹窗 -->
    <el-dialog v-model="teamDialog.visible" :title="teamDialog.id ? '编辑小组' : '新增小组'" width="520px" destroy-on-close>
      <el-form :model="teamDialog.form" label-width="100px">
        <el-form-item label="小组名称" required>
          <el-input v-model="teamDialog.form.name" placeholder="如：电销一组" maxlength="50" />
        </el-form-item>
        <el-form-item label="所属部门" required>
          <el-select v-model="teamDialog.form.department" placeholder="选择部门" filterable style="width:100%">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="组长">
          <el-select v-model="teamDialog.form.leader" placeholder="选择员工" clearable filterable style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.display_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="月度目标">
          <el-input-number v-model="teamDialog.form.month_target" :min="0" :precision="2" style="width:220px" />
          <span class="form-tip">元</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="teamDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="teamDialog.saving" @click="saveTeam">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { orgApi } from '@/api'

const loading = ref(false)
const departments = ref([])
const teams = ref([])
const users = ref([])

const fmt = (n) => (n === undefined || n === null ? '0' : Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 2 }))
const parentName = (pid) => {
  if (pid == null) return '—'
  const d = departments.value.find(x => x.id === pid)
  return d ? d.name : '—'
}
const teamsOf = (deptId) => teams.value.filter(t => (typeof t.department === 'object' ? t.department?.id : t.department) === deptId)

const load = async () => {
  loading.value = true
  try {
    const [dRes, tRes, uRes] = await Promise.all([
      orgApi.departments({ page_size: 100 }),
      orgApi.teams({ page_size: 200 }),
      orgApi.users({ page_size: 500 }),
    ])
    const pick = (r) => (Array.isArray(r) ? r : (r.results || r.data?.results || []))
    departments.value = pick(dRes).slice().sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    teams.value = pick(tRes)
    users.value = pick(uRes).filter(u => u.status !== 'RESIGNED')
  } finally { loading.value = false }
}

// ---------- 部门 ----------
const deptDialog = reactive({ visible: false, id: null, saving: false, form: {} })

function openDeptDialog(row) {
  deptDialog.id = row ? row.id : null
  deptDialog.form = row
    ? { name: row.name, code: row.code, parent: row.parent ?? null, leader: row.leader ?? null, order: row.order ?? 0, description: row.description || '' }
    : { name: '', code: '', parent: null, leader: null, order: (departments.value.length + 1) * 10, description: '' }
  deptDialog.visible = true
}

async function saveDept() {
  const f = deptDialog.form
  if (!f.name?.trim()) return ElMessage.warning('请填写部门名称')
  if (!f.code?.trim()) return ElMessage.warning('请填写部门编码（如 SALES）')
  if (!deptDialog.id) {
    const dup = departments.value.find(d => d.code.toUpperCase() === f.code.trim().toUpperCase())
    if (dup) return ElMessage.warning(`编码 ${f.code} 已被「${dup.name}」使用，请换一个`)
  }
  deptDialog.saving = true
  try {
    const payload = {
      name: f.name.trim(), code: f.code.trim().toUpperCase(),
      parent: f.parent || null, leader: f.leader || null,
      order: f.order || 0, description: f.description || '',
    }
    if (deptDialog.id) await orgApi.updateDepartment(deptDialog.id, payload)
    else await orgApi.createDepartment(payload)
    ElMessage.success(deptDialog.id ? '部门已更新' : '部门已创建，员工申请入职时即可选择')
    deptDialog.visible = false
    await load()
  } catch (e) {} finally { deptDialog.saving = false }
}

async function removeDept(row) {
  const memberCount = row.member_count ?? 0
  const teamCount = teamsOf(row.id).length
  if (memberCount > 0) {
    return ElMessage.warning(`「${row.name}」还有 ${memberCount} 名在职员工，请先在员工管理中转移他们的部门，再删除`)
  }
  if (teamCount > 0) {
    return ElMessage.warning(`「${row.name}」下还有 ${teamCount} 个小组，请先删除这些小组`)
  }
  const ok = await ElMessageBox.confirm(
    `确认删除部门「${row.name}」？删除后员工申请入职将不能再选择它。`,
    '删除部门', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
  ).then(() => true).catch(() => false)
  if (!ok) return
  try {
    await orgApi.deleteDepartment(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {}
}

// ---------- 小组 ----------
const teamDialog = reactive({ visible: false, id: null, saving: false, form: {} })

function openTeamDialog(row) {
  teamDialog.id = row ? row.id : null
  teamDialog.form = row
    ? {
        name: row.name,
        department: typeof row.department === 'object' ? row.department?.id : row.department,
        leader: row.leader ?? null,
        month_target: Number(row.month_target || 0),
      }
    : { name: '', department: null, leader: null, month_target: 0 }
  teamDialog.visible = true
}

async function saveTeam() {
  const f = teamDialog.form
  if (!f.name?.trim()) return ElMessage.warning('请填写小组名称')
  if (!f.department) return ElMessage.warning('请选择所属部门')
  teamDialog.saving = true
  try {
    const payload = { name: f.name.trim(), department: f.department, leader: f.leader || null, month_target: f.month_target || 0 }
    if (teamDialog.id) await orgApi.updateTeam(teamDialog.id, payload)
    else await orgApi.createTeam(payload)
    ElMessage.success(teamDialog.id ? '小组已更新' : '小组已创建')
    teamDialog.visible = false
    await load()
  } catch (e) {} finally { teamDialog.saving = false }
}

async function removeTeam(row) {
  if ((row.member_count ?? 0) > 0) {
    return ElMessage.warning(`「${row.name}」还有 ${row.member_count} 名成员，请先转移成员再删除小组`)
  }
  const ok = await ElMessageBox.confirm(`确认删除小组「${row.name}」？`, '删除小组', { type: 'warning' }).then(() => true).catch(() => false)
  if (!ok) return
  try {
    await orgApi.deleteTeam(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {}
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
.page-tip { font-size: 12px; color: var(--text-sub); font-weight: 400; }
.header-btns { display: flex; gap: 4px; }
.expand-box { padding: 8px 16px 12px 48px; }
.expand-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.form-tip { margin-left: 10px; font-size: 12px; color: var(--text-sub); }
</style>
