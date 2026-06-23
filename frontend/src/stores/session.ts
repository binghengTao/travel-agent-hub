/**
 * 本文件属于前端 TypeScript 逻辑层，注释说明状态、请求和路由等关键职责。
 * 注释只解释工程意图和边界，不修改任何输入输出结构。
 */
import { defineStore } from 'pinia'

const SESSION_KEY = 'travelai_session_id'
// 说明：createSessionId 是当前模块的处理入口之一，负责衔接数据、服务或接口调用。
function createSessionId() {
  // session_id 表示一次会话，不等同于 user_id；持久化后刷新页面仍能继续同一轮对话。
  const existing = localStorage.getItem(SESSION_KEY)
  if (existing) return existing
  const next = crypto.randomUUID()
  localStorage.setItem(SESSION_KEY, next)
  return next
}

export const useSessionStore = defineStore('session', {
  state: () => ({
    sessionId: createSessionId(),
    apiBase: import.meta.env.VITE_API_BASE_URL || '/api'
  }),
  actions: {
    newSession() {
      // 新建会话只切换聊天上下文，不影响登录用户和长期画像。
      this.sessionId = crypto.randomUUID()
      localStorage.setItem(SESSION_KEY, this.sessionId)
    }
  }
})
