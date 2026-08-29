<template><video :src="src" autoplay muted :loop="advertisement.loop === true" playsinline :style="{ objectFit: advertisement.fit || 'contain' }" :aria-label="advertisement.title" @ended="$emit('ended')" /></template>
<script setup lang="ts">import type { Advertisement } from "@/composables/useAdvertisementPlaylist"; defineProps<{ advertisement: Advertisement; src: string }>(); defineEmits<{ ended: [] }>();</script>
<style scoped>video{display:block;width:100%;height:100%;background:#160f1b}</style>
