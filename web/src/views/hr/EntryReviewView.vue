<template>
  <div class="entry-review">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>入职申请审核 · 人事管理员</span>
          <div>
            <el-radio-group v-model="filter" size="small" @change="loadData">
              <el-radio-button label="待审核">待审核</el-radio-button>
              <el-radio-button label="全部">全部</el-radio-button>
            </el-radio-group>
            <el-button style="margin-left:8px" @click="loadData">刷新</el-button>
          </div>
        </div>
        <!-- 数据自动核算：当前列表实时统计 -->
        <div class="auto-stats">
          <el-tag size="small" type="info">自动核算</el-tag>
          <span class="stat-item">共 <b>{{ list.length }}</b> 条</span>
          <span class="stat-item warn">待审核 <b>{{ countBy('PENDING') }}</b> 条</span>
          <span class="stat-item ok">已通过 <b>{{ countBy('APPROVED') }}</b> 条</span>
          <span class="stat-item danger">已拒绝 <b>{{ countBy('REJECTED') }}</b> 条</span>
          <span class="stat-item">期望薪资合计 <b>¥ {{ num(sumSalary()) }}</b></span>
        </div>
      </template>

      <el-table :data="list" v-loading="loading" border stripe size="default" max-height="560">
        <el-table-column prop="applicant_name" label="申请人" width="110" />
        <el-table-column prop="phone" label="联系电话" width="140" />
        <el-table-column prop="department_name" label="意向部门" width="110" />
        <el-table-column prop="position_name" label="意向岗位" width="110" />
        <el-table-column label="期望薪资" width="120">
          <template #default="{ row }">{{ num(row.expected_salary) }} 元</template>
        </el-table-column>
        <el-table-column label="简历" width="90">
          <template #default="{ row }">
            <el-button v-if="row.resume_url" link type="primary" @click="openUrl(row.resume_url)">查看</el-button>
            <span v-else class="muted">无</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status==='PENDING'?'warning':(row.status==='APPROVED'?'success':'danger')" size="small">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reviewed_by_name" label="审核人" width="100" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <template v-if="row.status === 'PENDING'">
              <el-button link type="success" @click="openApprove(row)">通过</el-button>
              <el-button link type="danger" @click="reject(row)">拒绝</el-button>
              <el-button link type="primary" @click="openEdit(row)">修改</el-button>
              <el-button link type="danger" @click="remove(row)">删除</el-button>
            </template>
            <template v-else-if="row.status === 'REJECTED'">
              <el-button link type="danger" @click="remove(row)">删除</el-button>
            </template>
            <span v-else class="muted">已处理</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 审核通过弹窗：指定实际部门/岗位/角色（默认带出员工意向） -->
    <el-dialog v-model="approveBox.visible" :title="`审核通过 · ${approveBox.row?.applicant_name || ''}`" width="480px" destroy-on-close>
      <el-alert type="info" :closable="false" show-icon style="margin-bottom:14px"
        title="员工申请时可能选错部门，请在此确认实际入职安排。部门决定他登录后能用哪些功能。" />
      <el-form label-width="90px">
        <el-form-item label="入职部门" required>
          <el-select v-model="approveBox.department" filterable style="width:100%" placeholder="选择部门">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="岗位">
          <el-select v-model="approveBox.position" filterable clearable style="width:100%" placeholder="可选，默认按申请意向">
            <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="系统角色">
          <el-select v-model="approveBox.role" style="width:100%">
            <el-option label="普通员工（只看本部门功能）" value="EMPLOYEE" />
            <el-option label="主管（看本部门+管理页）" value="LEADER" />
            <el-option label="经理（看管理功能）" value="MANAGER" />
            <el-option label="人事（管员工/考勤/审核）" value="HR" />
            <el-option label="老板（全部功能与数据）" value="BOSS" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveBox.visible = false">取消</el-button>
        <el-button type="success" :loading="approveBox.saving" @click="confirmApprove">确认通过并建号</el-button>
      </template>
    </el-dialog>

    <!-- 修改申请弹窗：待审核资料勘误 -->
    <el-dialog v-model="editBox.visible" :title="`修改申请 · ${editBox.row?.applicant_name || ''}`" width="480px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="申请人" required>
          <el-input v-model="editBox.applicant_name" maxlength="50" placeholder="申请人姓名" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="editBox.phone" maxlength="20" placeholder="联系电话" />
        </el-form-item>
        <el-form-item label="意向部门">
          <el-select v-model="editBox.department" filterable clearable style="width:100%" placeholder="选择部门">
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="意向岗位">
          <el-select v-model="editBox.position" filterable clearable style="width:100%" placeholder="选择岗位">
            <el-option v-for="p in positions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="期望薪资">
          <el-input-number v-model="editBox.expected_salary" :min="0" :max="999999" :controls="false" style="width:100%" />
          <span style="margin-left:8px;color:#909399;font-size:12px">元/月</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editBox.remark" type="textarea" :rows="2" placeholder="备注（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editBox.visible = false">取消</el-button>
        <el-button type="primary" :loading="editBox.saving" @click="confirmEdit">保存修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { orgApi } from '@/api/index'

const list = ref([])
const loading = ref(false)
const filter = ref('待审核')

function num(v) { const n = Number(v || 0); return n ? n.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '0' }
function openUrl(u) { if (u) window.open(u, '_blank') }

// ---------- 数据自动核算 ----------
function countBy(status) { return list.value.filter(r => r.status === status).length }
function sumSalary() { return list.value.reduce((s, r) => s + Number(r.expected_salary || 0), 0) }

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filter.value === '待审核') params.status = 'PENDING'
    const r = await orgApi.entries(params)
    list.value = Array.isArray(r) ? r : (r.results || [])
  } finally { loading.value = false }
}

// ---------- 审核通过：可指定实际部门/岗位/角色 ----------
const approveBox = reactive({ visible: false, row: null, saving: false, department: null, position: null, role: 'EMPLOYEE' })
const departments = ref([])
const positions = ref([])

async function ensureOrgOptions() {
  if (!departments.value.length) {
    try { const r = await orgApi.departments({ page_size: 100 }); departments.value = Array.isArray(r) ? r : (r.results || []) } catch (e) {}
    try { const r = await orgApi.positions({ page_size: 200 }); positions.value = Array.isArray(r) ? r : (r.results || []) } catch (e) {}
  }
}

async function openApprove(row) {
  approveBox.row = row
  approveBox.department = row.proposed_department || null
  approveBox.position = row.proposed_position || null
  approveBox.role = 'EMPLOYEE'
  approveBox.visible = true
  await ensureOrgOptions()
}

async function confirmApprove() {
  if (!approveBox.department) return ElMessage.warning('请选择入职部门（决定员工登录后能用哪些功能）')
  approveBox.saving = true
  try {
    const r = await orgApi.approveEntry(approveBox.row.id, {
      department: approveBox.department,
      position: approveBox.position || null,
      role: approveBox.role,
    })
    approveBox.visible = false
    const deptName = (departments.value.find(d => d.id === approveBox.department) || {}).name || ''
    const username = r?.username || ''
    if (username && r?.password_from === 'one_time' && r?.one_time_password) {
      ElMessageBox.alert(
        `员工「${approveBox.row.applicant_name}」账号已创建：<br/>登录账号：<b>${username}</b><br/>一次性初始密码：<b>${r.one_time_password}</b><br/>已归入「${deptName}」，请当面告知密码并提醒首次登录后修改。`,
        '账号创建成功',
        { dangerouslyUseHTMLString: true, confirmButtonText: '知道了' }
      )
    } else if (username) {
      ElMessageBox.alert(
        `员工「${approveBox.row.applicant_name}」账号已创建：<br/>登录账号：<b>${username}</b><br/>已归入「${deptName}」，密码为其申请时自设，直接登录即可。`,
        '账号创建成功',
        { dangerouslyUseHTMLString: true, confirmButtonText: '知道了' }
      )
    } else {
      ElMessage.success('已通过，员工账号已创建')
    }
    loadData()
  } catch (e) {} finally { approveBox.saving = false }
}

async function reject(row) {
  const { value } = await ElMessageBox.prompt('填写拒绝原因', '拒绝申请', { inputType: 'textarea', inputPlaceholder: '如：资料不符 / 暂不录用' }).catch(() => ({ value: null }))
  if (value === null) return
  try {
    await orgApi.rejectEntry(row.id, { reject_reason: value || '' })
    ElMessage.success('已拒绝')
    loadData()
  } catch (e) {}
}

// ---------- 修改申请（仅待审核状态） ----------
const editBox = reactive({
  visible: false, row: null, saving: false,
  applicant_name: '', phone: '', department: null, position: null, expected_salary: 0, remark: '',
})

async function openEdit(row) {
  editBox.row = row
  editBox.applicant_name = row.applicant_name || ''
  editBox.phone = row.phone || ''
  editBox.department = row.proposed_department || null
  editBox.position = row.proposed_position || null
  editBox.expected_salary = Number(row.expected_salary || 0)
  editBox.remark = row.remark || ''
  editBox.visible = true
  await ensureOrgOptions()
}

async function confirmEdit() {
  if (!editBox.applicant_name.trim()) return ElMessage.warning('申请人姓名不能为空')
  editBox.saving = true
  try {
    await orgApi.updateEntry(editBox.row.id, {
      applicant_name: editBox.applicant_name.trim(),
      phone: editBox.phone || '',
      proposed_department: editBox.department,
      proposed_position: editBox.position,
      expected_salary: editBox.expected_salary || 0,
      remark: editBox.remark || '',
    })
    ElMessage.success('已保存修改')
    editBox.visible = false
    loadData()
  } catch (e) {} finally { editBox.saving = false }
}

// ---------- 删除申请（待审核/已拒绝；已通过的已建号不可删） ----------
async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除「${row.applicant_name}」的入职申请？删除后不可恢复。`,
      '删除申请', { type: 'warning', confirmButtonText: '确认删除' })
  } catch (e) { return }
  try {
    await orgApi.deleteEntry(row.id)
    ElMessage.success('已删除')
    loadData()
  } catch (e) {}
}

onMounted(loadData)
</script>

<style scoped>
.entry-review { padding: 4px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.auto-stats {
  display: flex; align-items: center; gap: 16px;
  margin-top: 10px; padding: 8px 12px;
  background: #f5f7fa; border-radius: 8px; font-size: 13px; color: #606266;
}
.auto-stats .stat-item b { color: #303133; }
.auto-stats .stat-item.warn b { color: #e6a23c; }
.auto-stats .stat-item.ok b { color: #67c23a; }
.auto-stats .stat-item.danger b { color: #f56c6c; }
.muted { color: #909399; }
</style>
