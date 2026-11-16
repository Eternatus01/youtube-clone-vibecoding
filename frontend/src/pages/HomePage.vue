<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { components } from '../api/schema'
import VideoCard from '../components/VideoCard.vue'

type VideoOut = components['schemas']['VideoOut']

const route = useRoute()

const videos = ref<VideoOut[]>([])
const loading = ref(true)
const error = ref('')
const search = ref('')

const categories = [
  'Все',
  'Музыка',
  'Игры',
  'Фильмы',
  'Спорт',
  'Обучение',
  'Новости',
  'Технологии',
]
const activeCategory = ref('Все')

async function load() {
  loading.value = true
  error.value = ''
  search.value = typeof route.query.search === 'string' ? route.query.search : ''

  const { data, error: apiError } = await api.GET('/api/videos/', {
    params: {
      query: {
        page: 1,
        page_size: 20,
        ...(search.value ? { search: search.value } : {}),
      },
    },
  })

  if (apiError || !data) {
    error.value = 'Не удалось загрузить видео. Попробуйте еще раз.'
    videos.value = []
  } else {
    // Backend PaginatedResponse.items is untyped; the list endpoint returns videos.
    videos.value = (data.items as VideoOut[]) ?? []
  }
  loading.value = false
}

function retry() {
  load()
}

onMounted(load)
watch(
  () => route.query.search,
  () => {
    if (route.name === 'home') load()
  },
)
</script>

<template>
  <div class="page">
    <div class="chips" role="tablist" aria-label="Категории">
      <button
        v-for="c in categories"
        :key="c"
        type="button"
        class="chip"
        :class="{ active: c === activeCategory }"
        :aria-pressed="c === activeCategory"
        @click="activeCategory = c"
      >
        {{ c }}
      </button>
    </div>

    <h1 v-if="search" class="page-title">Результаты: «{{ search }}»</h1>
    <h1 v-else class="page-title">Рекомендации</h1>

    <div v-if="error" class="error-banner">
      {{ error }}
      <button class="btn retry-btn" @click="retry">Повторить</button>
    </div>

    <div v-if="loading" class="grid" aria-hidden="true">
      <div v-for="n in 12" :key="n" class="card-skeleton">
        <div class="skeleton thumb-skeleton"></div>
        <div class="skel-row">
          <div class="skeleton avatar-skeleton"></div>
          <div class="skel-lines">
            <div class="skeleton skel-line skel-title"></div>
            <div class="skeleton skel-line skel-channel"></div>
            <div class="skeleton skel-line skel-meta"></div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="videos.length" class="grid">
      <VideoCard v-for="v in videos" :key="v.id" :video="v" />
    </div>

    <div v-else-if="!error" class="empty-state">
      <h2>{{ search ? 'По вашему запросу ничего не найдено' : 'Нет видео' }}</h2>
      <p>
        {{
          search
            ? 'Попробуйте изменить поисковый запрос.'
            : 'Будьте первым, кто загрузит видео!'
        }}
      </p>
    </div>
  </div>
</template>

<style scoped>
/* ---- Chips row ---- */
.chips {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  gap: 12px;
  padding: 8px 0;
  margin: 0 -24px;
  padding-left: 24px;
  padding-right: 24px;
  background: var(--bg);
  margin-bottom: 12px;
  overflow-x: auto;
  scrollbar-width: none;
}

.chips::-webkit-scrollbar {
  display: none;
}

.chip {
  flex-shrink: 0;
  height: 32px;
  padding: 0 12px;
  border-radius: 16px;
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}

.chip:hover {
  background: var(--surface-hover);
}

.chip.active {
  background: var(--text);
  color: var(--bg);
}

.chip.active:hover {
  background: var(--text);
}

/* ---- Grid ---- */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px 16px;
}

@media (max-width: 792px) {
  .grid {
    grid-template-columns: 1fr;
  }
}

/* ---- Skeletons: mirror real VideoCard geometry ---- */
.card-skeleton .thumb-skeleton {
  aspect-ratio: 16 / 9;
  border-radius: var(--radius);
}

.card-skeleton .skel-row {
  display: flex;
  gap: 12px;
  padding: 12px 0 0;
}

.card-skeleton .avatar-skeleton {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
}

.card-skeleton .skel-lines {
  flex: 1;
  min-width: 0;
}

.card-skeleton .skel-line {
  margin-bottom: 6px;
}

.card-skeleton .skel-title {
  height: 14px;
  width: 100%;
}

.card-skeleton .skel-channel {
  height: 12px;
  width: 60%;
}

.card-skeleton .skel-meta {
  height: 12px;
  width: 40%;
  margin-bottom: 0;
}
</style>
