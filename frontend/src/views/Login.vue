<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="auth-page">
    <div class="auth-visual">
      <p class="eyebrow subtle">旅行助手</p>
      <h1>AI 智能旅行助手</h1>
      <p>登录后，系统会用 JWT 识别用户，并把对话、偏好、事实记忆和 Agent 执行摘要隔离保存。</p>
      <div class="auth-feature-grid">
        <span>LangGraph</span>
        <span>Agentic RAG</span>
        <span>Chroma</span>
        <span>Redis Memory</span>
      </div>
    </div>
    <el-form class="auth-card" label-position="top" @submit.prevent>
      <div class="auth-head">
        <h2>登录</h2>
        <p>继续使用你的长期旅行记忆。</p>
      </div>
      <el-form-item label="用户名">
        <el-input v-model="form.username" placeholder="请输入用户名" size="large" @keyup.enter="submit" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" placeholder="请输入密码" type="password" show-password size="large" @keyup.enter="submit" />
      </el-form-item>
      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="auth-error" />
      <el-button type="primary" size="large" class="auth-submit" :loading="loading" @click="submit">登录</el-button>
      <p class="auth-link">还没有账号？<RouterLink to="/register">创建账号</RouterLink></p>
    </el-form>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiPost } from '../api'
import { useAuthStore, type AuthUser } from '../stores/auth'

type AuthResponse = {
  access_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const form = reactive({
  username: '',
  password: ''
})
// 说明：submit 处理用户操作或数据加载，是页面交互链路的关键节点。
async function submit() {
  error.value = ''
  if (!form.username || !form.password) {
    error.value = '请填写用户名和密码。'
    return
  }
  loading.value = true
  try {
    const data = await apiPost<AuthResponse>('/v1/auth/login', form)
    auth.setAuth(data.access_token, data.user)
    router.push('/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败，请稍后再试。'
  } finally {
    loading.value = false
  }
}
</script>
