<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <h1>Agent 执行轨迹</h1>
      <el-button @click="$router.back()">返回</el-button>
    </div>
    <div v-if="loading" class="panel" style="text-align:center;padding:48px">
      <p>加载中...</p>
    </div>
    <div v-else-if="error" class="panel" style="text-align:center;padding:48px">
      <p>{{ error }}</p>
    </div>
    <div v-else class="workspace">
      <div class="panel">
        <h3 style="margin-top:0">意图识别</h3>
        <pre>{{ JSON.stringify(run?.intent, null, 2) }}</pre>
        <h3>最终回答</h3>
        <div class="result" style="min-height:auto;padding:16px">{{ run?.answer }}</div>
      </div>
      <div>
        <div class="panel" style="margin-bottom:16px">
          <h3 style="margin-top:0">工具调用</h3>
          <ToolTimeline v-if="run?.tool_calls?.length" :items="run.tool_calls" />
          <p v-else style="color:var(--color-text-secondary)">无工具调用</p>
        </div>
        <div class="panel" style="margin-bottom:16px">
          <h3 style="margin-top:0">引用来源</h3>
          <SourceList v-if="run?.sources?.length" :sources="run.sources" />
          <p v-else style="color:var(--color-text-secondary)">无引用来源</p>
        </div>
        <div class="panel" v-if="planItems.length">
          <h3 style="margin-top:0">旅行计划</h3>
          <PlanTimeline :items="planItems" />
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet } from '../api'
import ToolTimeline from '../components/ToolTimeline.vue'
import SourceList from '../components/SourceList.vue'
import PlanTimeline from '../components/PlanTimeline.vue'

const route = useRoute()
const run = ref<any>(null)
const loading = ref(true)
const error = ref('')

const planItems = computed(() => {
  const plan = run.value?.plan
  if (!plan?.days) return []
  const items: Array<{ time: string; place: string; activity: string }> = []
  for (const day of plan.days) {
    for (const item of day.items || []) {
      items.push({
        time: item.time || '',
        place: item.place || '',
        activity: item.activity || ''
      })
    }
  }
  return items
})

onMounted(async () => {
  try {
    run.value = await apiGet(`/v1/agent/runs/${route.params.runId}`)
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
})
</script>
