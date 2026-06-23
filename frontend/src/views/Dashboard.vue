<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page cockpit">
    <div class="hero-band">
      <div>
        <p class="eyebrow">旅行助手</p>
        <h1>{{ text.dashboard.title }}</h1>
        <p>{{ text.dashboard.desc }}</p>
      </div>
      <el-button type="primary" size="large" :icon="Cpu" @click="$router.push('/agent')">{{ text.dashboard.runAgent }}</el-button>
    </div>

    <div class="stat-grid">
      <div class="stat-card">
        <span>{{ text.dashboard.pdfDocs }}</span>
        <strong>{{ health.dataset_files }}</strong>
      </div>
      <div class="stat-card">
        <span>{{ text.dashboard.redisMemory }}</span>
        <strong>{{ health.redis ? text.dashboard.online : text.dashboard.fallback }}</strong>
      </div>
      <div class="stat-card">
        <span>{{ text.dashboard.defaultModel }}</span>
        <strong>{{ models.models.chat }}</strong>
      </div>
      <div class="stat-card">
        <span>{{ text.dashboard.agentRuntime }}</span>
        <strong>LangGraph</strong>
      </div>
    </div>

    <div class="dashboard-grid">
      <div class="panel dashboard-panel">
        <div class="section-head">
          <div>
            <h2>{{ text.dashboard.workflowTitle }}</h2>
            <p>{{ text.dashboard.workflowDesc }}</p>
          </div>
          <el-tag type="success">StateGraph</el-tag>
        </div>
        <AgentGraph :steps="graphSteps" />
      </div>
      <div class="panel dashboard-panel">
        <div class="section-head">
          <div>
            <h2>{{ text.dashboard.metricsTitle }}</h2>
            <p>{{ apiStatus }}</p>
          </div>
          <el-tag>RAG / Tool / Critic</el-tag>
        </div>
        <MetricChart type="bar" :data="chartData" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { onMounted, ref } from 'vue'
import { Cpu } from '@element-plus/icons-vue'
import AgentGraph from '../components/AgentGraph.vue'
import MetricChart from '../components/MetricChart.vue'
import { apiGet } from '../api'
import { zhCN as text } from '../i18n/zhCN'

type Health = { dataset_files: number; redis: boolean }
type Models = { models: Record<string, string> }

const health = ref<Health>({ dataset_files: 126, redis: false })
const models = ref<Models>({ models: { chat: 'qwen3.6-plus' } })
const apiStatus = ref<string>(text.dashboard.demoStatus)
const graphSteps = [
  { name: 'RouterAgent', status: 'success', summary: text.graph.intent },
  { name: 'ToolAgent', status: 'success', summary: text.graph.toolDone },
  { name: 'RAGAgent', status: 'success', summary: text.graph.ragDone },
  { name: 'PlannerAgent', status: 'success', summary: text.graph.plannerDone },
  { name: 'AnswerComposer', status: 'success', summary: text.graph.composerDone },
  { name: 'CriticAgent', status: 'success', summary: text.graph.criticDone }
]
const chartData = ref([
  { name: text.dashboard.chartPdf, value: 126 },
  { name: text.dashboard.chartTools, value: 3 },
  { name: text.dashboard.chartAgents, value: 7 },
  { name: text.dashboard.chartRetries, value: 2 }
])

onMounted(async () => {
  try {
    const [healthData, modelData] = await Promise.all([apiGet<Health>('/v1/health'), apiGet<Models>('/v1/models')])
    health.value = healthData
    models.value = modelData
    chartData.value[0].value = healthData.dataset_files
    apiStatus.value = text.dashboard.liveStatus
  } catch {
    chartData.value[0].value = health.value.dataset_files
  }
})
</script>
