<template>
  <!-- 悬浮按钮 -->
  <div class="ai-fab" @click="open = !open" :class="{ active: open }">
    <span v-if="!open" class="fab-icon">🤖</span>
    <span v-else class="fab-icon">×</span>
    <span class="fab-tip" v-if="!open">AI 经营助手</span>
  </div>

  <!-- 面板 -->
  <transition name="ai-slide">
    <div class="ai-panel" v-if="open">
      <div class="ai-head">
        <div class="ai-title">
          <span class="ai-dot"></span>
          经营助手 · AI Copilot
          <span v-if="isDemo" class="demo-tag" title="未配置 LLM API Key，调用的是本地模板">演示模式</span>
        </div>
        <el-button text size="small" @click="open = false">收起</el-button>
      </div>

      <div class="ai-body" ref="bodyRef">
        <div v-for="(m, i) in messages" :key="i" class="ai-msg" :class="m.role">
          <div class="ai-avatar">{{ m.role === 'ai' ? '🤖' : '我' }}</div>
          <div class="ai-bubble" v-html="m.html || escapeHtml(m.text)"></div>
        </div>
        <div v-if="thinking" class="ai-msg ai">
          <div class="ai-avatar">🤖</div>
          <div class="ai-bubble"><span class="dot-typing"></span>正在分析经营数据…</div>
        </div>
      </div>

      <div class="ai-presets">
        <div class="preset" v-for="p in presets" :key="p.key" @click="ask(p)">{{ p.q }}</div>
      </div>

      <div class="ai-input">
        <el-input v-model="input" placeholder="问问经营情况…" size="default"
                  @keyup.enter="sendFree" :disabled="thinking">
          <template #append>
            <el-button :icon="Promotion" @click="sendFree" :loading="thinking">发送</el-button>
          </template>
        </el-input>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import { aiApi } from '@/api'

const open = ref(false)
const thinking = ref(false)
const input = ref('')
const isDemo = ref(false)
const bodyRef = ref()
const messages = ref([
  { role: 'ai', text: '你好，我是财税企管云经营助手。我会基于实时数据回答经营问题，点击下方快捷问题即可。\n未配置 LLM_API_KEY 时显示「演示模式」（本地模板），填入 DeepSeek/Qwen Key 即升级为真 AI。' }
])

const presets = [
  { key: 'overview', q: '📊 本月经营概览' },
  { key: 'completion', q: '🎯 业绩目标完成率' },
  { key: 'expiring', q: '⏰ 哪些客户将到期' },
  { key: 'roi', q: '📣 各渠道投放 ROI' },
  { key: 'approval', q: '✅ 待我审批事项' }
]

const escapeHtml = (s) => (s || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')
const scrollBottom = async () => { await nextTick(); if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight }

async function ask(p) {
  if (thinking.value) return
  messages.value.push({ role: 'user', text: p.q })
  thinking.value = true; await scrollBottom()
  try {
    const r = await aiApi.chat({ mode: p.key, question: p.q })
    const d = r.data || {}
    isDemo.value = !!d.demo
    messages.value.push({ role: 'ai', text: d.answer || '（无回答）' })
  } catch (e) {
    messages.value.push({ role: 'ai', text: '⚠️ 请求失败：' + (e?.response?.data?.detail || e?.message || '网络异常') })
  }
  thinking.value = false
  await scrollBottom()
}

async function sendFree() {
  const q = input.value.trim()
  if (!q || thinking.value) return
  messages.value.push({ role: 'user', text: q })
  input.value = ''
  thinking.value = true; await scrollBottom()
  try {
    const r = await aiApi.chat({ mode: 'free', question: q })
    const d = r.data || {}
    isDemo.value = !!d.demo
    messages.value.push({ role: 'ai', text: d.answer || '（无回答）' })
  } catch (e) {
    messages.value.push({ role: 'ai', text: '⚠️ 请求失败：' + (e?.response?.data?.detail || e?.message || '网络异常') })
  }
  thinking.value = false
  await scrollBottom()
}
</script>

<style scoped>
.ai-fab {
  position: fixed; right: 24px; bottom: 28px; z-index: 2000;
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--brand-gradient); color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 24px rgba(47, 111, 237, .4);
  transition: transform .2s;
}
.ai-fab:hover { transform: scale(1.06); }
.ai-fab.active { background: #fff; color: var(--primary); border: 1px solid var(--primary); }
.fab-icon { font-size: 24px; line-height: 1; }
.fab-tip {
  position: absolute; right: 64px; white-space: nowrap; background: #fff; color: var(--primary);
  font-size: 12px; padding: 5px 10px; border-radius: 16px; box-shadow: var(--shadow-card); font-weight: 600;
}

.ai-panel {
  position: fixed; right: 24px; bottom: 96px; z-index: 2000;
  width: 360px; height: 540px; max-height: 78vh;
  background: #fff; border-radius: 14px; box-shadow: 0 16px 50px rgba(31, 35, 41, .18);
  display: flex; flex-direction: column; overflow: hidden;
  border: 1px solid var(--border-soft);
}
.ai-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 14px; background: var(--brand-gradient); color: #fff;
}
.ai-title { font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
.ai-dot { width: 8px; height: 8px; border-radius: 50%; background: #5fd0a0; box-shadow: 0 0 0 3px rgba(95,208,160,.3); }
.demo-tag {
  font-size: 11px; font-weight: 500; padding: 2px 8px; border-radius: 10px;
  background: rgba(255, 255, 255, .22); color: #fff;
  border: 1px solid rgba(255, 255, 255, .35);
}
.ai-head :deep(.el-button) { color: #fff; }

.ai-body { flex: 1; overflow-y: auto; padding: 14px; background: #fafbfc; }
.ai-msg { display: flex; gap: 8px; margin-bottom: 12px; align-items: flex-start; }
.ai-msg.user { flex-direction: row-reverse; }
.ai-avatar {
  width: 30px; height: 30px; border-radius: 50%; flex: none; font-size: 13px;
  display: flex; align-items: center; justify-content: center;
  background: var(--primary); color: #fff;
}
.ai-msg.user .ai-avatar { background: #c9cdd4; color: #fff; }
.ai-bubble {
  max-width: 78%; padding: 9px 12px; border-radius: 12px; font-size: 13px; line-height: 1.7;
  background: #fff; border: 1px solid var(--border-soft); white-space: pre-wrap; word-break: break-word;
}
.ai-msg.user .ai-bubble { background: var(--primary); color: #fff; border: none; }
.dot-typing { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--text-sub); animation: blink 1s infinite; }
@keyframes blink { 0%,100% { opacity: .2 } 50% { opacity: 1 } }

.ai-presets { padding: 8px 12px 4px; display: flex; flex-wrap: wrap; gap: 6px; border-top: 1px solid var(--border-soft); }
.preset {
  font-size: 12px; padding: 5px 10px; border-radius: 14px; cursor: pointer;
  background: var(--primary-50); color: var(--primary); border: 1px solid var(--primary-100);
  transition: background .15s;
}
.preset:hover { background: var(--primary-100); }

.ai-input { padding: 8px 12px 12px; }
.ai-input :deep(.el-input-group__append) .el-button { background: var(--primary); border-color: var(--primary); color: #fff; }

.ai-slide-enter-active, .ai-slide-leave-active { transition: opacity .2s, transform .2s; }
.ai-slide-enter-from, .ai-slide-leave-to { opacity: 0; transform: translateY(12px); }
</style>