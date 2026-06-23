<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.optimizer.eyebrow }}</p>
        <h1>{{ text.optimizer.title }}</h1>
      </div>
      <el-tag type="success">{{ text.optimizer.tag }}</el-tag>
    </div>
    <div class="workspace">
      <el-form class="panel" label-position="top">
        <el-form-item :label="text.optimizer.userId">
          <el-input :model-value="displayUser" disabled />
        </el-form-item>
        <el-form-item :label="text.optimizer.departure">
          <el-input v-model="form.departure" />
        </el-form-item>
        <el-form-item :label="text.optimizer.destination">
          <el-input v-model="form.destination" />
        </el-form-item>
        <el-form-item :label="text.optimizer.days">
          <el-input-number v-model="form.days" :min="1" :max="15" />
        </el-form-item>
        <el-form-item :label="text.optimizer.budget">
          <el-input v-model="form.budget" />
        </el-form-item>
        <el-form-item :label="text.optimizer.travelers">
          <el-input v-model="form.people" />
        </el-form-item>
        <el-form-item :label="text.optimizer.pace">
          <el-segmented v-model="form.pace" :options="paceOptions" />
        </el-form-item>
        <el-form-item :label="text.optimizer.mustVisit">
          <el-select v-model="form.must_visit" multiple filterable allow-create default-first-option />
        </el-form-item>
        <el-form-item :label="text.optimizer.avoid">
          <el-select v-model="form.avoid" multiple filterable allow-create default-first-option />
        </el-form-item>
        <div class="toolbar">
          <el-button type="primary" :loading="loading" @click="optimize">{{ text.optimizer.optimize }}</el-button>
        </div>
      </el-form>
      <div class="panel result">
        <el-alert v-if="warnings.length" type="warning" :closable="false" show-icon>
          <template #default>{{ warnings.join('; ') }}</template>
        </el-alert>
        <h3 v-if="steps.length">{{ text.optimizer.chain }}</h3>
        <ToolTimeline :items="steps" />
        <PlanTimeline :items="timelineItems" />
        <pre>{{ answer || text.optimizer.empty }}</pre>
        <SourceList :sources="sources" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { computed, reactive, ref } from 'vue'
import SourceList from '../components/SourceList.vue'
import ToolTimeline from '../components/ToolTimeline.vue'
import PlanTimeline from '../components/PlanTimeline.vue'
import { apiPost, type Source } from '../api'
import { useAuthStore } from '../stores/auth'
import { useSessionStore } from '../stores/session'
import { zhCN as text } from '../i18n/zhCN'

type Step = { name: string; status?: string; summary?: string; latency_ms?: number }

const session = useSessionStore()
const auth = useAuthStore()
const displayUser = computed(() => `${auth.user?.username || '当前用户'}（ID: ${auth.user?.id || '-'}）`)
const loading = ref(false)
const answer = ref('')
const warnings = ref<string[]>([])
const steps = ref<Step[]>([])
const sources = ref<Source[]>([])
const paceOptions = [...text.options.pace]
const timelineItems = ref([
  { time: '09:00', place: text.examples.coreArea, activity: text.optimizer.timelineMorning },
  { time: '12:00', place: text.examples.localRestaurant, activity: text.optimizer.timelineLunch },
  { time: '15:00', place: text.examples.backupSpot, activity: text.optimizer.timelineAfternoon }
])
const form = reactive({
  departure: text.examples.departureShanghai,
  destination: text.examples.destinationHangzhou,
  days: 1,
  budget: text.examples.budget500,
  people: '2',
  pace: text.options.pace[1],
  must_visit: [text.examples.westLake],
  avoid: [text.examples.avoidShopping]
})
// 说明：optimize 处理用户操作或数据加载，是页面交互链路的关键节点。
async function optimize() {
  loading.value = true
  try {
    const data = await apiPost<{ answer: string; warnings: string[]; steps: Step[]; sources: Source[] }>('/v1/plan/optimize', {
      ...form,
      session_id: session.sessionId
    })
    answer.value = data.answer
    warnings.value = data.warnings || []
    steps.value = data.steps || []
    sources.value = data.sources || []
  } catch (error) {
    answer.value = error instanceof Error ? error.message : text.common.backendError
  } finally {
    loading.value = false
  }
}
</script>
