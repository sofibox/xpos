import { computed, ref, watch } from "vue";

/** Per-tab seller preference. Document attribution never changes the next-sale default. */
export function useSalesPersonSelection(
    context: () => string,
    enabled: () => boolean,
    allowed: () => string[],
) {
    const selected = ref("");
    const remembered = ref("");
    let documentSelection = false;
    const salesPerson = computed({
        get: () => selected.value,
        set: (value: string) => {
            selected.value = value;
            if (!documentSelection) remembered.value = enabled() ? value : "";
        },
    });
    function resetSession() {
        remembered.value = "";
        selected.value = "";
        documentSelection = false;
    }
    function newSale() {
        documentSelection = false;
        selected.value = enabled() && allowed().includes(remembered.value) ? remembered.value : "";
    }
    function loadDocument(seller?: string | null) {
        documentSelection = true;
        selected.value = seller || "";
    }
    watch(context, resetSession, { flush: "sync" });
    watch(enabled, (value) => { if (!value) remembered.value = ""; }, { flush: "sync" });
    watch(allowed, (names) => {
        if (!names.includes(remembered.value)) remembered.value = "";
        if (!documentSelection && !names.includes(selected.value)) selected.value = "";
    }, { flush: "sync" });
    return { salesPerson, newSale, loadDocument, resetSession };
}
