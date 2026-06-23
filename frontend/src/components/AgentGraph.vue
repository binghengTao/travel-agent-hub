<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <div class="agent-graph">
    <VueFlow
      :nodes="nodes"
      :edges="edges"
      :fit-view-on-init="true"
      :nodes-draggable="false"
      :pan-on-drag="false"
      :zoom-on-scroll="false"
      :min-zoom="0.72"
      :max-zoom="1.08"
    >
      <Background pattern-color="#cbd9dc" :gap="20" />
      <Controls position="bottom-right" />
      <template #node-default="{ data, label }">
        <div class="agent-node-inner">
          <div class="agent-node-title">{{ label }}</div>
          <div class="agent-node-summary">{{ data.summary || text.graph.waiting }}</div>
          <span class="agent-node-status">{{ translateStatus(data.status) }}</span>
        </div>
      </template>
    </VueFlow>
  </div>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { computed } from 'vue'
import { VueFlow, type Edge, type Node } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { zhCN as text } from '../i18n/zhCN'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

type Step = { name: string; status?: string; summary?: string }

const props = defineProps<{ steps: Step[] }>()

const fallback: Step[] = [
  { name: 'RouterAgent', status: 'pending', summary: text.graph.router },
  { name: 'ToolAgent', status: 'pending', summary: text.graph.tool },
  { name: 'RAGAgent', status: 'pending', summary: text.graph.rag },
  { name: 'PlannerAgent', status: 'pending', summary: text.graph.planner },
  { name: 'AnswerComposer', status: 'pending', summary: text.graph.composer },
  { name: 'CriticAgent', status: 'pending', summary: text.graph.critic }
]
// 说明：translateStatus 处理用户操作或数据加载，是页面交互链路的关键节点。
function translateStatus(status?: string) {
  if (status === 'success') return text.common.statusSuccess
  if (status === 'warning') return text.common.statusWarning
  return text.common.statusPending
}

const nodes = computed<Node[]>(() => {
  const source = props.steps.length ? props.steps : fallback
  return source.map((step, index) => ({
    id: `${index}-${step.name}`,
    label: step.name.replace('.weather_tool', '').replace('.amap_poi_tool', '').replace('.web_search_tool', ''),
    position: { x: (index % 3) * 245, y: Math.floor(index / 3) * 138 },
    class: `agent-node agent-node-${step.status || 'pending'}`,
    style: { width: '190px' },
    data: { summary: step.summary || '', status: step.status || 'pending' }
  }))
})

const edges = computed<Edge[]>(() =>
  nodes.value.slice(0, -1).map((node, index) => ({
    id: `e-${node.id}-${nodes.value[index + 1].id}`,
    source: node.id,
    target: nodes.value[index + 1].id,
    animated: true,
    class: 'agent-edge'
  }))
)
</script>
