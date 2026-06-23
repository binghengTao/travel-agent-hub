/**
 * 本文件属于前端 TypeScript 逻辑层，注释说明状态、请求和路由等关键职责。
 * 注释只解释工程意图和边界，不修改任何输入输出结构。
 */
import { defineStore } from 'pinia'

export type AuthUser = {
  id: number
  username: string
  email?: string | null
  created_at?: string | null
}

const TOKEN_KEY = 'travelai_access_token'
const USER_KEY = 'travelai_user'
// 说明：readUser 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
function readUser(): AuthUser | null {
  // user 只用于前端展示，真正的身份校验以 accessToken 为准。
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    localStorage.removeItem(USER_KEY)
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    // 刷新页面后从 localStorage 恢复登录态，保证用户记忆和私有知识库能持续绑定同一 user_id。
    accessToken: localStorage.getItem(TOKEN_KEY) || '',
    user: readUser()
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken && state.user)
  },
  actions: {
    setAuth(token: string, user: AuthUser) {
      // 登录成功后同时写 Pinia 和 localStorage，页面刷新不会丢失 token。
      this.accessToken = token
      this.user = user
      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },
    logout() {
      // 退出登录必须同时清理 token 和用户信息，避免后续请求继续携带旧身份。
      this.accessToken = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    }
  }
})
