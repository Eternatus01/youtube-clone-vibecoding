<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Loader2, Upload, X } from 'lucide-vue-next'
import { api, extractError } from '../api/client'
import { putFile } from '../api/upload'
import { formatBytes } from '../utils/format'
import { useToast } from '../composables/useToast'

const toast = useToast()

type Phase = 'form' | 'uploading' | 'processing' | 'done' | 'failed'
type Visibility = 'public' | 'private' | 'unlisted'

const POLL_INTERVAL_MS = 1500
const TITLE_MAX = 100

const file = ref<File | null>(null)
const title = ref('')
const description = ref('')
const visibility = ref<Visibility>('public')
const tags = ref<string[]>([])
const tagsInput = ref('')

const phase = ref<Phase>('form')
const progress = ref(0)
const errorMessage = ref('')
const readyVideoId = ref('')
const dragOver = ref(false)

let pollTimer: number | null = null

const fileInput = ref<HTMLInputElement | null>(null)

const canSubmit = computed(
  () => file.value !== null && title.value.trim().length > 0 && phase.value === 'form',
)

/** Split the raw input on commas, trim and de-duplicate. */
const parsedTags = computed(() => {
  const seen = new Set<string>()
  for (const raw of tagsInput.value.split(',')) {
    const t = raw.trim()
    if (t) seen.add(t)
  }
  return [...seen]
})

function pickFile() {
  fileInput.value?.click()
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const selected = input.files?.[0] ?? null
  setFile(selected)
  input.value = ''
}

function setFile(selected: File | null) {
  if (selected && !selected.type.startsWith('video/')) {
    errorMessage.value = 'Выберите видеофайл.'
    return
  }
  errorMessage.value = ''
  file.value = selected
  if (selected && !title.value.trim()) {
    title.value = selected.name.replace(/\.[^.]+$/, '').slice(0, TITLE_MAX)
  }
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  e.preventDefault()
  setFile(e.dataTransfer?.files?.[0] ?? null)
}

function onDragOver() {
  dragOver.value = true
}

function onDragLeave() {
  dragOver.value = false
}

function reset() {
  stopPolling()
  file.value = null
  phase.value = 'form'
  progress.value = 0
  errorMessage.value = ''
  readyVideoId.value = ''
  tags.value = []
  tagsInput.value = ''
}

/** Commit the current input into the tags list. */
function commitTags() {
  tags.value = parsedTags.value
  tagsInput.value = tags.value.join(', ')
}

function removeTag(tag: string) {
  tags.value = tags.value.filter((t) => t !== tag)
  tagsInput.value = tags.value.join(', ')
}

async function startUpload() {
  if (!canSubmit.value || !file.value) return
  errorMessage.value = ''
  phase.value = 'uploading'
  progress.value = 0

  try {
    // 1. Init: get presigned PUT URL.
    const init = await api.POST('/api/uploads/init', {
      body: {
        filename: file.value.name,
        content_type: file.value.type || 'video/mp4',
        size_bytes: file.value.size,
        title: title.value.trim(),
        description: description.value.trim() || null,
        visibility: visibility.value,
        tags: tags.value,
      },
    })
    if (init.error || !init.data) {
      throw new Error(extractError(init.error, 'Не удалось начать загрузку'))
    }
    const { upload_url, upload_session_id, video_id } = init.data

    // 2. PUT the file with progress.
    await putFile(upload_url, file.value, (pct) => {
      progress.value = pct
    })

    // 3. Complete: backend enqueues transcoding.
    const done = await api.POST('/api/uploads/complete', {
      body: { upload_session_id },
    })
    if (done.error) {
      throw new Error(extractError(done.error, 'Не удалось завершить загрузку'))
    }

    // 4. Poll until the video leaves uploading/processing.
    phase.value = 'processing'
    poll(video_id)
  } catch (e) {
    phase.value = 'failed'
    errorMessage.value = e instanceof Error ? e.message : 'Ошибка загрузки'
    toast.push(errorMessage.value)
  }
}

function poll(videoId: string) {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    try {
      const { data, error: apiError } = await api.GET('/api/videos/{video_id}', {
        params: { path: { video_id: videoId } },
      })
      if (apiError || !data) {
        throw new Error(extractError(apiError, 'Не удалось проверить статус видео'))
      }
      if (data.status === 'ready') {
        stopPolling()
        phase.value = 'done'
        readyVideoId.value = videoId
        toast.push('Видео обработано и опубликовано')
      } else if (data.status === 'failed') {
        stopPolling()
        phase.value = 'failed'
        errorMessage.value = 'Не удалось обработать видео.'
        toast.push(errorMessage.value)
      }
      // still uploading/processing: keep polling
    } catch (e) {
      stopPolling()
      phase.value = 'failed'
      errorMessage.value = e instanceof Error ? e.message : 'Не удалось проверить статус видео'
      toast.push(errorMessage.value)
    }
  }, POLL_INTERVAL_MS)
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="upload">
    <div class="panel">
      <!-- Step 1: pick file + metadata -->
      <template v-if="phase === 'form'">
        <h1 class="panel-title">Загрузить видео</h1>

        <div
          v-if="!file"
          class="dropzone"
          :class="{ over: dragOver }"
          role="button"
          tabindex="0"
          aria-label="Выбрать файл"
          @click="pickFile"
          @keydown.enter.prevent="pickFile"
          @keydown.space.prevent="pickFile"
          @drop="onDrop"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
        >
          <Upload :size="48" stroke-width="1.75" class="drop-icon" />
          <p class="drop-text">Перетащите файл сюда или выберите</p>
          <button class="btn btn-primary pill" type="button" @click.stop="pickFile">
            Выбрать файл
          </button>
        </div>

        <div v-else class="file-row">
          <div class="file-info">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatBytes(file.size) }}</span>
          </div>
          <button class="icon-btn" title="Убрать файл" aria-label="Убрать файл" @click="reset">
            <X :size="20" stroke-width="1.75" />
          </button>
        </div>

        <input
          ref="fileInput"
          type="file"
          accept="video/*"
          class="sr-only"
          @change="onFileChange"
        />

        <form v-if="file" class="meta-form" @submit.prevent="startUpload">
          <div class="field">
            <label for="title">Название</label>
            <div class="counter-wrap">
              <input
                id="title"
                v-model="title"
                class="input input-lg"
                type="text"
                maxlength="100"
                required
              />
              <span class="counter">{{ title.length }}/{{ TITLE_MAX }}</span>
            </div>
          </div>

          <div class="field">
            <label for="description">Описание</label>
            <textarea id="description" v-model="description" class="input" rows="5"></textarea>
          </div>

          <div class="field">
            <label for="tags">Теги</label>
            <input
              id="tags"
              v-model="tagsInput"
              class="input input-lg"
              type="text"
              placeholder="Теги (через запятую)"
              @keydown.enter.prevent="commitTags"
              @blur="commitTags"
            />
            <div v-if="tags.length" class="tags-list">
              <span v-for="t in tags" :key="t" class="tag-chip">
                {{ t }}
                <button
                  type="button"
                  class="tag-remove"
                  :aria-label="`Удалить тег ${t}`"
                  @click="removeTag(t)"
                >
                  <X :size="12" stroke-width="2" />
                </button>
              </span>
            </div>
          </div>

          <div class="field">
            <label for="visibility">Доступ</label>
            <select id="visibility" v-model="visibility" class="input input-lg">
              <option value="public">Публичное</option>
              <option value="private">Приватное</option>
              <option value="unlisted">По ссылке</option>
            </select>
          </div>

          <p v-if="errorMessage" class="inline-error">{{ errorMessage }}</p>

          <button class="btn btn-primary" type="submit" :disabled="!canSubmit">Загрузить</button>
        </form>
      </template>

      <!-- Step 2/3: progress / processing -->
      <div v-else class="status-panel">
        <div class="progress-track">
          <div
            class="progress-fill"
            :class="{ indeterminate: phase !== 'uploading' }"
            :style="phase === 'uploading' ? { width: `${progress}%` } : undefined"
          ></div>
        </div>
        <p class="progress-num">{{ phase === 'uploading' ? `${progress}%` : '' }}</p>

        <p v-if="phase === 'uploading'" class="status-line">
          <span class="status-spin"><Loader2 :size="20" stroke-width="1.75" class="animate-spin" /></span>
          Загрузка…
        </p>
        <p v-else-if="phase === 'processing'" class="status-line">
          <span class="status-spin"><Loader2 :size="20" stroke-width="1.75" class="animate-spin" /></span>
          Обработка…
        </p>

        <template v-else-if="phase === 'done'">
          <p class="status-done">Готово</p>
          <RouterLink
            :to="{ name: 'watch', params: { id: readyVideoId } }"
            class="btn btn-primary pill watch-link"
          >
            Смотреть видео
          </RouterLink>
        </template>

        <template v-else-if="phase === 'failed'">
          <p class="inline-error">{{ errorMessage }}</p>
          <button class="btn" type="button" @click="reset">Повторить</button>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload {
  max-width: 960px;
  margin: 24px auto;
}

.panel {
  background: var(--surface);
  border-radius: 12px;
  padding: 32px;
}

.panel-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 24px;
}

/* ---- Drop zone ---- */
.dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px 24px;
  border: 2px dashed var(--divider);
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  color: var(--text-2);
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.dropzone.over,
.dropzone:hover,
.dropzone:focus-visible {
  border-color: var(--accent);
  outline: none;
}

.dropzone.over {
  background: var(--overlay-hover);
}

.drop-icon {
  color: var(--text-2);
}

.drop-text {
  font-size: 14px;
}

.pill {
  border-radius: 18px;
  height: 40px;
}

/* ---- Selected file row ---- */
.file-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--bg);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 24px;
}

.file-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  word-break: break-all;
}

.file-size {
  font-size: 12px;
  color: var(--text-2);
}

/* ---- Metadata form ---- */
.meta-form {
  margin-top: 8px;
}

.counter-wrap {
  position: relative;
}

.counter {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  color: var(--text-2);
  pointer-events: none;
}

.input-lg {
  height: 48px;
  padding: 10px 12px;
}

.counter-wrap .input-lg {
  padding-right: 56px;
}

.inline-error {
  color: var(--danger);
  font-size: 12px;
  margin-bottom: 12px;
}

/* ---- Tags chips ---- */
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border-radius: 14px;
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  user-select: none;
}

.tag-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border-radius: 50%;
  color: var(--text-2);
}

.tag-remove:hover {
  color: var(--danger);
}

/* ---- Progress / status ---- */
.status-panel {
  max-width: 480px;
  margin: 40px auto;
  text-align: center;
}

.progress-track {
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: var(--surface-hover);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 2px;
  background: var(--accent);
  transition: width 0.15s ease;
}

.progress-fill.indeterminate {
  width: 40%;
}

.progress-num {
  font-size: 12px;
  color: var(--text-2);
  margin: 8px 0 16px;
  min-height: 18px;
}

.status-line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 14px;
}

.status-done {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 16px;
}

.watch-link {
  display: inline-flex;
}

.status-spin {
  display: inline-flex;
  color: var(--text-2);
}

/* animate-spin is Tailwind-ish; define locally */
.animate-spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
