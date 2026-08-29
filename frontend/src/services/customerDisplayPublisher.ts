import { watch } from "vue";
import { useCartStore } from "@/stores/cartStore";
import { usePosStore } from "@/stores/posStore";
import { createCustomerDisplayChannel, getCustomerDisplaySessionId, type CustomerDisplayState } from "./customerDisplayChannel";

type CustomerDisplayConfig = { enabled?: boolean; sessionId?: string };

export function startCustomerDisplayPublisher(): () => void {
	const cart = useCartStore();
	const pos = usePosStore();
	const customerDisplayCart = cart as typeof cart & { currency?: string };
	const customerDisplayPos = pos as typeof pos & { invoiceCurrency?: string };
	let changeAmount = 0;
	let sessionId = getCustomerDisplaySessionId();
	let channel = createCustomerDisplayChannel(sessionId);
	let lastCart: CustomerDisplayState | null = null;
	let paymentTimer: ReturnType<typeof setTimeout> | undefined;
	let showingPayment = false;
	let previousQuantities = new Map<string, number>();
	const isEnabled = () => localStorage.getItem("xpos.customerDisplay.enabled") !== "false";
	const sendIdle = () => channel?.postMessage({ type: "display-disabled" });
	const snapshot = (): CustomerDisplayState => {
		let highlightedItemKey: string | undefined;
		const items = cart.items.map((item, index) => {
			const lineKey = item.uid || `${item.item_code}:${item.rate}:${index}`;
			const discount = item.discount_amount || (item.rate * item.qty * item.discount_percentage) / 100;
			if (item.qty > (previousQuantities.get(lineKey) || 0)) highlightedItemKey = lineKey;
			const itemData = item as unknown as Record<string, unknown>;
			const attributes = itemData.attributes;
			const attributeLabels = attributes && typeof attributes === "object" && !Array.isArray(attributes)
				? Object.entries(attributes as Record<string, unknown>).flatMap(([name, value]) => typeof value === "string" && value.trim() ? [name.toLowerCase() === "size" ? `${name} ${value}` : value] : [])
				: [];
			const explicitVariant = [itemData.variant_name, itemData.variant].find((value): value is string => typeof value === "string" && value.trim().length > 0) || "";
			const variant = [explicitVariant, ...attributeLabels, item.uom || item.stock_uom].filter(Boolean).join(" · ");
			return { lineKey, name: item.item_name || item.item_code, variant: variant || undefined, quantity: item.qty, rate: item.rate, discount, amount: item.qty * item.rate - discount };
		});
		previousQuantities = new Map(items.map((item) => [item.lineKey, item.quantity]));
		const grossSubtotal = items.reduce((sum, item) => sum + item.rate * item.quantity, 0);
		const itemDiscount = items.reduce((sum, item) => sum + Math.abs(item.discount), 0);
		// Keep this calculation aligned with CartSummary.vue: a percentage-based
		// additional discount applies to the cart subtotal after item discounts.
		const additionalDiscount = cart.discountPercentage > 0
			? (cart.subtotal * cart.discountPercentage) / 100
			: Math.max(0, Number(cart.discountAmount) || 0);
		const tax = cart.taxAmount;
		const grandTotal = cart.grandTotal;
		return {
			mode: items.length ? "cart" : "idle",
			items,
			customerName: cart.customerName,
			subtotal: grossSubtotal,
			tax,
			itemDiscount,
			additionalDiscount,
			grandTotal,
			changeAmount,
			currency: customerDisplayCart.currency || customerDisplayPos.invoiceCurrency || "RM",
			highlightedItemKey,
			updatedAt: Date.now(),
		};
	};
	const publish = () => {
		if (showingPayment) return;
		lastCart = snapshot();
		if (!isEnabled()) { sendIdle(); return; }
		channel?.postMessage(lastCart);
	};
	const replaceChannel = (nextSessionId: string) => {
		if (nextSessionId === sessionId) return;
		channel?.close();
		sessionId = nextSessionId;
		channel = createCustomerDisplayChannel(sessionId);
		if (channel) channel.onmessage = (event: MessageEvent<{ type?: string }>) => { if (event.data?.type === "display-ready") publish(); };
	};
	const onConfig = (event: Event) => {
		const config = (event as CustomEvent<CustomerDisplayConfig>).detail || {};
		if (config.sessionId) replaceChannel(config.sessionId);
		publish();
	};
	const onChangeAmount = (event: Event) => {
		changeAmount = Math.max(0, Number((event as CustomEvent<{ amount?: number }>).detail?.amount) || 0);
		publish();
	};
	window.addEventListener("xpos:customer-display-change", onChangeAmount);
	const stopCart = watch(() => [cart.items, cart.customerName, cart.subtotal, cart.taxAmount, cart.grandTotal, cart.discountPercentage, cart.discountAmount], publish, { deep: true, immediate: true });
	const stopPayment = watch(() => pos.lastInvoiceName, (invoice) => {
		if (!invoice || !lastCart || !isEnabled() || localStorage.getItem("xpos.customerDisplay.paymentScreen") === "false") return;
		showingPayment = true;
		channel?.postMessage({ ...lastCart, mode: "payment", paymentStatus: "paid", updatedAt: Date.now() });
		if (paymentTimer) clearTimeout(paymentTimer);
		const delay = Math.max(5, Math.min(60, Number(localStorage.getItem("xpos.customerDisplay.returnDelay") || 10)));
		paymentTimer = setTimeout(() => { showingPayment = false; channel?.postMessage({ ...lastCart!, mode: "idle", items: [], updatedAt: Date.now() }); }, delay * 1000);
	});
	if (channel) channel.onmessage = (event: MessageEvent<{ type?: string }>) => { if (event.data?.type === "display-ready") publish(); };
	window.addEventListener("xpos:customer-display-config", onConfig);
	return () => { stopCart(); stopPayment(); if (paymentTimer) clearTimeout(paymentTimer); channel?.close(); window.removeEventListener("xpos:customer-display-change", onChangeAmount); window.removeEventListener("xpos:customer-display-config", onConfig); };
}
