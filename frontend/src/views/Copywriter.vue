<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.copywriter.eyebrow }}</p>
        <h1>{{ text.copywriter.title }}</h1>
      </div>
      <el-tag type="success">{{ text.copywriter.tag }}</el-tag>
    </div>
    <div class="workspace">
      <div class="panel">
        <el-upload drag :auto-upload="false" :limit="1" accept="image/*" :on-change="onImageChange">
          <el-icon><UploadFilled /></el-icon>
          <div>{{ text.copywriter.dropImage }}</div>
        </el-upload>
        <el-form label-position="top" style="margin-top: 12px">
          <el-form-item :label="text.copywriter.style">
            <el-select v-model="style">
              <el-option v-for="option in text.options.copyStyles" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
          <el-form-item :label="text.copywriter.caption">
            <el-input v-model="caption" type="textarea" :rows="4" />
          </el-form-item>
        </el-form>
        <div class="toolbar">
          <el-button type="primary" :icon="Picture" :loading="loading" @click="captionImage">{{ text.copywriter.captionBtn }}</el-button>
          <el-button type="primary" :icon="EditPen" :loading="loading" @click="writeCopy">{{ text.copywriter.copyBtn }}</el-button>
          <el-button :icon="Microphone" :loading="loading" @click="tts">{{ text.copywriter.ttsBtn }}</el-button>
          <el-button :icon="Brush" :loading="loading" @click="image">{{ text.copywriter.imageBtn }}</el-button>
        </div>
      </div>
      <div class="panel result">
        <div>{{ answer || text.copywriter.empty }}</div>
        <audio v-if="audioUrl" :src="audioUrl" controls />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { ref } from 'vue'
import { Brush, EditPen, Microphone, Picture, UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile } from 'element-plus'
import { apiPost, apiUpload } from '../api'
import { useSessionStore } from '../stores/session'
import { zhCN as text } from '../i18n/zhCN'

const session = useSessionStore()
const loading = ref(false)
const file = ref<File | null>(null)
const style = ref(text.options.copyStyles[0])
const caption = ref('')
const answer = ref('')
const audioUrl = ref('')
// 说明：onImageChange 处理用户操作或数据加载，是页面交互链路的关键节点。
function onImageChange(upload: UploadFile) {
  file.value = upload.raw || null
}
// 说明：captionImage 处理用户操作或数据加载，是页面交互链路的关键节点。
async function captionImage() {
  if (!file.value) return
  loading.value = true
  try {
    const data = await apiUpload<{ caption: string }>('/media/caption', 'image', file.value)
    caption.value = data.caption
  } finally {
    loading.value = false
  }
}
// 说明：writeCopy 处理用户操作或数据加载，是页面交互链路的关键节点。
async function writeCopy() {
  loading.value = true
  try {
    const data = await apiPost<{ answer: string }>('/media/copywriting', {
      image_caption: caption.value,
      style: style.value,
      session_id: session.sessionId
    })
    answer.value = data.answer
  } catch (error) {
    answer.value = error instanceof Error ? error.message : text.common.backendError
  } finally {
    loading.value = false
  }
}
// 说明：tts 处理用户操作或数据加载，是页面交互链路的关键节点。
async function tts() {
  loading.value = true
  try {
    const data = await apiPost<{ output_url?: string; message: string }>('/media/tts', {
      text: answer.value || caption.value,
      session_id: session.sessionId
    })
    audioUrl.value = data.output_url || ''
    answer.value = data.message
  } catch (error) {
    answer.value = error instanceof Error ? error.message : text.common.backendError
  } finally {
    loading.value = false
  }
}
// 说明：image 处理用户操作或数据加载，是页面交互链路的关键节点。
async function image() {
  loading.value = true
  try {
    const data = await apiPost<{ output_url?: string; message: string }>('/media/image', {
      prompt: answer.value || caption.value,
      session_id: session.sessionId
    })
    answer.value = `${data.message}\n${data.output_url || ''}`
  } catch (error) {
    answer.value = error instanceof Error ? error.message : text.common.backendError
  } finally {
    loading.value = false
  }
}
</script>
