import { onMounted, onUnmounted, ref } from "vue";
import {
	createCustomerDisplayChannel,
	getCustomerDisplaySessionId,
	type CustomerDisplayState,
} from "@/services/customerDisplayChannel";

export function useCustomerDisplay() {
	const state = ref<CustomerDisplayState>({
		mode: "idle",
		items: [],
		customerName: "",
		subtotal: 0,
		tax: 0,
		itemDiscount: 0,
		additionalDiscount: 0,
		grandTotal: 0,
		currency: "RM",
		updatedAt: 0,
	});
	const connected = ref(false);
	let channel: BroadcastChannel | null = null;

	onMounted(() => {
		channel = createCustomerDisplayChannel(getCustomerDisplaySessionId());
		if (!channel) return;
		connected.value = true;
		channel.onmessage = (event: MessageEvent<CustomerDisplayState | { type: string }>) => {
			if ("type" in event.data && event.data.type === "display-ping") { channel?.postMessage({ type: "display-ready" }); return; }
			if ("type" in event.data && event.data.type === "display-disabled") { state.value = { ...state.value, mode: "idle", items: [] }; return; }
			if (!("mode" in event.data) || !["idle", "cart", "payment"].includes(event.data.mode)) return;
			state.value = event.data;
		};
		channel.postMessage({ type: "display-ready" });
	});

	const notifyClosed = () => channel?.postMessage({ type: "display-closed" });
	onMounted(() => window.addEventListener("pagehide", notifyClosed));
	onUnmounted(() => { window.removeEventListener("pagehide", notifyClosed); notifyClosed(); channel?.close(); });

	return { state, connected };
}
