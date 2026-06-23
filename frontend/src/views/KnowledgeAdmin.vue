<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.kbAdmin.eyebrow }}</p>
        <h1>{{ text.kbAdmin.title }}</h1>
      </div>
      <el-tag>PDF / Chroma / BM25</el-tag>
    </div>
    <div class="workspace">
      <div class="panel">
        <el-form label-position="top">
          <el-form-item :label="text.kbAdmin.adminToken">
            <el-input v-model="adminToken" show-password />
          </el-form-item>
          <el-form-item :label="text.kbAdmin.uploadPdf">
            <el-upload drag :auto-upload="false" :limit="1" accept="application/pdf" :on-change="onFileChange">
              <el-icon><UploadFilled /></el-icon>
              <div>{{ text.kbAdmin.selectPdf }}</div>
            </el-upload>
          </el-form-item>
        </el-form>
        <div class="toolbar">
          <el-button type="primary" :loading="loading" @click="upload">{{ text.kbAdmin.upload }}</el-button>
          <el-button :loading="loading" @click="reindex">{{ text.kbAdmin.reindex }}</el-button>
          <el-button @click="loadDocs">{{ text.common.refresh }}</el-button>
        </div>
      </div>
      <div class="panel result">
        <el-table :data="docs" height="520">
          <el-table-column prop="name" :label="text.kbAdmin.document" min-width="220" />
          <el-table-column prop="size" :label="text.kbAdmin.size" width="120" />
          <el-table-column :label="text.kbAdmin.action" width="100">
            <template #default="{ row }">
              <el-button link type="danger" @click="deleteDoc(row.doc_id)">{{ text.common.delete }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { onMounted, ref } from 'vue'
import type { UploadFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { apiDelete, apiGet, apiPost, apiUpload } from '../api'
import { zhCN as text } from '../i18n/zhCN'

type DocumentItem = { doc_id: string; name: string; size: number }

const adminToken = ref('change-me')
const loading = ref(false)
const file = ref<File | null>(null)
const docs = ref<DocumentItem[]>([])
// 说明：onFileChange 处理用户操作或数据加载，是页面交互链路的关键节点。
function onFileChange(upload: UploadFile) {
  file.value = upload.raw || null
}
// 说明：loadDocs 处理用户操作或数据加载，是页面交互链路的关键节点。
async function loadDocs() {
  try {
    const data = await apiGet<{ documents: DocumentItem[] }>('/v1/kb/documents')
    docs.value = data.documents
  } catch {
    docs.value = []
  }
}
// 说明：upload 处理用户操作或数据加载，是页面交互链路的关键节点。
async function upload() {
  if (!file.value) return
  loading.value = true
  try {
    await apiUpload('/v1/kb/upload', 'upload', file.value, { 'x-admin-token': adminToken.value })
    await loadDocs()
  } finally {
    loading.value = false
  }
}
// 说明：reindex 处理用户操作或数据加载，是页面交互链路的关键节点。
async function reindex() {
  loading.value = true
  try {
    await apiPost('/v1/kb/reindex', {}, { 'x-admin-token': adminToken.value })
  } finally {
    loading.value = false
  }
}
// 说明：deleteDoc 处理用户操作或数据加载，是页面交互链路的关键节点。
async function deleteDoc(docId: string) {
  await apiDelete(`/v1/kb/documents/${encodeURIComponent(docId)}`, { 'x-admin-token': adminToken.value })
  await loadDocs()
}

onMounted(loadDocs)
</script>
