<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page domain-page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">Realtime Tools & Multimodal Creation</p>
        <h1>{{ text.workspace.creation.title }}</h1>
      </div>
      <el-tag type="warning">Tool / Vision / TTS</el-tag>
    </div>
    <p class="domain-desc">{{ text.workspace.creation.desc }}</p>
    <el-tabs v-model="active" class="domain-tabs">
      <el-tab-pane :label="text.workspace.creation.toolsTab" name="tools">
        <div class="embedded-page"><RealtimeTools /></div>
      </el-tab-pane>
      <el-tab-pane :label="text.workspace.creation.copyTab" name="copy">
        <div class="embedded-page"><Copywriter /></div>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { ref } from 'vue'
import RealtimeTools from './RealtimeTools.vue'
import Copywriter from './Copywriter.vue'
import { zhCN as text } from '../i18n/zhCN'

const active = ref('tools')
</script>
