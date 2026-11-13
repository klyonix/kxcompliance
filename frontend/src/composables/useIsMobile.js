import { onBeforeUnmount, ref } from "vue";

// Phones get MobileShell and desks DesktopShell; frappe-ui treats them as two navigation models.
const QUERY = "(max-width: 639px)";

export function useIsMobile() {
	const media = window.matchMedia(QUERY);
	const isMobile = ref(media.matches);
	const update = (event) => (isMobile.value = event.matches);
	media.addEventListener("change", update);
	onBeforeUnmount(() => media.removeEventListener("change", update));
	return isMobile;
}
