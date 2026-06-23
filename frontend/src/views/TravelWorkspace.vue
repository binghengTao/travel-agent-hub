<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page domain-page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">Travel Planning Workspace</p>
        <h1>{{ text.workspace.travel.title }}</h1>
      </div>
      <el-tag type="success">Planner / Optimizer / Toolkit</el-tag>
    </div>
    <p class="domain-desc">{{ text.workspace.travel.desc }}</p>
    <el-tabs v-model="active" class="domain-tabs">
      <el-tab-pane :label="text.workspace.travel.plannerTab" name="planner">
        <div class="embedded-page"><TripPlanner /></div>
      </el-tab-pane>
      <el-tab-pane :label="text.workspace.travel.optimizerTab" name="optimizer">
        <div class="embedded-page"><TravelOptimizer /></div>
      </el-tab-pane>
      <el-tab-pane :label="text.workspace.travel.toolkitTab" name="toolkit">
        <div class="embedded-page"><TravelToolkit /></div>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { ref } from 'vue'
import TripPlanner from './TripPlanner.vue'
import TravelOptimizer from './TravelOptimizer.vue'
import TravelToolkit from './TravelToolkit.vue'
import { zhCN as text } from '../i18n/zhCN'

const active = ref('planner')
</script>
