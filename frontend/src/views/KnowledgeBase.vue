<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.rag.eyebrow }}</p>
        <h1>{{ text.rag.title }}</h1>
      </div>
      <el-tag>Chroma + BM25 + RRF + Rerank</el-tag>
    </div>
    <div class="workspace">
      <div class="panel">
        <el-input v-model="question" type="textarea" :rows="7" :placeholder="text.rag.placeholder" />
        <div class="toolbar" style="margin-top: 12px">
          <el-button type="primary" :icon="Search" :loading="loading" @click="submit">{{ text.rag.ask }}</el-button>
          <el-input v-model="cityHint" :placeholder="text.common.optionalCity" style="max-width: 180px" />
        </div>
        <el-radio-group v-model="scope" style="margin-top: 12px">
          <el-radio-button label="hybrid">混合检索</el-radio-button>
          <el-radio-button label="personal">我的文件</el-radio-button>
          <el-radio-button label="global">公共知识库</el-radio-button>
        </el-radio-group>
      </div>
      <div class="panel result">
        <div>{{ answer || text.rag.empty }}</div>
        <SourceList :sources="sources" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import SourceList from '../components/SourceList.vue'
import { apiPost, type Source } from '../api'
import { useSessionStore } from '../stores/session'
import { zhCN as text } from '../i18n/zhCN'

const session = useSessionStore()
const loading = ref(false)
const question = ref(text.rag.defaultQuestion)
const cityHint = ref('')
const scope = ref<'global' | 'personal' | 'hybrid'>('hybrid')
const answer = ref('')
const sources = ref<Source[]>([])
// 说明：submit 处理用户操作或数据加载，是页面交互链路的关键节点。
async function submit() {
  loading.value = true
  try {
    const data = await apiPost<{ answer: string; sources: Source[] }>('/v1/rag/ask', {
      question: question.value,
      city_hint: cityHint.value || undefined,
      scope: scope.value,
      session_id: session.sessionId
    })
    answer.value = data.answer
    sources.value = data.sources
  } catch (error) {
    answer.value = error instanceof Error ? error.message : text.common.backendError
  } finally {
    loading.value = false
  }
}
</script>
