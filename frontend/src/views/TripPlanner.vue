<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.trip.eyebrow }}</p>
        <h1>{{ text.trip.title }}</h1>
      </div>
      <el-tag type="success">{{ text.trip.tag }}</el-tag>
    </div>
    <div class="workspace">
      <el-form class="panel" label-position="top">
        <el-form-item :label="text.trip.departure"><el-input v-model="form.departure" /></el-form-item>
        <el-form-item :label="text.trip.destination"><el-input v-model="form.destination" /></el-form-item>
        <el-form-item :label="text.trip.days"><el-input-number v-model="form.days" :min="1" :max="30" /></el-form-item>
        <el-form-item :label="text.trip.style">
          <el-segmented v-model="form.style" :options="styleOptions" />
        </el-form-item>
        <el-form-item :label="text.trip.budget"><el-input v-model="form.budget" :placeholder="text.trip.budgetPlaceholder" /></el-form-item>
        <el-form-item :label="text.trip.travelers"><el-input v-model="form.people" /></el-form-item>
        <el-form-item :label="text.trip.preferences"><el-input v-model="form.preferences" type="textarea" :rows="4" /></el-form-item>
        <el-form-item :label="text.trip.useWebSearch">
          <el-switch v-model="form.useWebSearch" />
          <p class="hint-text">{{ text.trip.webSearchHint }}</p>
        </el-form-item>
        <div class="toolbar">
          <el-button type="primary" :icon="Promotion" :loading="loading" @click="submit">{{ text.trip.generate }}</el-button>
          <el-button :icon="RefreshLeft" @click="clearResult">{{ text.common.clear }}</el-button>
        </div>
      </el-form>
      <div class="panel result">
        <el-alert v-if="warnings.length" type="warning" :closable="false" show-icon>
          <template #default>{{ warnings.join('; ') }}</template>
        </el-alert>
        <div>{{ answer || text.trip.empty }}</div>
        <div v-if="webSources.length" class="source-list">
          <h3>{{ text.trip.webSources }}</h3>
          <div v-for="(source, index) in webSources" :key="source.url || index" class="source-item">
            <strong>{{ source.title }}</strong>
            <small>{{ source.source }} <span v-if="source.published_at">| {{ source.published_at }}</span></small>
            <p>{{ source.snippet }}</p>
            <a v-if="source.url" :href="source.url" target="_blank" rel="noreferrer">{{ source.url }}</a>
          </div>
        </div>
        <h3 v-if="ragSources.length">{{ text.trip.ragSources }}</h3>
        <SourceList :sources="ragSources" />
        <h3 v-if="steps.length">{{ text.trip.toolTrace }}</h3>
        <ToolTimeline :items="steps" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { reactive, ref } from 'vue'
import { Promotion, RefreshLeft } from '@element-plus/icons-vue'
import SourceList from '../components/SourceList.vue'
import ToolTimeline from '../components/ToolTimeline.vue'
import { apiPost, streamPost, type Source } from '../api'
import { useSessionStore } from '../stores/session'
import { zhCN as text } from '../i18n/zhCN'

type WebSource = {
  title: string
  url: string
  snippet: string
  source?: string
  published_at?: string
}

type AgentStep = {
  name: string
  status?: string
  summary?: string
  latency_ms?: number
}

const session = useSessionStore()
const loading = ref(false)
const answer = ref('')
const warnings = ref<string[]>([])
const webSources = ref<WebSource[]>([])
const ragSources = ref<Source[]>([])
const steps = ref<AgentStep[]>([])
const styleOptions = [...text.options.style]
const form = reactive({
  departure: text.examples.departureHefei,
  destination: text.examples.destinationXian,
  days: 3,
  style: text.options.style[1],
  budget: text.examples.budget3000,
  people: '2',
  preferences: '',
  useWebSearch: true
})
// 说明：submit 处理用户操作或数据加载，是页面交互链路的关键节点。
async function submit() {
  loading.value = true
  clearResult()
  try {
    if (form.useWebSearch) {
      const data = await apiPost<{
        answer: string
        warnings: string[]
        web_sources: WebSource[]
        sources: Source[]
        steps: AgentStep[]
      }>('/v1/plan/web-enhanced', {
        departure: form.departure,
        destination: form.destination,
        days: form.days,
        style: form.style,
        budget: form.budget,
        people: form.people,
        preferences: form.preferences,
        session_id: session.sessionId,
        use_web_search: true
      })
      answer.value = data.answer
      warnings.value = data.warnings || []
      webSources.value = data.web_sources || []
      ragSources.value = data.sources || []
      steps.value = data.steps || []
    } else {
      await streamPost('/trips/plan/stream', { ...form, session_id: session.sessionId }, (token) => {
        answer.value += token
      })
    }
  } catch (error) {
    answer.value = error instanceof Error ? error.message : text.common.backendError
  } finally {
    loading.value = false
  }
}
// 说明：clearResult 处理用户操作或数据加载，是页面交互链路的关键节点。
function clearResult() {
  answer.value = ''
  warnings.value = []
  webSources.value = []
  ragSources.value = []
  steps.value = []
}
</script>

<style scoped>
.hint-text {
  color: #60737b;
  font-size: 12px;
  line-height: 1.5;
  margin: 8px 0 0;
}

.source-item a {
  color: #287d73;
  word-break: break-all;
}
</style>
