import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
	cacheAdvertisementFile,
	getCustomerDisplaySessionId,
	getAdvertisementCacheStatus,
	getCachedAdvertisementUrl,
} from "@/services/customerDisplayChannel";
import {
	applyLocalCustomerDisplayConfiguration,
	CUSTOMER_DISPLAY_SAVED_SETUP_KEY,
	loadCustomerDisplayConfiguration,
	readLocalCustomerDisplayConfiguration,
	saveCustomerDisplayConfiguration,
} from "@/services/customerDisplayStorage";

export type Advertisement = {
	id: string;
	title: string;
	type: "image" | "video" | "html";
	file: string;
	duration: number;
	order: number;
	enabled: boolean;
	startDate?: string;
	endDate?: string;
	content?: string;
	loop?: boolean;
	fit?: "contain" | "cover" | "fill";
};

const DEFAULT_PLAYLIST: Advertisement[] = [];
export const PLAYLIST_KEY = "xpos.customerDisplay.playlist";

export function isAdvertisementActive(ad: Advertisement, now = new Date()): boolean {
	return ad.enabled && (!ad.startDate || new Date(ad.startDate) <= now) && (!ad.endDate || new Date(ad.endDate) >= now);
}

export function useAdvertisementPlaylist(previewId = "") {
	const playlist = ref<Advertisement[]>(loadPlaylist());
	const now = ref(Date.now());
	const currentIndex = ref(0);
	const currentUrl = ref("");
	const cacheStatus = ref({ downloaded: 0, total: 0 });
	const available = computed(() => {
		const currentTime = new Date(now.value);
		return playlist.value.filter((ad) => isAdvertisementActive(ad, currentTime)).sort((a, b) => a.order - b.order);
	});
	const current = computed(() => previewId ? playlist.value.find((ad) => ad.id === previewId) : available.value[currentIndex.value % Math.max(available.value.length, 1)]);
	watch(current, () => { void resolveCurrentUrl(); });

	let scheduleTimer: number | undefined;
	onMounted(async () => {
		window.addEventListener("storage", syncPlaylist);
		window.addEventListener("xpos:customer-display-storage", refreshLocalPlaylist);
		// Scheduled entries must react while the display remains open. localStorage
		// only notifies cross-window edits; passing time itself needs a reactive tick.
		scheduleTimer = window.setInterval(() => { now.value = Date.now(); }, 1000);
		await restoreServerPlaylist();
		await refreshCacheStatus();
		await resolveCurrentUrl();
	});
	onBeforeUnmount(() => {
		window.removeEventListener("storage", syncPlaylist);
		window.removeEventListener("xpos:customer-display-storage", refreshLocalPlaylist);
		if (scheduleTimer) window.clearInterval(scheduleTimer);
	});

	function syncPlaylist(event: StorageEvent) {
		if (event.key !== PLAYLIST_KEY) return;
		playlist.value = loadPlaylist();
		currentIndex.value = 0;
		void refreshCacheStatus();
		void resolveCurrentUrl();
	}

	function refreshLocalPlaylist() {
		playlist.value = loadPlaylist();
		currentIndex.value = 0;
		void refreshCacheStatus();
		void resolveCurrentUrl();
	}

	async function resolveCurrentUrl() {
		if (!current.value || current.value.type === "html") {
			currentUrl.value = "";
			return;
		}
		currentUrl.value = await getCachedAdvertisementUrl(current.value.file);
	}

	async function refreshCacheStatus() {
		cacheStatus.value = await getAdvertisementCacheStatus(
			available.value.filter((ad) => ad.type !== "html").map((ad) => ad.file),
		);
	}

	async function cacheAll(): Promise<void> {
		await Promise.all(available.value.filter((ad) => ad.type !== "html").map((ad) => cacheAdvertisementFile(ad.file)));
		await refreshCacheStatus();
	}

	async function restoreServerPlaylist(): Promise<void> {
		try {
			const configuration = await loadCustomerDisplayConfiguration(getCustomerDisplaySessionId());
			if (!configuration) return;
			applyLocalCustomerDisplayConfiguration(configuration);
			if (Array.isArray(configuration.playlist)) {
				playlist.value = configuration.playlist as Advertisement[];
				localStorage.setItem(PLAYLIST_KEY, JSON.stringify(playlist.value));
			}
		} catch (error) {
			console.info("[XPOS] Customer Display server restore unavailable; using local offline copy", error);
		}
	}

	function goTo(index: number): void {
		if (previewId || available.value.length < 2) return;
		const length = available.value.length;
		currentIndex.value = ((index % length) + length) % length;
	}

	function next(): void { goTo(currentIndex.value + 1); }
	function previous(): void { goTo(currentIndex.value - 1); }

	return { playlist, available, current, currentIndex, currentUrl, cacheStatus, cacheAll, goTo, next, previous };
}

export function saveAdvertisementPlaylist(playlist: Advertisement[]): void {
	localStorage.setItem(PLAYLIST_KEY, JSON.stringify(playlist));
	const terminalId = getCustomerDisplaySessionId();
	if (localStorage.getItem(CUSTOMER_DISPLAY_SAVED_SETUP_KEY) !== terminalId) return;
	void saveCustomerDisplayConfiguration(
		terminalId,
		readLocalCustomerDisplayConfiguration(playlist),
	).catch((error) => console.info("[XPOS] Customer Display playlist remains in local offline storage", error));
}

function loadPlaylist(): Advertisement[] {
	try {
		const value = JSON.parse(localStorage.getItem(PLAYLIST_KEY) || "null");
		return Array.isArray(value) ? value : DEFAULT_PLAYLIST;
	} catch {
		return DEFAULT_PLAYLIST;
	}
}
