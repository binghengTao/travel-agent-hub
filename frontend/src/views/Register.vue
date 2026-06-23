<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="auth-page">
    <div class="auth-visual">
      <p class="eyebrow subtle">旅行助手</p>
      <h1>创建你的旅行记忆空间</h1>
      <p>账号会绑定长期画像、事实记忆、会话摘要和 Agent run 轨迹，刷新页面后仍能延续上下文。</p>
      <div class="auth-feature-grid">
        <span>JWT</span>
        <span>SQLite</span>
        <span>Redis</span>
        <span>Context Compression</span>
      </div>
    </div>
    <el-form class="auth-card" label-position="top" @submit.prevent>
      <div class="auth-head">
        <h2>注册</h2>
        <p>本地演示账号，无短信和邮箱验证。</p>
      </div>
      <el-form-item label="用户名">
        <el-input v-model="form.username" placeholder="至少 3 个字符" size="large" />
      </el-form-item>
      <el-form-item label="邮箱，可选">
        <el-input v-model="form.email" placeholder="用于后续扩展，不填也可以" size="large" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" placeholder="至少 6 个字符" type="password" show-password size="large" @keyup.enter="submit" />
      </el-form-item>
      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="auth-error" />
      <el-button type="primary" size="large" class="auth-submit" :loading="loading" @click="submit">注册并进入</el-button>
      <p class="auth-link">已有账号？<RouterLink to="/login">去登录</RouterLink></p>
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
  email: '',
  password: ''
})
// 说明：submit 处理用户操作或数据加载，是页面交互链路的关键节点。
async function submit() {
  error.value = ''
  if (form.username.length < 3) {
    error.value = '用户名至少需要 3 个字符。'
    return
  }
  if (form.password.length < 6) {
    error.value = '密码至少需要 6 个字符。'
    return
  }
  loading.value = true
  try {
    const data = await apiPost<AuthResponse>('/v1/auth/register', {
      username: form.username,
      password: form.password,
      email: form.email || null
    })
    auth.setAuth(data.access_token, data.user)
    router.push('/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '注册失败，请稍后再试。'
  } finally {
    loading.value = false
  }
}
</script>
