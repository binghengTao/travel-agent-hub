<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page domain-page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">LangGraph Agent Workspace</p>
        <h1>{{ text.workspace.agent.title }}</h1>
      </div>
      <el-tag type="success">Router / Memory / Critic</el-tag>
    </div>
    <p class="domain-desc">{{ text.workspace.agent.desc }}</p>
    <el-tabs v-model="active" class="domain-tabs">
      <el-tab-pane :label="text.workspace.agent.chatTab" name="chat">
        <div class="embedded-page"><AgentChat /></div>
      </el-tab-pane>
      <el-tab-pane :label="text.workspace.agent.profileTab" name="profile">
        <div class="embedded-page"><Preferences /></div>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { ref } from 'vue'
import AgentChat from './AgentChat.vue'
import Preferences from './Preferences.vue'
import { zhCN as text } from '../i18n/zhCN'

const active = ref('chat')
</script>
