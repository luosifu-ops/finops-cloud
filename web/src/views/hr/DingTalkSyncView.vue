<template>
  <div class="dingtalk-page">
    <el-row :gutter="16">
      <!-- 配置状态 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header><span>钉钉集成状态</span></template>
          <div class="status-body">
            <template v-if="loading">
              <el-skeleton :rows="3" animated />
            </template>
            <template v-else>
              <div class="status-item">
                <span class="dot" :class="st.configured ? 'ok' : 'off'"></span>
                {{ st.configured ? '已配置，可以同步' : '未配置凭证' }}
              </div>
              <div class="status-item muted" v-if="st.configured">
                AppKey：{{ st.app_key_masked }}
              </div>
              <el-alert v-if="!st.configured" type="warning" :closable="false" show-icon style="margin-top:12px"
                title="尚未配置钉钉凭证" description="请先在钉钉管理后台创建企业内部应用，将 AppKey / AppSecret 交给管理员配置到服务器后，即可一键同步通讯录。" />
              <el-button v-if="st.configured" type="primary" style="margin-top:16px;width:100%"
                :loading="syncing" @click="doSync(false)">一键同步通讯录</el-button>
              <el-button v-if="st.configured" style="margin-top:8px;width:100%"
                :loading="dryRunning" @click="doSync(true)">预演（不写入数据）</el-button>
            </template>
          </div>
        </el-card>
      </el-col>

      <!-- 同步结果 -->
      <el-col :span="16">
        <el-card shadow="never">
          <template #header><span>同步结果</span></template>
          <template v-if="!result">
            <el-empty description="尚未执行同步" :image-size="80" />
          </template>
          <template v-else>
            <el-row :gutter="12">
              <el-col :span="6" v-for="c in resultCards" :key="c.label">
                <div class="stat">
                  <div class="num">{{ c.value }}</div>
                  <div class="label">{{ c.label }}</div>
                </div>
              </el-col>
            </el-row>
            <el-alert v-if="result.errors && result.errors.length" type="error" :closable="false"
              show-icon style="margin-top:14px" title="部分条目被跳过">
              <div v-for="(e, i) in result.errors" :key="i" class="err-line">· {{ e }}</div>
            </el-alert>
            <el-alert type="info" :closable="false" show-icon style="margin-top:14px"
              title="同步规则"
              description="部门按钉钉树同步（编码 DT+钉钉部门ID，不占用业务码）；老员工按手机号匹配只补部门不动角色；新员工账号默认不可登录，需管理员在员工档案重置密码后启用。" />
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { integrationApi } from '@/api'

const loading = ref(true)
const syncing = ref(false)
const dryRunning = ref(false)
const st = ref({ configured: false, app_key_masked: '' })
const result = ref(null)

const resultCards = computed(() => result.value ? [
  { label: '新建部门', value: result.value.depts_created ?? 0 },
  { label: '更新部门', value: result.value.depts_updated ?? 0 },
  { label: '新建员工', value: result.value.users_created ?? 0 },
  { label: '匹配老员工', value: result.value.users_matched ?? 0 },
] : [])

async function loadStatus() {
  loading.value = true
  try {
    const d = await integrationApi.dingtalkStatus()
    st.value = d.data || d || { configured: false }
  } catch (e) {} finally { loading.value = false }
}

async function doSync(dry) {
  if (dry) dryRunning.value = true
  else {
    const { ElMessageBox } = await import('element-plus')
    try { await ElMessageBox.confirm('将从钉钉拉取部门与成员并写入系统组织架构（老员工按手机号匹配）。继续？', '钉钉同步', { type: 'warning' }) }
    catch { return }
    syncing.value = true
  }
  try {
    const d = await integrationApi.dingtalkSync({ dry_run: dry })
    result.value = d.data || d
    ElMessage.success(dry ? '预演完成' : '同步完成')
  } catch (e) {} finally {
    syncing.value = false; dryRunning.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.dingtalk-page { padding: 8px 4px; }
.status-body { padding: 4px 0; }
.status-item { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.status-item.muted { font-weight: 400; font-size: 13px; color: var(--text-sub, #909399); }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot.ok { background: #12865a; }
.dot.off { background: #c07a12; }
.stat { text-align: center; padding: 14px 0; background: var(--bg-sub, #f7f8fa); border-radius: 10px; }
.stat .num { font-size: 26px; font-weight: 800; }
.stat .label { font-size: 12px; color: var(--text-sub, #909399); margin-top: 4px; }
.err-line { font-size: 12px; line-height: 1.8; }
</style>
