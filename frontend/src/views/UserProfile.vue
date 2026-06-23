<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <h1>个人中心</h1>
    </div>
    <div v-if="loading" class="panel" style="text-align:center;padding:48px">
      <p>加载中...</p>
    </div>
    <div v-else class="profile-grid">
      <div class="panel">
        <h3 style="margin-top:0">账号信息</h3>
        <div class="profile-field">
          <span class="profile-label">用户名</span>
          <strong>{{ user?.username }}</strong>
        </div>
        <div class="profile-field">
          <span class="profile-label">邮箱</span>
          <strong>{{ user?.email || '未设置' }}</strong>
        </div>
        <div class="profile-field">
          <span class="profile-label">用户 ID</span>
          <strong style="font-family:monospace;font-size:13px">{{ user?.user_id || user?.id }}</strong>
        </div>
        <div class="profile-field">
          <span class="profile-label">注册时间</span>
          <strong>{{ user?.created_at || '—' }}</strong>
        </div>
      </div>
      <div class="panel">
        <h3 style="margin-top:0">快捷入口</h3>
        <div class="profile-links">
          <el-button @click="$router.push('/agent')">偏好记忆设置</el-button>
          <el-button @click="$router.push('/sessions')">会话历史</el-button>
          <el-button @click="$router.push('/knowledge')">我的知识库</el-button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { onMounted, ref } from 'vue'
import { apiGet } from '../api'

const user = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await apiGet<any>('/v1/auth/me')
    user.value = data.user || data
  } catch {
    user.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.profile-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  max-width: 800px;
}
@media (max-width: 640px) {
  .profile-grid { grid-template-columns: 1fr; }
}
.profile-field {
  padding: 14px 0;
  border-bottom: 1px solid rgba(0,0,0,0.04);
}
.profile-field:last-child { border-bottom: none; }
.profile-label {
  display: block;
  color: var(--color-text-secondary);
  font-size: 12px;
  margin-bottom: 4px;
}
.profile-links {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
