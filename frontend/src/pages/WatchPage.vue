<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <div class="watch">
    <div class="player">Video Player Placeholder (ID: {{ route.params.id }})</div>
    <h2>Video Title</h2>
    <p>Description...</p>
  </div>
</template>

<style scoped>
.watch { max-width: 1200px; margin: 0 auto; padding: 24px; }
.player { background: var(--bg-elevated); aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; border-radius: 12px; }
h2 { margin-top: 16px; }
</style>