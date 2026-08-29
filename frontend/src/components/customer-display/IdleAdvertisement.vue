<template>
	<section class="idle-advertisement" aria-label="Advertisement">
		<div v-if="previewId" class="preview-badge">Preview mode</div>
		<Transition name="advertisement-slide" mode="out-in"><div v-if="current" :key="current.id" class="advertisement-stage"><VideoAdvertisement v-if="current.type === 'video'" :advertisement="current" :src="currentUrl" @ended="next" /><ImageAdvertisement v-else-if="current.type === 'image'" :advertisement="current" :src="currentUrl" @ended="next" /><HtmlAdvertisement v-else :advertisement="current" @ended="next" /></div><div v-else key="welcome" class="welcome"><img v-if="companyLogo" :src="companyLogo" alt="Company logo" /><p>{{ language === "ms" ? "SELAMAT DATANG KE" : "WELCOME TO" }}</p><h1>LOZIRA</h1><span>COLLECTION</span><small>{{ language === "ms" ? "Gaya anda, direka indah" : "Your style, beautifully made" }}</small></div></Transition>
		<nav v-if="available.length > 1 && !previewId" class="slide-navigation" :aria-label="language === 'ms' ? 'Navigasi iklan' : 'Advertisement navigation'"><button type="button" :aria-label="language === 'ms' ? 'Iklan sebelumnya' : 'Previous advertisement'" @click="previous"><ChevronLeft /></button><div class="dots"><button v-for="(advertisement, index) in available" :key="advertisement.id" type="button" :class="{ active: index === currentIndex }" :aria-label="`${language === 'ms' ? 'Papar iklan' : 'Show advertisement'} ${index + 1}`" @click="goTo(index)"></button></div><button type="button" :aria-label="language === 'ms' ? 'Iklan seterusnya' : 'Next advertisement'" @click="next"><ChevronRight /></button></nav>
	</section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { ChevronLeft, ChevronRight } from "lucide-vue-next";
import ImageAdvertisement from "./ImageAdvertisement.vue";
import VideoAdvertisement from "./VideoAdvertisement.vue";
import HtmlAdvertisement from "./HtmlAdvertisement.vue";
import { useAdvertisementPlaylist } from "@/composables/useAdvertisementPlaylist";
const props = defineProps<{ language: "en" | "ms"; previewId?: string }>();
const companyLogo = ref(localStorage.getItem("xpos.customerDisplay.companyLogo") || "");
const { available, current, currentIndex, currentUrl, goTo, next, previous, cacheAll } = useAdvertisementPlaylist(props.previewId);
let timer: ReturnType<typeof setTimeout> | undefined;
watch(current, (ad) => { if (timer) clearTimeout(timer); if (ad && !props.previewId) timer = setTimeout(next, Math.max(3, ad.duration) * 1000); }, { immediate: true });
const onStorage = (event: StorageEvent) => { if (event.key === "xpos.customerDisplay.companyLogo") companyLogo.value = event.newValue || ""; };
window.addEventListener("storage", onStorage);
onBeforeUnmount(() => { if (timer) clearTimeout(timer); window.removeEventListener("storage", onStorage); });
cacheAll().catch(() => {});
</script>

<style scoped>
.idle-advertisement{position:relative;width:100%;height:100%;overflow:hidden;background:#160f1b}.advertisement-stage{width:100%;height:100%}.preview-badge{position:absolute;z-index:3;top:1rem;right:1rem;border-radius:999px;background:#fff;color:#211923;padding:.35rem .7rem;font-size:.75rem;font-weight:700}.welcome{height:100%;display:grid;place-items:center;align-content:center;gap:.5rem;color:#fff;text-align:center}.welcome img{max-width:11rem;max-height:5rem;object-fit:contain;margin-bottom:1rem}.welcome p,.welcome h1,.welcome span,.welcome small{margin:0}.slide-navigation{position:absolute;z-index:2;right:1rem;bottom:1rem;left:1rem;display:flex;align-items:center;justify-content:center;gap:.65rem;opacity:.68;transition:opacity .2s ease}.idle-advertisement:hover .slide-navigation,.slide-navigation:focus-within{opacity:1}.slide-navigation button{display:grid;place-items:center;width:2rem;height:2rem;border:1px solid rgb(255 255 255/.42);border-radius:999px;background:rgb(15 23 42/.54);color:#fff;cursor:pointer;backdrop-filter:blur(5px)}.slide-navigation button:hover,.slide-navigation button:focus-visible{border-color:#fbbf24;background:rgb(15 23 42/.82);outline:none}.slide-navigation svg{width:1rem;height:1rem}.dots{display:flex;gap:.45rem}.dots button{width:.65rem;height:.65rem;padding:0;background:rgb(255 255 255/.5)}.dots button.active{width:1.45rem;border-color:#fff;background:#fff}.advertisement-slide-enter-active,.advertisement-slide-leave-active{transition:opacity .42s ease,transform .42s cubic-bezier(.22,1,.36,1)}.advertisement-slide-enter-from{opacity:0;transform:translateX(2.25rem) scale(1.015)}.advertisement-slide-leave-to{opacity:0;transform:translateX(-2.25rem) scale(.985)}
</style>
