/**
 * 本文件属于前端 TypeScript 逻辑层，注释说明状态、请求和路由等关键职责。
 * 注释只解释工程意图和边界，不修改任何输入输出结构。
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

const Dashboard = () => import('./views/Dashboard.vue')
const AgentWorkspace = () => import('./views/AgentWorkspace.vue')
const TravelWorkspace = () => import('./views/TravelWorkspace.vue')
const KnowledgeWorkspace = () => import('./views/KnowledgeWorkspace.vue')
const CreationWorkspace = () => import('./views/CreationWorkspace.vue')
const Login = () => import('./views/Login.vue')
const Register = () => import('./views/Register.vue')
const AgentRunViewer = () => import('./views/AgentRunViewer.vue')
const SessionHistory = () => import('./views/SessionHistory.vue')
const UserProfile = () => import('./views/UserProfile.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: Login, meta: { public: true } },
    { path: '/register', component: Register, meta: { public: true } },
    { path: '/dashboard', component: Dashboard },
    { path: '/agent', component: AgentWorkspace },
    { path: '/travel', component: TravelWorkspace },
    { path: '/knowledge', component: KnowledgeWorkspace },
    { path: '/creation', component: CreationWorkspace },
    { path: '/runs/:runId', component: AgentRunViewer },
    { path: '/sessions', component: SessionHistory },
    { path: '/profile', component: UserProfile },
    { path: '/optimizer', redirect: '/travel' },
    { path: '/toolkit', redirect: '/travel' },
    { path: '/trip', redirect: '/travel' },
    { path: '/rag', redirect: '/knowledge' },
    { path: '/rag-eval', redirect: '/knowledge' },
    { path: '/kb-admin', redirect: '/knowledge' },
    { path: '/preferences', redirect: '/agent' },
    { path: '/tools', redirect: '/creation' },
    { path: '/copywriter', redirect: '/creation' }
  ]
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const isPublic = Boolean(to.meta.public)
  // 登录页和注册页是公开路由，其余工作台页面必须先拿到 JWT。
  if (!auth.isAuthenticated && !isPublic) {
    // 保存 redirect，登录成功后可以回到用户原本想访问的页面。
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (auth.isAuthenticated && (to.path === '/login' || to.path === '/register')) {
    return '/dashboard'
  }
  return true
})

export default router
