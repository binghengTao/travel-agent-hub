<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.tools.eyebrow }}</p>
        <h1>{{ text.tools.title }}</h1>
      </div>
      <el-tag type="warning">{{ text.tools.tag }}</el-tag>
    </div>
    <div class="workspace">
      <div class="panel">
        <el-tabs v-model="tab">
          <el-tab-pane :label="text.tools.weather" name="weather">
            <el-input v-model="weather.city" :placeholder="text.tools.cityPlaceholder" />
            <el-slider v-model="weather.days" :min="1" :max="7" />
            <el-button type="primary" :icon="Sunny" :loading="loading" @click="runWeather">{{ text.tools.checkWeather }}</el-button>
          </el-tab-pane>
          <el-tab-pane :label="text.tools.nearby" name="nearby">
            <el-input v-model="nearby.location" :placeholder="text.tools.locationPlaceholder" />
            <el-input v-model="nearby.city" :placeholder="text.tools.cityPlaceholder" style="margin-top: 8px" />
            <el-input v-model="nearby.keyword" :placeholder="text.tools.keywordPlaceholder" style="margin-top: 8px" />
            <el-button type="primary" :icon="Location" :loading="loading" style="margin-top: 10px" @click="runNearby">{{ text.tools.searchNearby }}</el-button>
          </el-tab-pane>
          <el-tab-pane :label="text.tools.search" name="search">
            <el-input v-model="query" type="textarea" :rows="5" :placeholder="text.tools.queryPlaceholder" />
            <el-button type="primary" :icon="Search" :loading="loading" style="margin-top: 10px" @click="runSearch">{{ text.tools.webSearch }}</el-button>
          </el-tab-pane>
        </el-tabs>
      </div>
      <div class="panel result">{{ result || text.tools.empty }}</div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { reactive, ref } from 'vue'
import { Location, Search, Sunny } from '@element-plus/icons-vue'
import { apiPost } from '../api'
import { zhCN as text } from '../i18n/zhCN'

const tab = ref('weather')
const loading = ref(false)
const result = ref('')
const query = ref(text.examples.terracotta)
const weather = reactive({ city: text.examples.beijing, days: 3 })
const nearby = reactive({ location: text.examples.sanlitun, city: text.examples.beijing, keyword: text.examples.cafe })
// 说明：runWeather 处理用户操作或数据加载，是页面交互链路的关键节点。
async function runWeather() {
  await run('/v1/tools/weather', weather)
}
// 说明：runNearby 处理用户操作或数据加载，是页面交互链路的关键节点。
async function runNearby() {
  await run('/v1/tools/nearby', nearby)
}
// 说明：runSearch 处理用户操作或数据加载，是页面交互链路的关键节点。
async function runSearch() {
  await run('/v1/tools/web-search', { query: query.value })
}
// 说明：run 处理用户操作或数据加载，是页面交互链路的关键节点。
async function run(path: string, payload: unknown) {
  loading.value = true
  try {
    const data = await apiPost<{ result: string }>(path, payload)
    result.value = data.result
  } catch (error) {
    result.value = error instanceof Error ? error.message : text.common.backendError
  } finally {
    loading.value = false
  }
}
</script>
