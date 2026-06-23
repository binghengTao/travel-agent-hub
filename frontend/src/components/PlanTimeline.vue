<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <div class="plan-timeline">
    <div v-for="(item, index) in items" :key="index" class="plan-stop">
      <div class="plan-time">{{ item.time }}</div>
      <div class="plan-card">
        <strong>{{ item.place }}</strong>
        <p>{{ item.activity }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
defineProps<{ items: Array<{ time: string; place: string; activity: string }> }>()
</script>
