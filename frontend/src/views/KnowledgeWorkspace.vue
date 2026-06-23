<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page domain-page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">Agentic RAG Knowledge Workspace</p>
        <h1>{{ text.workspace.knowledge.title }}</h1>
      </div>
      <el-tag>Chroma / BM25 / Rerank</el-tag>
    </div>
    <p class="domain-desc">{{ text.workspace.knowledge.desc }}</p>
    <el-tabs v-model="active" class="domain-tabs">
      <el-tab-pane :label="text.workspace.knowledge.qaTab" name="qa">
        <div class="embedded-page"><KnowledgeBase /></div>
      </el-tab-pane>
      <el-tab-pane :label="text.workspace.knowledge.evalTab" name="eval">
        <div class="embedded-page"><RagEvaluation /></div>
      </el-tab-pane>
      <el-tab-pane label="我的文件" name="user">
        <div class="embedded-page"><UserKnowledge /></div>
      </el-tab-pane>
      <el-tab-pane :label="text.workspace.knowledge.governanceTab" name="governance">
        <div class="embedded-page"><KnowledgeGovernance /></div>
      </el-tab-pane>
      <el-tab-pane :label="text.workspace.knowledge.adminTab" name="admin">
        <div class="embedded-page"><KnowledgeAdmin /></div>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { ref } from 'vue'
import KnowledgeBase from './KnowledgeBase.vue'
import RagEvaluation from './RagEvaluation.vue'
import UserKnowledge from './UserKnowledge.vue'
import KnowledgeGovernance from './KnowledgeGovernance.vue'
import KnowledgeAdmin from './KnowledgeAdmin.vue'
import { zhCN as text } from '../i18n/zhCN'

const active = ref('qa')
</script>
