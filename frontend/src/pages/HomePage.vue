<script setup lang="ts">
const videos = [
  { id: '1', title: 'Sample Video', views: 1234, duration: '10:30' },
]
</script>

<template>
  <div class="home">
    <h1>YouTube Clone</h1>
    <div class="feed">
      <div v-for="v in videos" :key="v.id" class="card">
        <div class="thumbnail">▶</div>
        <div class="info">
          <div class="title">{{ v.title }}</div>
          <div class="meta">{{ v.views }} views</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home { max-width: var(--max-width); margin: 0 auto; padding: 24px; }
h1 { margin-bottom: 16px; }
.feed { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.card { cursor: pointer; }
.thumbnail { background: var(--bg-elevated); aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; border-radius: 12px; }
.title { margin-top: 8px; font-weight: 500; }
.meta { color: var(--text-secondary); font-size: 12px; }
</style>