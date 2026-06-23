<template>
  <!-- 本组件负责当前页面或控件的可视化结构，注释说明关键区域和交互入口。 -->
  <section class="page">
    <div class="page-title">
      <div>
        <p class="eyebrow subtle">{{ text.preferences.eyebrow }}</p>
        <h1>{{ text.preferences.title }}</h1>
      </div>
      <el-tag>{{ text.preferences.tag }}</el-tag>
    </div>
    <div class="workspace">
      <el-form class="panel" label-position="top">
        <el-form-item :label="text.preferences.userId">
          <el-input :model-value="displayUser" disabled />
        </el-form-item>
        <el-form-item :label="text.preferences.budgetLevel">
          <el-segmented v-model="form.budget_level" :options="budgetOptions" />
        </el-form-item>
        <el-form-item :label="text.preferences.travelStyle">
          <el-segmented v-model="form.travel_style" :options="styleOptions" />
        </el-form-item>
        <el-form-item :label="text.preferences.pace">
          <el-segmented v-model="form.pace" :options="paceOptions" />
        </el-form-item>
        <el-form-item :label="text.preferences.favoriteThemes">
          <el-select v-model="form.favorite_themes" multiple>
            <el-option v-for="theme in text.options.themes" :key="theme" :label="theme" :value="theme" />
          </el-select>
        </el-form-item>
        <el-form-item :label="text.preferences.dislikedThemes">
          <el-select v-model="form.disliked_themes" multiple>
            <el-option v-for="theme in text.options.disliked" :key="theme" :label="theme" :value="theme" />
          </el-select>
        </el-form-item>
        <el-form-item :label="text.preferences.food">
          <el-input v-model="form.food_preference" />
        </el-form-item>
        <el-form-item :label="text.preferences.hotel">
          <el-input v-model="form.hotel_preference" />
        </el-form-item>
        <el-form-item :label="text.preferences.notes">
          <el-input v-model="form.notes" type="textarea" :rows="4" />
        </el-form-item>
        <div class="toolbar">
          <el-button type="primary" :loading="loading" @click="save">{{ text.preferences.save }}</el-button>
          <el-button @click="load">{{ text.common.load }}</el-button>
          <el-button type="danger" plain @click="remove">{{ text.common.clear }}</el-button>
        </div>
      </el-form>
      <div class="panel result">
        <pre>{{ JSON.stringify(profile, null, 2) || text.preferences.empty }}</pre>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
// 本脚本承载组件状态、接口调用和事件处理，保持模板展示与后端能力解耦。
import { computed, reactive, ref } from 'vue'
import { apiDelete, apiGet, apiPut } from '../api'
import { useAuthStore } from '../stores/auth'
import { zhCN as text } from '../i18n/zhCN'

type Profile = {
  budget_level: string
  travel_style: string
  favorite_themes: string[]
  disliked_themes: string[]
  pace: string
  food_preference: string
  hotel_preference: string
  notes: string
}

const auth = useAuthStore()
const userId = computed(() => auth.user?.id ? String(auth.user.id) : 'me')
const displayUser = computed(() => `${auth.user?.username || '当前用户'}（ID: ${userId.value}）`)
const loading = ref(false)
const profile = ref<Record<string, unknown>>({})
const budgetOptions = [...text.options.budget]
const styleOptions = [...text.options.travelStyle]
const paceOptions = [...text.options.pace]
const form = reactive<Profile>({
  budget_level: text.options.budget[1],
  travel_style: text.options.travelStyle[0],
  favorite_themes: [text.options.themes[0], text.options.themes[2]],
  disliked_themes: [text.options.disliked[0]],
  pace: text.options.pace[1],
  food_preference: text.examples.foodPreference,
  hotel_preference: text.examples.hotelPreference,
  notes: text.examples.notes
})
// 说明：save 处理用户操作或数据加载，是页面交互链路的关键节点。
async function save() {
  loading.value = true
  try {
    const data = await apiPut<{ profile: Record<string, unknown> }>('/v1/preferences/me', form)
    profile.value = data.profile
  } finally {
    loading.value = false
  }
}
// 说明：load 处理用户操作或数据加载，是页面交互链路的关键节点。
async function load() {
  const data = await apiGet<{ profile: Record<string, unknown> }>('/v1/preferences/me')
  profile.value = data.profile
}
// 说明：remove 处理用户操作或数据加载，是页面交互链路的关键节点。
async function remove() {
  await apiDelete('/v1/preferences/me')
  profile.value = {}
}
</script>
