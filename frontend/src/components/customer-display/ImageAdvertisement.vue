<template><img :src="src" :style="{ objectFit: advertisement.fit || 'contain' }" :alt="advertisement.title" /></template>
<script setup lang="ts">import type { Advertisement } from "@/composables/useAdvertisementPlaylist"; defineProps<{ advertisement: Advertisement; src: string }>();</script>
<style scoped>img{display:block;width:100%;height:100%;background:#160f1b}</style>
