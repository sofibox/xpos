export type CustomerDisplayConfiguration = {
	settings: Record<string, string>;
	playlist: unknown[];
};

export type CustomerDisplaySetup = { terminal_id: string; modified: string };
export type CustomerDisplayAssetCheck = { url: string; status: "available" | "missing" | "external" | "unavailable" };

export const CUSTOMER_DISPLAY_PREFIX = "xpos.customerDisplay.";
export const CUSTOMER_DISPLAY_SAVED_SETUP_KEY = `${CUSTOMER_DISPLAY_PREFIX}savedSetup`;
export const CUSTOMER_DISPLAY_SETTING_KEYS = [
	"enabled",
	"sessionId",
	"returnDelay",
	"activeMedia",
	"receiptWidth",
	"showChange",
	"paymentScreen",
	"paymentContent",
	"companyLogo",
	"language",
] as const;

function csrfToken(): string {
	return window.xpos?.csrf_token || (document.querySelector('meta[name="csrf-token"]') as HTMLMetaElement | null)?.content || "";
}

async function call(method: string, args: Record<string, unknown>): Promise<unknown> {
	const csrf = csrfToken();
	const response = await fetch(`/api/method/${method}`, {
		method: "POST",
		credentials: "same-origin",
		headers: { "Content-Type": "application/json", ...(csrf ? { "X-Frappe-CSRF-Token": csrf } : {}) },
		body: JSON.stringify(args),
	});
	const data = await response.json().catch(() => ({}));
	if (!response.ok || data.exc) throw new Error(data._server_messages || "Customer Display server storage is unavailable");
	return data.message;
}

export function readLocalCustomerDisplayConfiguration(playlist: unknown[] = []): CustomerDisplayConfiguration {
	const settings: Record<string, string> = {};
	for (const key of CUSTOMER_DISPLAY_SETTING_KEYS) {
		const value = localStorage.getItem(`${CUSTOMER_DISPLAY_PREFIX}${key}`);
		if (value !== null) settings[key] = value;
	}
	return { settings, playlist };
}

export function applyLocalCustomerDisplayConfiguration(configuration: CustomerDisplayConfiguration): void {
	for (const key of CUSTOMER_DISPLAY_SETTING_KEYS) {
		const value = configuration.settings?.[key];
		if (typeof value === "string") localStorage.setItem(`${CUSTOMER_DISPLAY_PREFIX}${key}`, value);
	}
}

export async function loadCustomerDisplayConfiguration(terminalId: string): Promise<CustomerDisplayConfiguration | null> {
	const message = await call("xpos.api.customer_display.get_configuration", { terminal_id: terminalId }) as { configuration?: CustomerDisplayConfiguration | null };
	return message.configuration || null;
}

export async function listCustomerDisplayConfigurations(): Promise<CustomerDisplaySetup[]> {
	const message = await call("xpos.api.customer_display.list_configurations", {}) as CustomerDisplaySetup[];
	return Array.isArray(message) ? message : [];
}

export async function deleteCustomerDisplayConfiguration(terminalId: string): Promise<void> {
	await call("xpos.api.customer_display.delete_configuration", { terminal_id: terminalId });
}

export async function checkCustomerDisplayAssets(fileUrls: string[]): Promise<CustomerDisplayAssetCheck[]> {
	const message = await call("xpos.api.customer_display.check_assets", { file_urls: JSON.stringify(fileUrls) }) as CustomerDisplayAssetCheck[];
	return Array.isArray(message) ? message : [];
}

export async function checkCustomerDisplayMedia(urls: string[]): Promise<CustomerDisplayAssetCheck[]> {
	const uploaded = urls.filter((url) => new URL(url, window.location.origin).origin === window.location.origin && new URL(url, window.location.origin).pathname.startsWith("/files/"));
	const external = urls.filter((url) => !uploaded.includes(url));
	const checkedExternal = await Promise.all(external.map(async (url) => { try { let response = await fetch(url, { method: "HEAD", mode: "cors", credentials: "omit" }); if (response.status === 405) response = await fetch(url, { method: "GET", mode: "cors", credentials: "omit", headers: { Range: "bytes=0-0" } }); return { url, status: response.ok ? "available" : "unavailable" } as CustomerDisplayAssetCheck; } catch { return { url, status: "unavailable" } as CustomerDisplayAssetCheck; } }));
	return [...await checkCustomerDisplayAssets(uploaded), ...checkedExternal];
}

export async function saveCustomerDisplayConfiguration(terminalId: string, configuration: CustomerDisplayConfiguration): Promise<void> {
	await call("xpos.api.customer_display.save_configuration", {
		terminal_id: terminalId,
		configuration: JSON.stringify(configuration),
	});
}

export async function createCustomerDisplayConfiguration(terminalId: string, configuration: CustomerDisplayConfiguration): Promise<void> {
	await call("xpos.api.customer_display.create_configuration", {
		terminal_id: terminalId,
		configuration: JSON.stringify(configuration),
	});
}
