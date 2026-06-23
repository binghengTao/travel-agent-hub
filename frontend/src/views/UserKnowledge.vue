<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">Personal RAG Workspace</p>
        <h1>我的文件知识库</h1>
      </div>
      <el-tag>Private RAG / User Scope</el-tag>
    </div>
    <div class="workspace">
      <div class="panel">
        <el-alert
          title="这里上传的文件只属于当前登录用户，不会进入公共攻略库。需要进入公共库时，再由管理员通过攻略治理流程合并。"
          type="info"
          show-icon
          :closable="false"
        />

        <h3>上传文件</h3>
        <el-upload drag :auto-upload="false" :limit="1" accept=".pdf,.md,.txt" :on-change="onFileChange" :on-remove="onFileRemove">
          <el-icon><UploadFilled /></el-icon>
          <div>选择 PDF / Markdown / TXT</div>
        </el-upload>
        <el-input v-model="uploadCity" placeholder="城市，可选" style="margin-top: 8px" />
        <el-input v-model="uploadTags" placeholder="标签，用逗号分隔，可选" style="margin-top: 8px" />
        <el-button type="primary" :loading="loading" style="margin-top: 10px" @click="upload">上传文件</el-button>

        <h3>记录文字攻略</h3>
        <el-input v-model="textForm.title" placeholder="标题，例如：杭州西湖雨天避坑笔记" />
        <el-input v-model="textForm.city" placeholder="城市，可选" style="margin-top: 8px" />
        <el-input v-model="textForm.tags" placeholder="标签，用逗号分隔" style="margin-top: 8px" />
        <el-input v-model="textForm.content" type="textarea" :rows="6" placeholder="把你发现的新攻略、避坑点、路线经验写在这里" style="margin-top: 8px" />
        <div class="toolbar" style="margin-top: 10px">
          <el-button :loading="loading" @click="registerText">保存文字攻略</el-button>
          <el-button type="success" :loading="loading" @click="reindex">重建个人索引</el-button>
          <el-button @click="loadDocuments">刷新列表</el-button>
        </div>

        <h3>基于我的文件提问</h3>
        <el-input v-model="question" type="textarea" :rows="4" placeholder="例如：根据我上传的攻略，杭州下雨天怎么安排？" />
        <el-button type="primary" :icon="Search" :loading="loading" style="margin-top: 10px" @click="askPersonal">查询我的文件</el-button>
      </div>

      <div class="panel result">
        <el-alert v-if="notice" :title="notice" type="success" show-icon :closable="false" style="margin-bottom: 12px" />
        <h3>我的文件</h3>
        <el-table :data="documents" size="small" style="width: 100%">
          <el-table-column prop="original_name" label="原始名称" min-width="160" />
          <el-table-column prop="city" label="城市" width="90" />
          <el-table-column prop="size" label="大小" width="90" />
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-button link type="danger" @click="remove(row.doc_id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <h3>回答</h3>
        <pre>{{ answer || '用户文件问答结果会显示在这里。' }}</pre>
        <SourceList :sources="sources" />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { onMounted, reactive, ref } from 'vue'
import type { UploadFile } from 'element-plus'
import { Search, UploadFilled } from '@element-plus/icons-vue'
import SourceList from '../components/SourceList.vue'
import { apiDelete, apiGet, apiPost, apiUploadForm, type Source } from '../api'
import { useSessionStore } from '../stores/session'

type UserDocument = {
  doc_id: string
  name: string
  original_name: string
  city?: string
  tags?: string[]
  size: number
}

const session = useSessionStore()
const loading = ref(false)
const selectedFile = ref<File | null>(null)
const uploadCity = ref('')
const uploadTags = ref('')
const documents = ref<UserDocument[]>([])
const answer = ref('')
const notice = ref('')
const sources = ref<Source[]>([])
const question = ref('根据我上传的攻略，杭州下雨天怎么安排？')
const textForm = reactive({
  title: '杭州西湖雨天避坑笔记',
  city: '杭州',
  tags: '西湖,雨天,避坑',
  content: '雨天不要把西湖外圈步行排得太满，可以优先安排博物馆、茶馆、湖滨商圈，傍晚雨小后再去白堤或湖滨步行。'
})

onMounted(loadDocuments)
// 说明：onFileChange 处理用户操作或数据加载，是页面交互链路的关键节点。
function onFileChange(upload: UploadFile) {
  selectedFile.value = upload.raw || null
}
// 说明：onFileRemove 处理用户操作或数据加载，是页面交互链路的关键节点。
function onFileRemove() {
  selectedFile.value = null
}
// 说明：upload 处理用户操作或数据加载，是页面交互链路的关键节点。
async function upload() {
  if (!selectedFile.value) {
    notice.value = '请先选择文件。'
    return
  }
  loading.value = true
  try {
    const data = new FormData()
    data.append('upload', selectedFile.value)
    data.append('city', uploadCity.value)
    data.append('tags', uploadTags.value)
    await apiUploadForm('/v1/user-kb/upload', data)
    notice.value = '上传成功，建议重建个人索引。'
    await loadDocuments()
  } finally {
    loading.value = false
  }
}
// 说明：registerText 处理用户操作或数据加载，是页面交互链路的关键节点。
async function registerText() {
  loading.value = true
  try {
    await apiPost('/v1/user-kb/register-text', {
      title: textForm.title,
      city: textForm.city,
      tags: splitTags(textForm.tags),
      content: textForm.content,
      source_note: 'user_note',
      trust_level: 'user_provided'
    })
    notice.value = '文字攻略已保存，建议重建个人索引。'
    await loadDocuments()
  } finally {
    loading.value = false
  }
}
// 说明：reindex 处理用户操作或数据加载，是页面交互链路的关键节点。
async function reindex() {
  loading.value = true
  try {
    const data = await apiPost<{ files: number; chunks: number }>('/v1/user-kb/reindex', {})
    notice.value = `个人索引已重建：${data.files} 个文件，${data.chunks} 个片段。`
  } finally {
    loading.value = false
  }
}
// 说明：loadDocuments 处理用户操作或数据加载，是页面交互链路的关键节点。
async function loadDocuments() {
  const data = await apiGet<{ documents: UserDocument[] }>('/v1/user-kb/documents')
  documents.value = data.documents
}
// 说明：remove 处理用户操作或数据加载，是页面交互链路的关键节点。
async function remove(docId: string) {
  await apiDelete(`/v1/user-kb/documents/${encodeURIComponent(docId)}`)
  notice.value = '文件已删除，建议重建个人索引。'
  await loadDocuments()
}
// 说明：askPersonal 处理用户操作或数据加载，是页面交互链路的关键节点。
async function askPersonal() {
  loading.value = true
  try {
    const data = await apiPost<{ answer: string; sources: Source[] }>('/v1/user-kb/query', {
      question: question.value,
      session_id: session.sessionId
    })
    answer.value = data.answer
    sources.value = data.sources || []
  } catch (error) {
    answer.value = error instanceof Error ? error.message : '请求失败，请检查后端服务。'
  } finally {
    loading.value = false
  }
}
// 说明：splitTags 处理用户操作或数据加载，是页面交互链路的关键节点。
function splitTags(raw: string) {
  return raw.split(/[,，、;\s]+/).map((item) => item.trim()).filter(Boolean)
}
</script>
