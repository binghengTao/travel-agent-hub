<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <h1>会话历史</h1>
      <div class="toolbar">
        <el-input v-model="sessionId" placeholder="输入会话 ID" style="width:280px" clearable />
        <el-button type="primary" @click="loadHistory">查询</el-button>
      </div>
    </div>

    <div v-if="loading" class="panel" style="text-align:center;padding:48px">
      <p>加载中...</p>
    </div>
    <div v-else-if="messages.length === 0" class="panel" style="text-align:center;padding:48px">
      <p style="color:var(--color-text-secondary)">输入会话 ID 查看历史消息</p>
    </div>
    <div v-else class="chat-history">
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        :class="['chat-bubble', msg.role === 'user' ? 'chat-bubble--user' : 'chat-bubble--assistant']"
      >
        <div class="chat-bubble__role">{{ msg.role === 'user' ? '你' : '旅行助手' }}</div>
        <div class="chat-bubble__content">{{ typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content) }}</div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { ref } from 'vue'
import { apiGet } from '../api'

const sessionId = ref('')
const messages = ref<any[]>([])
const loading = ref(false)
// 说明：loadHistory 处理用户操作或数据加载，是页面交互链路的关键节点。
async function loadHistory() {
  if (!sessionId.value) return
  loading.value = true
  try {
    const data = await apiGet<any>(`/v1/history/${sessionId.value}`)
    messages.value = data.messages || data || []
  } catch (e: any) {
    messages.value = []
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.chat-history {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 800px;
}
.chat-bubble {
  max-width: 70%;
  padding: 14px 18px;
  border-radius: 18px;
  line-height: 1.6;
}
.chat-bubble--user {
  align-self: flex-end;
  background: var(--color-accent);
  color: #fff;
  border-bottom-right-radius: 6px;
}
.chat-bubble--assistant {
  align-self: flex-start;
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: var(--shadow-card);
  border-bottom-left-radius: 6px;
}
.chat-bubble__role {
  font-size: 11px;
  font-weight: 600;
  opacity: 0.7;
  margin-bottom: 6px;
}
.chat-bubble__content {
  font-size: 14px;
  white-space: pre-wrap;
}
</style>
