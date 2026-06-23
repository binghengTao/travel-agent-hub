<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <router-view v-if="isAuthPage" />
  <el-container v-else class="shell">
    <el-aside width="248px" class="sidebar">
      <div class="brand">
        <div>
          <strong>旅行助手</strong>
          <span>{{ text.app.subtitle }}</span>
        </div>
      </div>
      <el-menu router :default-active="$route.path" class="nav">
        <el-menu-item index="/dashboard"><el-icon><Odometer /></el-icon>{{ text.app.nav.dashboard }}</el-menu-item>
        <el-menu-item index="/agent"><el-icon><Cpu /></el-icon>{{ text.app.nav.agent }}</el-menu-item>
        <el-menu-item index="/travel"><el-icon><MapLocation /></el-icon>{{ text.workspace.travel.title }}</el-menu-item>
        <el-menu-item index="/knowledge"><el-icon><Collection /></el-icon>{{ text.workspace.knowledge.title }}</el-menu-item>
        <el-menu-item index="/creation"><el-icon><Compass /></el-icon>{{ text.workspace.creation.title }}</el-menu-item>
        <el-menu-item index="/sessions"><el-icon><Clock /></el-icon>会话历史</el-menu-item>
        <el-menu-item index="/profile"><el-icon><User /></el-icon>个人中心</el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <div class="user-card">
          <span>当前用户</span>
          <strong>{{ auth.user?.username }}</strong>
        </div>
        <div class="sidebar-actions">
          <el-tooltip content="新建会话会保留账号记忆，只切换当前 session">
            <el-button :icon="Plus" circle @click="session.newSession()" />
          </el-tooltip>
          <el-tooltip content="退出登录">
            <el-button :icon="SwitchButton" circle @click="logout" />
          </el-tooltip>
        </div>
      </div>
    </el-aside>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Clock,
  Collection,
  Compass,
  Cpu,
  MapLocation,
  Odometer,
  Plus,
  SwitchButton,
  User
} from '@element-plus/icons-vue'
import { zhCN as text } from './i18n/zhCN'
import { useAuthStore } from './stores/auth'
import { useSessionStore } from './stores/session'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const session = useSessionStore()
const isAuthPage = computed(() => route.path === '/login' || route.path === '/register')
// 说明：logout 处理用户操作或数据加载，是页面交互链路的关键节点。
function logout() {
  auth.logout()
  router.push('/login')
}
</script>
