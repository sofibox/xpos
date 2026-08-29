<template><iframe :title="advertisement.title" sandbox="allow-same-origin" scrolling="no" :srcdoc="safeHtml" /></template>
<script setup lang="ts">
import { computed } from "vue";
import type { Advertisement } from "@/composables/useAdvertisementPlaylist";
const props = defineProps<{ advertisement: Advertisement }>();
const safeHtml = computed(() => sanitize(props.advertisement.content || ""));
function sanitize(input: string): string {
	const doc = new DOMParser().parseFromString(input, "text/html");
	const allowed = new Set(["DIV", "H1", "H2", "H3", "P", "SPAN", "STRONG", "EM", "BR", "IMG"]);
	doc.body.querySelectorAll("*").forEach((node) => {
		if (!allowed.has(node.tagName)) { node.replaceWith(...Array.from(node.childNodes)); return; }
		Array.from(node.attributes).forEach((attribute) => {
			if (attribute.name !== "alt" && !(node.tagName === "IMG" && attribute.name === "src" && /^(https?:|blob:|data:image\/(png|jpeg|webp);)/i.test(attribute.value))) node.removeAttribute(attribute.name);
		});
	});
	return `<!doctype html><html><head><meta charset="utf-8"><style>html,body{width:100%;height:100%;margin:0;overflow:hidden}body{display:grid;place-items:center;background:#160f1b;color:white;font:clamp(1rem,4vw,4rem) sans-serif;text-align:center}img{display:block;max-width:100%;max-height:100%;object-fit:contain}</style></head><body>${doc.body.innerHTML}</body></html>`;
}
</script>
<style scoped>iframe{display:block;border:0;width:100%;height:100%;overflow:hidden;background:#160f1b}</style>
