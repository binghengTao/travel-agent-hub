<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <VChart class="metric-chart" :option="option" autoresize />
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, BarChart, GridComponent, TooltipComponent, LegendComponent])

const props = defineProps<{
  type?: 'bar' | 'pie' | 'gauge'
  title?: string
  data: Array<{ name: string; value: number }>
}>()

const option = computed(() => {
  if (props.type === 'pie') {
    return {
      tooltip: { trigger: 'item' },
      legend: { bottom: 0 },
      series: [{ type: 'pie', radius: ['42%', '70%'], center: ['50%', '44%'], data: props.data }]
    }
  }
  if (props.type === 'gauge') {
    return {
      series: [
        {
          type: 'gauge',
          min: 0,
          max: 100,
          progress: { show: true, width: 8 },
          axisLine: { lineStyle: { width: 8 } },
          detail: { formatter: '{value}%', fontSize: 18 },
          data: [{ value: props.data[0]?.value || 0, name: props.data[0]?.name || props.title || '' }]
        }
      ]
    }
  }
  return {
    tooltip: {},
    grid: { left: 28, right: 14, top: 20, bottom: 24 },
    xAxis: { type: 'category', data: props.data.map((item) => item.name), axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#edf2f3' } } },
    series: [{ type: 'bar', data: props.data.map((item) => item.value), itemStyle: { color: '#3aa99e', borderRadius: [5, 5, 0, 0] } }]
  }
})
</script>
