<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <el-timeline v-if="items.length">
    <el-timeline-item v-for="(item, index) in items" :key="index" :timestamp="item.name" :type="item.status === 'warning' ? 'warning' : 'primary'">
      <div class="timeline-title">
        <el-tag size="small" :type="item.status === 'warning' ? 'warning' : 'success'">{{ statusText(item.status) }}</el-tag>
        <span v-if="item.latency_ms !== undefined">{{ item.latency_ms }} ms</span>
      </div>
      <pre>{{ item.summary || item.result || item.error }}</pre>
    </el-timeline-item>
  </el-timeline>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { zhCN as text } from '../i18n/zhCN'

defineProps<{ items: Array<{ name: string; status?: string; summary?: string; latency_ms?: number; result?: unknown; error?: string }> }>()
// 说明：statusText 处理用户操作或数据加载，是页面交互链路的关键节点。
function statusText(status?: string) {
  if (status === 'warning') return text.common.statusWarning
  if (status === 'pending') return text.common.statusPending
  return text.common.statusSuccess
}
</script>
