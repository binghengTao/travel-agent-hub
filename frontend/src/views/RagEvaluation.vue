<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.ragEval.eyebrow }}</p>
        <h1>{{ text.ragEval.title }}</h1>
      </div>
      <el-tag type="warning">{{ text.ragEval.tag }}</el-tag>
    </div>
    <div class="workspace">
      <div class="panel">
        <el-input v-model="question" type="textarea" :rows="6" :placeholder="text.ragEval.questionPlaceholder" />
        <el-input v-model="expected" :placeholder="text.ragEval.expectedPlaceholder" style="margin-top: 10px" />
        <el-input v-model="cityHint" :placeholder="text.ragEval.cityPlaceholder" style="margin-top: 10px" />
        <div class="toolbar" style="margin-top: 12px">
          <el-button type="primary" :loading="loading" @click="evaluate">{{ text.ragEval.run }}</el-button>
        </div>
      </div>
      <div class="panel result">
        <el-row :gutter="10" v-if="metrics">
          <el-col :span="8"><el-statistic :title="text.ragEval.sourceCount" :value="metrics.source_count" /></el-col>
          <el-col :span="8"><el-statistic :title="text.ragEval.latency" :value="metrics.latency_ms" /></el-col>
          <el-col :span="8"><el-statistic :title="text.ragEval.avgRerank" :value="metrics.avg_rerank_score" :precision="3" /></el-col>
        </el-row>
        <div class="meta-line" v-if="metrics">
          <el-tag :type="metrics.has_sources ? 'success' : 'danger'">{{ metrics.has_sources ? text.ragEval.sourcesOk : text.ragEval.sourcesMissing }}</el-tag>
          <el-tag :type="metrics.has_citation_text ? 'success' : 'warning'">{{ metrics.has_citation_text ? text.ragEval.citationOk : text.ragEval.citationWeak }}</el-tag>
          <el-tag :type="metrics.matched_expected_source ? 'success' : 'warning'">{{ metrics.matched_expected_source ? text.ragEval.expectedHit : text.ragEval.expectedMiss }}</el-tag>
        </div>
        <MetricChart
          v-if="metrics"
          type="bar"
          :data="[
            { name: text.ragEval.sourceCount, value: metrics.source_count },
            { name: text.ragEval.latency, value: Math.round(metrics.latency_ms / 1000) },
            { name: text.ragEval.avgRerank, value: Math.round(metrics.avg_rerank_score * 100) }
          ]"
        />
        <pre>{{ answer || text.ragEval.empty }}</pre>
        <SourceList :sources="sources" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { ref } from 'vue'
import SourceList from '../components/SourceList.vue'
import MetricChart from '../components/MetricChart.vue'
import { apiPost, type Source } from '../api'
import { useSessionStore } from '../stores/session'
import { zhCN as text } from '../i18n/zhCN'

type Metrics = {
  latency_ms: number
  source_count: number
  has_sources: boolean
  has_citation_text: boolean
  matched_expected_source: boolean
  avg_rerank_score: number
}

const session = useSessionStore()
const loading = ref(false)
const question = ref(text.ragEval.defaultQuestion)
const expected = ref(text.ragEval.defaultExpected)
const cityHint = ref('')
const metrics = ref<Metrics | null>(null)
const answer = ref('')
const sources = ref<Source[]>([])
// 说明：evaluate 处理用户操作或数据加载，是页面交互链路的关键节点。
async function evaluate() {
  loading.value = true
  try {
    const data = await apiPost<{ answer: string; metrics: Metrics; sources: Source[] }>('/v1/rag/evaluate', {
      question: question.value,
      expected_source_keyword: expected.value,
      city_hint: cityHint.value || undefined,
      session_id: session.sessionId
    })
    metrics.value = data.metrics
    answer.value = data.answer
    sources.value = data.sources
  } catch (error) {
    answer.value = error instanceof Error ? error.message : text.common.backendError
  } finally {
    loading.value = false
  }
}
</script>
