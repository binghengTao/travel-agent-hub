<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <div v-if="sources.length" class="source-list">
    <div v-for="source in sources" :key="source.chunk_id" class="source-item">
      <strong>
        {{ source.source }}
        <span v-if="source.page">{{ text.common.page.replace('{page}', String(source.page)) }}</span>
      </strong>
      <small v-if="source.score !== undefined">{{ text.common.score }}: {{ source.score.toFixed(3) }}</small>
      <p>{{ source.preview }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import type { Source } from '../api'
import { zhCN as text } from '../i18n/zhCN'

defineProps<{ sources: Source[] }>()
</script>
