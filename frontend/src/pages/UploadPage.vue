<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, extractError } from '../api/client'
import { putFile } from '../api/upload'
import { formatBytes } from '../utils/format'

const router = useRouter()

type Phase = 'form' | 'uploading' | 'processing' | 'failed'
type Visibility = 'public' | 'private' | 'unlisted'

const POLL_INTERVAL_MS = 1500

const file = ref<File | null>(null)
const title = ref('')
const description = ref('')
const visibility = ref<Visibility>('public')

const phase = ref<Phase>('form')
const progress = ref(0)
const errorMessage = ref('')
const statusText = ref('')

let pollTimer: number | null = null

const fileInput = ref<HTMLInputElement | null>(null)

const canSubmit = computed(
  () => file.value !== null && title.value.trim().length > 0 && phase.value === 'form',
)

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
    errorMessage.value = 'Please select a video file.'
    return
  }
  errorMessage.value = ''
  file.value = selected
  if (selected && !title.value.trim()) {
    title.value = selected.name.replace(/\.[^.]+$/, '')
  }
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  setFile(e.dataTransfer?.files?.[0] ?? null)
}

function reset() {
  stopPolling()
  file.value = null
  phase.value = 'form'
  progress.value = 0
  errorMessage.value = ''
  statusText.value = ''
}

async function startUpload() {
  if (!canSubmit.value || !file.value) return
  errorMessage.value = ''
  phase.value = 'uploading'
  progress.value = 0
  statusText.value = 'Uploading…'

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
      },
    })
    if (init.error || !init.data) {
      throw new Error(extractError(init.error, 'Failed to start upload'))
    }
    const { upload_url, upload_session_id, video_id } = init.data

    // 2. PUT the file with progress.
    statusText.value = `Uploading… ${progress.value}%`
    await putFile(upload_url, file.value, (pct) => {
      progress.value = pct
      statusText.value = `Uploading… ${pct}%`
    })

    // 3. Complete: backend enqueues transcoding.
    statusText.value = 'Finishing upload…'
    const done = await api.POST('/api/uploads/complete', {
      body: { upload_session_id },
    })
    if (done.error) {
      throw new Error(extractError(done.error, 'Failed to complete upload'))
    }

    // 4. Poll until the video leaves uploading/processing.
    phase.value = 'processing'
    statusText.value = 'Processing video…'
    progress.value = 0
    poll(video_id)
  } catch (e) {
    phase.value = 'failed'
    errorMessage.value = e instanceof Error ? e.message : 'Upload failed'
    statusText.value = ''
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
        throw new Error(extractError(apiError, 'Failed to check video status'))
      }
      if (data.status === 'ready') {
        stopPolling()
        router.push({ name: 'watch', params: { id: videoId } })
      } else if (data.status === 'failed') {
        stopPolling()
        phase.value = 'failed'
        errorMessage.value = 'Video processing failed.'
        statusText.value = ''
      }
      // still uploading/processing: keep polling
    } catch (e) {
      stopPolling()
      phase.value = 'failed'
      errorMessage.value = e instanceof Error ? e.message : 'Failed to check video status'
      statusText.value = ''
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
  <div class="page upload">
    <h1 class="page-title">Upload video</h1>

    <div v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
      <button v-if="phase === 'failed'" class="btn" style="margin-left: 12px" @click="reset">
        Start over
      </button>
    </div>

    <!-- Step 1: pick file + metadata -->
    <form v-if="phase === 'form'" class="panel" @submit.prevent="startUpload">
      <div
        class="dropzone"
        :class="{ filled: file }"
        role="button"
        tabindex="0"
        aria-label="Select video file"
        @click="pickFile"
        @keydown.enter.prevent="pickFile"
        @keydown.space.prevent="pickFile"
        @dragover.prevent
        @drop="onDrop"
      >
        <template v-if="file">
          <div class="file-name">{{ file.name }}</div>
          <div class="file-size">{{ formatBytes(file.size) }}</div>
          <button type="button" class="btn" @click.stop="pickFile">Change file</button>
        </template>
        <template v-else>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" class="drop-icon">
            <path d="M12 4l6 6h-4v7h-4v-7H6l6-6zM5 19h14v2H5v-2z" />
          </svg>
          <p>Select a video file to upload</p>
          <p class="hint">Or drag and drop it here</p>
        </template>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept="video/*,.mp4,.webm,.mov"
        hidden
        @change="onFileChange"
      />

      <div class="field">
        <label for="title">Title *</label>
        <input id="title" v-model="title" class="input" type="text" maxlength="200" required />
      </div>

      <div class="field">
        <label for="description">Description</label>
        <textarea id="description" v-model="description" class="input" rows="4"></textarea>
      </div>

      <div class="field">
        <label for="visibility">Visibility</label>
        <select id="visibility" v-model="visibility" class="input">
          <option value="public">Public</option>
          <option value="private">Private</option>
          <option value="unlisted">Unlisted</option>
        </select>
      </div>

      <button class="btn btn-primary" type="submit" :disabled="!canSubmit">Upload</button>
    </form>

    <!-- Step 2/3: progress -->
    <div v-else class="panel">
      <h2 class="status-title">{{ statusText || (phase === 'processing' ? 'Processing video…' : 'Working…') }}</h2>
      <div class="progress-track" role="progressbar">
        <div
          class="progress-fill"
          :class="{ indeterminate: phase === 'processing' || (!progress && phase === 'uploading') }"
          :style="phase === 'uploading' && progress ? { width: `${progress}%` } : undefined"
        ></div>
      </div>
      <p v-if="phase === 'processing'" class="hint">
        Transcoding usually takes a moment. You will be redirected when the video is ready.
      </p>
    </div>
  </div>
</template>

<style scoped>
.upload {
  max-width: 720px;
}

.panel {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
}

.dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 24px;
  border: 2px dashed var(--border);
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  margin-bottom: 24px;
  color: var(--text-secondary);
}

.dropzone:hover,
.dropzone:focus-visible {
  border-color: var(--accent);
  outline: none;
}

.dropzone.filled {
  color: var(--text);
  border-style: solid;
}

.drop-icon {
  color: var(--text-secondary);
}

.file-name {
  font-weight: 600;
  word-break: break-all;
}

.file-size {
  font-size: 12px;
  margin-bottom: 8px;
}

.hint {
  color: var(--text-secondary);
  font-size: 12px;
}

.status-title {
  font-size: 16px;
  margin-bottom: 16px;
}
</style>
