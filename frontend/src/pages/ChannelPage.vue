<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <div class="channel">
    <h1>Channel: {{ route.params.id }}</h1>
    <p>Videos and playlists will appear here.</p>
  </div>
</template>

<style scoped>
.channel { max-width: var(--max-width); margin: 0 auto; padding: 24px; }
</style>