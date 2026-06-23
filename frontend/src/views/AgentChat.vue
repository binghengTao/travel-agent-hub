<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.agent.eyebrow }}</p>
        <h1>{{ text.agent.title }}</h1>
      </div>
      <el-tag type="success">Router / RAG / Tool / Planner / Critic</el-tag>
    </div>
    <div class="workspace agent-workspace">
      <div class="panel input-panel">
        <el-input v-model="message" type="textarea" :rows="7" :placeholder="text.agent.placeholder" />
        <div class="toolbar" style="margin-top: 12px">
          <el-button type="primary" :icon="Promotion" :loading="loading" @click="submit">{{ text.agent.run }}</el-button>
          <el-button :icon="RefreshLeft" @click="clear">{{ text.common.clear }}</el-button>
        </div>
        <div v-if="runId" class="meta-line">
          <el-tag>{{ runId }}</el-tag>
          <el-tag v-if="graphEngine" type="success">{{ graphEngine }}</el-tag>
          <el-tag v-if="intent" type="warning">{{ intent }}</el-tag>
          <el-tag v-if="destination" type="info">{{ destination }}</el-tag>
          <el-tag v-if="retryCount" type="danger">retry {{ retryCount }}</el-tag>
        </div>
      </div>
      <div class="panel graph-panel">
        <div class="section-head">
          <div>
            <h2>{{ text.agent.graphTitle }}</h2>
            <p>{{ text.agent.graphDesc }}</p>
          </div>
        </div>
        <AgentGraph :steps="steps" />
      </div>
      <div class="panel result">
        <div>{{ answer || text.agent.empty }}</div>
        <h3 v-if="steps.length">{{ text.common.executionTrace }}</h3>
        <ToolTimeline :items="steps" />
        <h3 v-if="toolCalls.length">{{ text.common.toolCalls }}</h3>
        <ToolTimeline :items="toolCalls" />
        <h3 v-if="sources.length">{{ text.common.sources }}</h3>
        <SourceList :sources="sources" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { ref } from 'vue'
import { Promotion, RefreshLeft } from '@element-plus/icons-vue'
import SourceList from '../components/SourceList.vue'
import ToolTimeline from '../components/ToolTimeline.vue'
import AgentGraph from '../components/AgentGraph.vue'
import { apiPost, type Source } from '../api'
import { useSessionStore } from '../stores/session'
import { zhCN as text } from '../i18n/zhCN'

type ToolCall = { name: string; result?: unknown; error?: string; status?: string; summary?: string; latency_ms?: number }
type AgentStep = { name: string; status?: string; summary?: string; latency_ms?: number }
type AgentResponse = {
  run_id: string
  answer: string
  intent?: string
  destination?: string
  graph_engine?: string
  retry_count?: number
  tool_calls: ToolCall[]
  steps: AgentStep[]
  sources: Source[]
}

const session = useSessionStore()
const loading = ref(false)
const message = ref(text.agent.defaultQuestion)
const answer = ref('')
const runId = ref('')
const intent = ref('')
const destination = ref('')
const graphEngine = ref('')
const retryCount = ref(0)
const toolCalls = ref<ToolCall[]>([])
const steps = ref<AgentStep[]>([])
const sources = ref<Source[]>([])
// 说明：submit 处理用户操作或数据加载，是页面交互链路的关键节点。
async function submit() {
  loading.value = true
  try {
    // AgentChat 只提交自然语言和 session_id，用户身份由 api.ts 自动带上的 JWT 负责。
    const data = await apiPost<AgentResponse>('/v1/agent/chat', {
      message: message.value,
      session_id: session.sessionId
    })
    // 后端返回的 run_id、steps、tool_calls、sources 会同时驱动图谱、时间线和引用面板。
    runId.value = data.run_id
    answer.value = data.answer
    intent.value = data.intent || ''
    destination.value = data.destination || ''
    graphEngine.value = data.graph_engine || ''
    retryCount.value = data.retry_count || 0
    toolCalls.value = data.tool_calls || []
    steps.value = data.steps || []
    sources.value = data.sources || []
  } catch (error) {
    // 接口失败时直接把中文错误态写入回答区，避免页面空白。
    answer.value = error instanceof Error ? error.message : text.agent.error
  } finally {
    loading.value = false
  }
}
// 说明：clear 处理用户操作或数据加载，是页面交互链路的关键节点。
function clear() {
  answer.value = ''
  runId.value = ''
  intent.value = ''
  destination.value = ''
  graphEngine.value = ''
  retryCount.value = 0
  toolCalls.value = []
  steps.value = []
  sources.value = []
}
</script>
