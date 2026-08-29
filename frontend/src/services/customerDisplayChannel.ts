export type CustomerDisplayMode = "idle" | "cart" | "payment";

export interface CustomerDisplayItem {
	lineKey: string;
	name: string;
	variant?: string;
	quantity: number;
	rate: number;
	discount: number;
	amount: number;
}

export interface CustomerDisplayState {
	mode: CustomerDisplayMode;
	items: CustomerDisplayItem[];
	customerName: string;
	subtotal: number;
	tax: number;
	itemDiscount: number;
	additionalDiscount: number;
	grandTotal: number;
	changeAmount?: number;
	currency: string;
	highlightedItemKey?: string;
	paymentStatus?: "paid" | "pending";
	updatedAt: number;
}

const CACHE_NAME = "xpos-customer-display-media-v1";
const CHANNEL_PREFIX = "xpos-display-";

export function getCustomerDisplaySessionId(): string {
	const key = "xpos.customerDisplay.sessionId";
	const fromUrl = new URLSearchParams(location.search).get("session");
	if (fromUrl?.trim()) {
		localStorage.setItem(key, fromUrl.trim());
		return fromUrl.trim();
	}
	const existing = localStorage.getItem(key);
	if (existing) return existing;
	const generated = `${location.host}-${crypto.randomUUID()}`;
	localStorage.setItem(key, generated);
	return generated;
}

export function createCustomerDisplayChannel(sessionId = getCustomerDisplaySessionId()): BroadcastChannel | null {
	if (typeof BroadcastChannel === "undefined") return null;
	return new BroadcastChannel(`${CHANNEL_PREFIX}${sessionId}`);
}

export function mediaCacheKey(url: string): string {
	return `${location.origin}${url.startsWith("/") ? url : `/${url}`}`;
}

export async function cacheAdvertisementFile(url: string): Promise<boolean> {
	if (!url || typeof caches === "undefined") return false;
	try {
		const cache = await caches.open(CACHE_NAME);
		const request = new Request(mediaCacheKey(url), { credentials: "same-origin" });
		if (!(await cache.match(request))) await cache.add(request);
		return true;
	} catch (error) {
		console.warn("[XPOS] Customer advertisement cache failed", error);
		return false;
	}
}

export async function getCachedAdvertisementUrl(url: string): Promise<string> {
	if (!url || typeof caches === "undefined") return url;
	try {
		const response = await (await caches.open(CACHE_NAME)).match(mediaCacheKey(url));
		return response ? URL.createObjectURL(await response.blob()) : url;
	} catch {
		return url;
	}
}

export async function getAdvertisementCacheStatus(urls: string[]): Promise<{ downloaded: number; total: number }> {
	if (typeof caches === "undefined") return { downloaded: 0, total: urls.length };
	const cache = await caches.open(CACHE_NAME);
	let downloaded = 0;
	for (const url of urls) if (await cache.match(mediaCacheKey(url))) downloaded += 1;
	return { downloaded, total: urls.length };
}
