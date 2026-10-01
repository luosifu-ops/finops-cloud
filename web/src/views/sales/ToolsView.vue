<template>
  <div class="page">
    <h2 class="page-title">外部获客工具</h2>
    <p class="text-muted" style="margin-top:-8px">电销部 · 外部获客工具（点击卡片跳转至对应平台官网）</p>

    <el-row :gutter="14">
      <el-col v-for="t in TOOLS" :key="t.name" :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="tool-card" @click="open(t.url)">
          <div class="tool-icon">{{ t.icon }}</div>
          <div class="tool-name">{{ t.name }}</div>
          <div class="tool-desc">{{ t.desc }}</div>
          <el-button type="primary" round size="small" class="tool-btn">打开</el-button>
        </el-card>
      </el-col>
    </el-row>

    <el-alert type="success" :closable="false" style="margin-top:8px">
      已配置正式平台地址（快启 · 探迹），点击卡片即可在新标签页打开。
    </el-alert>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
// 外部获客工具：name/desc/url 集中配置，Boss 可替换为真实合作地址
const TOOLS = [
  { name: '快启', icon: '🚀', desc: '智能外呼 / 客户管理 CRM 获客工具', url: 'https://sales.ukuaiqi.com' },
  { name: '探迹', icon: '📝', desc: '销售线索挖掘与跟进大数据平台', url: 'https://user.tungee.com/home' },
]
const open = (url) => {
  const win = window.open(url, '_blank', 'noopener')
  if (!win) ElMessage.error('浏览器拦截了新窗口，请允许弹出窗口后重试')
}
</script>

<style scoped>
.tool-card { text-align: center; border-radius: 16px; margin-bottom: 14px; cursor: pointer; transition: transform .15s; }
.tool-card:hover { transform: translateY(-3px); }
.tool-icon { font-size: 34px; margin-bottom: 8px; }
.tool-name { font-size: 16px; font-weight: 700; }
.tool-desc { font-size: 12px; color: var(--text-sub); margin: 6px 0 12px; min-height: 34px; }
.tool-btn { width: 80%; }
</style>
