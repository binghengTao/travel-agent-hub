<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.toolkit.eyebrow }}</p>
        <h1>{{ text.toolkit.title }}</h1>
      </div>
      <el-tag>{{ text.toolkit.tag }}</el-tag>
    </div>
    <div class="workspace">
      <div class="panel">
        <el-tabs v-model="tab">
          <el-tab-pane :label="text.toolkit.budgetTab" name="budget">
            <el-form label-position="top">
              <el-form-item :label="text.toolkit.days"><el-input-number v-model="budget.days" :min="1" :max="60" /></el-form-item>
              <el-form-item :label="text.toolkit.travelers"><el-input-number v-model="budget.people" :min="1" :max="50" /></el-form-item>
              <el-form-item :label="text.toolkit.hotel"><el-input-number v-model="budget.hotel_per_night" :min="0" /></el-form-item>
              <el-form-item :label="text.toolkit.food"><el-input-number v-model="budget.food_per_person_day" :min="0" /></el-form-item>
              <el-form-item :label="text.toolkit.transport"><el-input-number v-model="budget.transport_total" :min="0" /></el-form-item>
              <el-form-item :label="text.toolkit.ticket"><el-input-number v-model="budget.ticket_per_person" :min="0" /></el-form-item>
              <el-form-item :label="text.toolkit.misc"><el-input-number v-model="budget.shopping_misc" :min="0" /></el-form-item>
              <el-button type="primary" :loading="loading" @click="runBudget">{{ text.toolkit.calculate }}</el-button>
            </el-form>
          </el-tab-pane>

          <el-tab-pane :label="text.toolkit.exportTab" name="export">
            <el-input v-model="exportForm.title" :placeholder="text.toolkit.titlePlaceholder" />
            <el-radio-group v-model="exportForm.format" style="margin: 10px 0">
              <el-radio-button label="markdown">Markdown</el-radio-button>
              <el-radio-button label="html">HTML</el-radio-button>
            </el-radio-group>
            <el-input v-model="exportForm.content" type="textarea" :rows="8" />
            <el-button type="primary" :loading="loading" style="margin-top: 10px" @click="runExport">{{ text.toolkit.export }}</el-button>
          </el-tab-pane>

          <el-tab-pane :label="text.toolkit.alternativesTab" name="alternatives">
            <el-input v-model="alt.destination" :placeholder="text.toolkit.destinationPlaceholder" />
            <el-input v-model="alt.issue" :placeholder="text.toolkit.issuePlaceholder" style="margin-top: 8px" />
            <el-input v-model="alt.original_plan" type="textarea" :rows="5" style="margin-top: 8px" />
            <el-button type="primary" :loading="loading" style="margin-top: 10px" @click="runAlternatives">{{ text.toolkit.generateAlt }}</el-button>
          </el-tab-pane>

          <el-tab-pane :label="text.toolkit.routeTab" name="route">
            <el-input v-model="route.destination" :placeholder="text.toolkit.cityPlaceholder" />
            <el-select v-model="route.places" multiple filterable allow-create default-first-option style="width: 100%; margin-top: 8px">
              <el-option :label="text.examples.westLake" :value="text.examples.westLake" />
              <el-option :label="text.examples.lingyin" :value="text.examples.lingyin" />
              <el-option :label="text.examples.hefang" :value="text.examples.hefang" />
            </el-select>
            <el-input v-model="route.plan_markdown" type="textarea" :rows="5" :placeholder="text.toolkit.planPlaceholder" style="margin-top: 8px" />
            <el-button type="primary" :loading="loading" style="margin-top: 10px" @click="runRoute">{{ text.toolkit.generateRoute }}</el-button>
          </el-tab-pane>

          <el-tab-pane :label="text.toolkit.groupTab" name="merge">
            <el-input v-model="mergeJson" type="textarea" :rows="12" />
            <el-button type="primary" :loading="loading" style="margin-top: 10px" @click="runMerge">{{ text.toolkit.mergeProfiles }}</el-button>
          </el-tab-pane>
        </el-tabs>
      </div>
      <div class="panel result">
        <pre>{{ output || text.toolkit.empty }}</pre>
        <div v-if="exportUrl" class="meta-line">
          <el-link :href="exportUrl" target="_blank" type="primary">{{ text.common.openExport }}</el-link>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { reactive, ref } from 'vue'
import { apiPost } from '../api'
import { useSessionStore } from '../stores/session'
import { zhCN as text } from '../i18n/zhCN'

const session = useSessionStore()
const tab = ref('budget')
const loading = ref(false)
const output = ref('')
const exportUrl = ref('')

const budget = reactive({
  days: 3,
  people: 2,
  hotel_per_night: 380,
  food_per_person_day: 120,
  transport_total: 500,
  ticket_per_person: 180,
  shopping_misc: 200,
  buffer_rate: 0.1
})

const exportForm = reactive({
  title: text.examples.planTitle,
  content: text.examples.planMarkdown,
  format: 'markdown'
})

const alt = reactive({
  destination: text.examples.destinationHangzhou,
  issue: text.examples.rainIssue,
  original_plan: text.examples.originalPlan
})

const route = reactive({
  destination: text.examples.destinationHangzhou,
  places: [text.examples.westLake, text.examples.lingyin, text.examples.hefang],
  plan_markdown: ''
})

const mergeJson = ref(JSON.stringify({
  profiles: [
    { budget_level: text.options.budget[1], travel_style: text.options.travelStyle[0], favorite_themes: [text.options.themes[0], text.options.themes[2]], disliked_themes: [text.options.disliked[0]], pace: text.options.pace[1] },
    { budget_level: text.options.budget[1], travel_style: text.options.travelStyle[2], favorite_themes: [text.options.themes[1]], disliked_themes: [text.options.disliked[1]], pace: text.options.pace[0] }
  ]
}, null, 2))
// 说明：runBudget 处理用户操作或数据加载，是页面交互链路的关键节点。
async function runBudget() {
  await run('/v1/plan/budget', budget)
}
// 说明：runExport 处理用户操作或数据加载，是页面交互链路的关键节点。
async function runExport() {
  exportUrl.value = ''
  const data = await run('/v1/plan/export', exportForm)
  if (data && typeof data === 'object' && 'output_url' in data) {
    exportUrl.value = data.output_url as string
  }
}
// 说明：runAlternatives 处理用户操作或数据加载，是页面交互链路的关键节点。
async function runAlternatives() {
  await run('/v1/plan/alternatives', { ...alt, session_id: session.sessionId })
}
// 说明：runRoute 处理用户操作或数据加载，是页面交互链路的关键节点。
async function runRoute() {
  await run('/v1/plan/route-nodes', route)
}
// 说明：runMerge 处理用户操作或数据加载，是页面交互链路的关键节点。
async function runMerge() {
  try { await run('/v1/preferences/merge', JSON.parse(mergeJson.value)) }
  catch { output.value = 'JSON 格式错误，请检查输入' }
}
// 说明：run 处理用户操作或数据加载，是页面交互链路的关键节点。
async function run(path: string, body: unknown): Promise<unknown> {
  loading.value = true
  try {
    const data = await apiPost<unknown>(path, body)
    output.value = JSON.stringify(data, null, 2)
    return data
  } catch (error) {
    output.value = error instanceof Error ? error.message : text.common.backendError
    return null
  } finally {
    loading.value = false
  }
}
</script>
