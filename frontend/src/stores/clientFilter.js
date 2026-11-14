// The client a firm's staff member has chosen to look at, shared by every list and kept on this
// device (per site and person) until they clear it.
import { computed, reactive } from "vue";
import { call } from "@/api";
import { boot, checksOnly, isClientLogin } from "@/boot";
import { companiesOf } from "@/lib/clientFilter";

const KEY = `compliance-plus:${boot.siteName}:${boot.user}:client`;

export const clientFilter = reactive({
	client: localStorage.getItem(KEY) || "",
	clients: [],
	loaded: false,
});

// Firm staff only: an organisation has no clients, and a client's own login sees one client.
export const filterOffered = () =>
	boot.accountType === "CA/CS Firm" && !isClientLogin() && !checksOnly();

// The chosen client's companies, or null for every client. Until the clients are loaded the
// choice cannot be applied, so lists wait for them (see loadClients).
export const chosenCompanies = computed(() =>
	filterOffered() ? companiesOf(clientFilter.clients, clientFilter.client) : null
);

export function chooseClient(name) {
	clientFilter.client = name || "";
	if (clientFilter.client) localStorage.setItem(KEY, clientFilter.client);
	else localStorage.removeItem(KEY);
}

let loading;
export function loadClients() {
	if (!filterOffered()) return Promise.resolve();
	loading ??= call("compliance_plus.api.client_choices")
		.then((clients) => {
			clientFilter.clients = clients;
			// A client no longer offered (left the firm, or the team changed) is let go.
			if (clientFilter.client && !clients.some((row) => row.name === clientFilter.client)) {
				chooseClient("");
			}
		})
		.catch(() => {
			// Offline or refused: the lists show every client, and the choice is kept for later.
			loading = undefined;
		})
		.finally(() => {
			clientFilter.loaded = true;
		});
	return loading;
}
