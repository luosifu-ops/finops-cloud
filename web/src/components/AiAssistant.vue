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
/* AI 浮球：深墨蓝 + 金环，与全站品牌语言统一 */
.ai-fab {
  position: fixed; right: 26px; bottom: 30px; z-index: 2000;
  width: 54px; height: 54px; border-radius: 50%;
  background: linear-gradient(150deg, #2b4a8f 0%, #14273f 55%, #0b1a2e 100%);
  color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(200, 164, 77, 0.45);
  box-shadow:
    0 8px 22px -6px rgba(11, 26, 46, 0.55),
    0 0 0 4px rgba(255, 255, 255, 0.9),
    inset 0 1px 0 rgba(255, 255, 255, 0.18);
  transition: transform var(--dur-base) var(--ease-out), box-shadow var(--dur-base) var(--ease-out);
}
.ai-fab:hover {
  transform: translateY(-2px) scale(1.04);
  box-shadow:
    0 14px 30px -8px rgba(11, 26, 46, 0.6),
    0 0 0 4px rgba(255, 255, 255, 0.9),
    0 0 0 5px rgba(200, 164, 77, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.22);
}
.ai-fab.active {
  background: #fff; color: var(--primary);
  border-color: var(--border);
}
.fab-icon { font-size: 22px; line-height: 1; }
.fab-tip {
  position: absolute; right: 64px; white-space: nowrap;
  background: #fff; color: var(--text-main);
  font-size: 11.5px; padding: 6px 11px; border-radius: 20px;
  box-shadow: var(--shadow-pop); font-weight: 600;
  border: 1px solid var(--border-soft);
  letter-spacing: 0.02em;
}

.ai-panel {
  position: fixed; right: 26px; bottom: 98px; z-index: 2000;
  width: 366px; height: 546px; max-height: 78vh;
  background: #fff; border-radius: var(--radius-lg);
  box-shadow: var(--shadow-pop);
  display: flex; flex-direction: column; overflow: hidden;
  border: 1px solid var(--border-soft);
}
.ai-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 13px 16px;
  background:
    radial-gradient(280px 120px at 88% -40%, rgba(74, 111, 240, 0.55) 0%, rgba(11, 26, 46, 0) 70%),
    linear-gradient(120deg, #16273f 0%, #0b1a2e 100%);
  color: #fff;
  border-bottom: 1px solid rgba(200, 164, 77, 0.25);
}
.ai-title { font-size: 14px; font-weight: 650; display: flex; align-items: center; gap: 8px; letter-spacing: -0.1px; }
.ai-dot {
  width: 7px; height: 7px; border-radius: 50%; background: #3ecf94;
  box-shadow: 0 0 0 3px rgba(62, 207, 148, 0.22);
}
.demo-tag {
  font-size: 10.5px; font-weight: 550; padding: 2px 8px; border-radius: 10px;
  background: rgba(200, 164, 77, 0.18); color: #eddcb0;
  border: 1px solid rgba(200, 164, 77, 0.38);
}
.ai-head :deep(.el-button) { color: rgba(255, 255, 255, 0.85); }

.ai-body { flex: 1; overflow-y: auto; padding: 16px; background: var(--surface-2); }
.ai-msg { display: flex; gap: 9px; margin-bottom: 13px; align-items: flex-start; }
.ai-msg.user { flex-direction: row-reverse; }
.ai-avatar {
  width: 30px; height: 30px; border-radius: 9px; flex: none; font-size: 12px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(145deg, #4a6ff0, #16307f);
  color: #fff;
  box-shadow: 0 2px 8px -3px rgba(42, 79, 212, 0.55);
}
.ai-msg.user .ai-avatar { background: var(--surface-4); color: var(--text-sub); box-shadow: none; }
.ai-bubble {
  max-width: 78%; padding: 10px 13px; border-radius: 12px; font-size: 13px; line-height: 1.72;
  background: #fff; border: 1px solid var(--border-soft);
  white-space: pre-wrap; word-break: break-word;
  box-shadow: var(--shadow-xs);
}
.ai-msg.user .ai-bubble {
  background: linear-gradient(145deg, #2a4fd4, #1d3aa8);
  color: #fff; border: none;
  box-shadow: 0 4px 14px -6px rgba(42, 79, 212, 0.6);
}
.dot-typing { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--text-sub); animation: blink 1s infinite; }
@keyframes blink { 0%,100% { opacity: .2 } 50% { opacity: 1 } }

.ai-presets { padding: 9px 13px 5px; display: flex; flex-wrap: wrap; gap: 6px; border-top: 1px solid var(--border-soft); }
.preset {
  font-size: 11.5px; padding: 5px 10px; border-radius: 14px; cursor: pointer;
  background: var(--primary-50); color: var(--primary-700);
  border: 1px solid var(--primary-100);
  transition: all var(--dur-fast);
  font-weight: 500;
}
.preset:hover { background: var(--primary-100); border-color: var(--primary-200); }

.ai-input { padding: 9px 13px 13px; }
.ai-input :deep(.el-input-group__append) .el-button {
  background: var(--primary); border-color: var(--primary); color: #fff;
}

.ai-slide-enter-active, .ai-slide-leave-active { transition: opacity .2s, transform .2s; }
.ai-slide-enter-from, .ai-slide-leave-to { opacity: 0; transform: translateY(12px); }

@media (max-width: 768px) {
  .ai-fab { right: 16px; bottom: 18px; width: 48px; height: 48px; }
  .fab-icon { font-size: 19px; }
  .fab-tip { display: none; }
  .ai-panel { right: 12px; left: 12px; width: auto; bottom: 76px; height: 66vh; }
}
</style>