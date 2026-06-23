<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.governance.eyebrow }}</p>
        <h1>{{ text.governance.title }}</h1>
      </div>
      <el-tag type="success">{{ text.governance.tag }}</el-tag>
    </div>

    <div class="workspace">
      <div class="panel">
        <el-alert :title="text.governance.desc" type="info" show-icon :closable="false" />
        <el-form label-position="top" class="governance-form">
          <el-form-item :label="text.governance.adminToken">
            <el-input v-model="adminToken" show-password />
          </el-form-item>
          <el-form-item :label="text.governance.candidateTitle">
            <el-input v-model="form.title" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item :label="text.governance.city">
              <el-input v-model="form.city" />
            </el-form-item>
            <el-form-item :label="text.governance.theme">
              <el-input v-model="form.theme" />
            </el-form-item>
          </div>
          <el-form-item :label="text.governance.tags">
            <el-input v-model="form.tags" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item :label="text.governance.trustLevel">
              <el-select v-model="form.trustLevel">
                <el-option :label="text.governance.low" value="low" />
                <el-option :label="text.governance.medium" value="medium" />
                <el-option :label="text.governance.high" value="high" />
              </el-select>
            </el-form-item>
            <el-form-item :label="text.governance.action">
              <el-select v-model="form.action">
                <el-option :label="text.governance.newDocument" value="new_document" />
                <el-option :label="text.governance.supplement" value="supplement" />
                <el-option :label="text.governance.merge" value="merge" />
                <el-option :label="text.governance.replaceOrMerge" value="replace_or_merge" />
              </el-select>
            </el-form-item>
          </div>
          <el-form-item :label="text.governance.sourceNote">
            <el-input v-model="form.sourceNote" />
          </el-form-item>
          <el-form-item :label="text.governance.summary">
            <el-input v-model="form.summary" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item :label="text.governance.content">
            <el-input v-model="form.content" type="textarea" :rows="5" />
          </el-form-item>
          <el-form-item :label="text.governance.uploadPdf">
            <el-upload drag :auto-upload="false" :limit="1" accept="application/pdf" :on-change="onFileChange" :on-remove="onFileRemove">
              <el-icon><UploadFilled /></el-icon>
              <div>{{ text.governance.selectPdf }}</div>
            </el-upload>
          </el-form-item>
        </el-form>

        <div class="toolbar">
          <el-button type="primary" :icon="Search" :loading="loading" @click="analyze">{{ text.governance.analyze }}</el-button>
          <el-button :icon="DocumentAdd" :loading="loading" @click="registerText">{{ text.governance.registerText }}</el-button>
          <el-button :icon="UploadFilled" :loading="loading" @click="uploadPdf">{{ text.governance.uploadAndRegister }}</el-button>
          <el-button :icon="Refresh" @click="loadRecords">{{ text.governance.refresh }}</el-button>
        </div>
      </div>

      <div class="panel result governance-result">
        <el-alert
          v-if="analysis"
          :title="`${text.governance.recommendation}: ${recommendationLabel(analysis.recommendation)}`"
          :type="analysis.recommendation === 'new_document' ? 'success' : 'warning'"
          show-icon
          :closable="false"
        />
        <el-alert v-if="needsReindex" :title="text.governance.needsReindex" type="warning" show-icon :closable="false" />
        <p v-if="!analysis && !records.length" class="empty-copy">{{ text.governance.emptyResult }}</p>

        <div class="result-section">
          <div class="section-head compact">
            <h2>{{ text.governance.similarDocs }}</h2>
          </div>
          <el-table :data="analysis?.similar_docs || []" height="180">
            <el-table-column prop="name" :label="text.kbAdmin.document" min-width="220" />
            <el-table-column prop="city" :label="text.governance.city" width="100" />
            <el-table-column prop="score" :label="text.common.score" width="100" />
          </el-table>
        </div>

        <div class="result-section">
          <div class="section-head compact">
            <h2>{{ text.governance.records }}</h2>
          </div>
          <el-table :data="records" height="220">
            <el-table-column prop="name" :label="text.kbAdmin.document" min-width="220" />
            <el-table-column prop="city" :label="text.governance.city" width="90" />
            <el-table-column prop="action" :label="text.governance.action" width="120">
              <template #default="{ row }">{{ recommendationLabel(row.action) }}</template>
            </el-table-column>
            <el-table-column prop="status" :label="text.governance.status" width="120">
              <template #default="{ row }">{{ statusLabel(row.status) }}</template>
            </el-table-column>
          </el-table>
        </div>

        <el-divider />
        <div class="form-grid">
          <el-input v-model="mergeForm.sourceDocIds" :placeholder="text.governance.sourceDocs" />
          <el-input v-model="mergeForm.targetTitle" :placeholder="text.governance.targetTitle" />
        </div>
        <div class="form-grid merge-line">
          <el-select v-model="mergeForm.strategy">
            <el-option :label="text.governance.supplement" value="supplement" />
            <el-option :label="text.governance.merge" value="merge" />
            <el-option :label="text.governance.replaceOrMerge" value="replace_or_merge" />
          </el-select>
          <el-button type="primary" :icon="Connection" :loading="loading" @click="generateMergePlan">{{ text.governance.generateMergePlan }}</el-button>
        </div>
        <el-input v-model="mergeForm.notes" type="textarea" :rows="2" :placeholder="text.governance.notes" />
        <pre v-if="mergePlan" class="json-box">{{ JSON.stringify(mergePlan, null, 2) }}</pre>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { onMounted, reactive, ref } from 'vue'
import type { UploadFile } from 'element-plus'
import { Connection, DocumentAdd, Refresh, Search, UploadFilled } from '@element-plus/icons-vue'
import { apiGet, apiPost, apiUploadForm } from '../api'
import { zhCN as text } from '../i18n/zhCN'

type SimilarDoc = {
  doc_id: string
  name: string
  city?: string
  theme?: string
  source?: string
  score?: number
}

type GovernanceAnalysis = {
  recommendation: string
  similar_docs: SimilarDoc[]
}

type GovernanceRecord = {
  record_id: string
  doc_id: string
  name: string
  city?: string
  theme?: string
  action: string
  status: string
  version: number
}

type GovernanceRecordsResponse = {
  records: GovernanceRecord[]
  merge_plans: unknown[]
}

const adminToken = ref('change-me')
const loading = ref(false)
const selectedFile = ref<File | null>(null)
const analysis = ref<GovernanceAnalysis | null>(null)
const records = ref<GovernanceRecord[]>([])
const mergePlan = ref<unknown | null>(null)
const needsReindex = ref(false)

const form = reactive({
  title: text.governance.defaultTitle,
  city: text.examples.destinationHangzhou,
  theme: text.governance.defaultTheme,
  tags: text.governance.defaultTags,
  trustLevel: 'medium',
  action: 'new_document',
  sourceNote: text.governance.manualSource,
  summary: text.governance.defaultSummary,
  content: text.governance.defaultContent
})

const mergeForm = reactive({
  sourceDocIds: '',
  targetTitle: text.governance.defaultTitle,
  strategy: 'merge',
  notes: ''
})
// 说明：onFileChange 处理用户操作或数据加载，是页面交互链路的关键节点。
function onFileChange(upload: UploadFile) {
  selectedFile.value = upload.raw || null
}
// 说明：onFileRemove 处理用户操作或数据加载，是页面交互链路的关键节点。
function onFileRemove() {
  selectedFile.value = null
}
// 说明：splitTags 处理用户操作或数据加载，是页面交互链路的关键节点。
function splitTags(value: string) {
  return value.split(/[,\uFF0C\u3001;\s]+/).map((item) => item.trim()).filter(Boolean)
}
// 说明：recommendationLabel 处理用户操作或数据加载，是页面交互链路的关键节点。
function recommendationLabel(value: string) {
  const labels: Record<string, string> = {
    new_document: text.governance.newDocument,
    supplement: text.governance.supplement,
    merge: text.governance.merge,
    replace_or_merge: text.governance.replaceOrMerge
  }
  return labels[value] || value
}
// 说明：statusLabel 处理用户操作或数据加载，是页面交互链路的关键节点。
function statusLabel(value: string) {
  const labels: Record<string, string> = {
    active: text.governance.activeStatus,
    pending_merge: text.governance.pendingMergeStatus
  }
  return labels[value] || value
}
// 说明：buildAnalyzePayload 处理用户操作或数据加载，是页面交互链路的关键节点。
function buildAnalyzePayload() {
  return {
    title: form.title,
    city: form.city,
    theme: form.theme,
    tags: splitTags(form.tags),
    summary: form.summary
  }
}
// 说明：applyAnalysis 处理用户操作或数据加载，是页面交互链路的关键节点。
function applyAnalysis(data: GovernanceAnalysis) {
  analysis.value = data
  form.action = data.recommendation || form.action
  if (!mergeForm.sourceDocIds && data.similar_docs?.length) {
    mergeForm.sourceDocIds = data.similar_docs.slice(0, 2).map((doc) => doc.doc_id || doc.name).join(',')
  }
}
// 说明：analyze 处理用户操作或数据加载，是页面交互链路的关键节点。
async function analyze() {
  loading.value = true
  needsReindex.value = false
  try {
    const data = await apiPost<GovernanceAnalysis>('/v1/kb/governance/analyze', buildAnalyzePayload())
    applyAnalysis(data)
  } finally {
    loading.value = false
  }
}
// 说明：registerText 处理用户操作或数据加载，是页面交互链路的关键节点。
async function registerText() {
  loading.value = true
  try {
    const data = await apiPost<{ analysis: GovernanceAnalysis; needs_reindex: boolean }>('/v1/kb/governance/register-text', {
      ...buildAnalyzePayload(),
      content: form.content,
      source_note: form.sourceNote,
      trust_level: form.trustLevel,
      action: form.action
    }, { 'x-admin-token': adminToken.value })
    applyAnalysis(data.analysis)
    needsReindex.value = data.needs_reindex
    await loadRecords()
  } finally {
    loading.value = false
  }
}
// 说明：uploadPdf 处理用户操作或数据加载，是页面交互链路的关键节点。
async function uploadPdf() {
  if (!selectedFile.value) return
  loading.value = true
  try {
    const data = new FormData()
    data.append('upload', selectedFile.value)
    data.append('city', form.city)
    data.append('theme', form.theme)
    data.append('tags', form.tags)
    data.append('source_note', form.sourceNote)
    data.append('trust_level', form.trustLevel)
    data.append('action', form.action)
    data.append('summary', form.summary)
    const result = await apiUploadForm<{ analysis: GovernanceAnalysis; needs_reindex: boolean }>('/v1/kb/governance/upload', data, { 'x-admin-token': adminToken.value })
    applyAnalysis(result.analysis)
    needsReindex.value = result.needs_reindex
    await loadRecords()
  } finally {
    loading.value = false
  }
}
// 说明：loadRecords 处理用户操作或数据加载，是页面交互链路的关键节点。
async function loadRecords() {
  try {
    const data = await apiGet<GovernanceRecordsResponse>('/v1/kb/governance/records')
    records.value = data.records
  } catch {
    records.value = []
  }
}
// 说明：generateMergePlan 处理用户操作或数据加载，是页面交互链路的关键节点。
async function generateMergePlan() {
  loading.value = true
  try {
    const data = await apiPost<unknown>('/v1/kb/governance/merge-plan', {
      source_doc_ids: splitTags(mergeForm.sourceDocIds),
      target_title: mergeForm.targetTitle,
      strategy: mergeForm.strategy,
      notes: mergeForm.notes
    })
    mergePlan.value = data
  } finally {
    loading.value = false
  }
}

onMounted(loadRecords)
</script>

<style scoped>
.governance-form {
  margin-top: 14px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.governance-result {
  display: grid;
  gap: 12px;
}

.result-section {
  display: grid;
  gap: 8px;
}

.compact {
  margin-bottom: 0;
}

.empty-copy {
  color: #60737b;
  margin: 0;
}

.merge-line {
  align-items: center;
}

.json-box {
  padding: 12px;
  border: 1px solid #d8e6e7;
  border-radius: 8px;
  background: #f7fbfa;
  max-height: 280px;
  overflow: auto;
}

@media (max-width: 900px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
