// The client a firm's staff member has chosen to look at, or the company an organisation's people
// have, shared by every list and kept on this device (per site and person) until they clear it.
import { computed, reactive } from "vue";
import { call } from "@/api";
import { boot, checksOnly, isClientLogin } from "@/boot";
import { companiesOf, companyChosen } from "@/lib/clientFilter";

const KEY = `kxcompliance:${boot.siteName}:${boot.user}:client`;
const COMPANY_KEY = `kxcompliance:${boot.siteName}:${boot.user}:company`;

export const clientFilter = reactive({
	client: localStorage.getItem(KEY) || "",
	company: localStorage.getItem(COMPANY_KEY) || "",
	clients: [],
	loaded: false,
});

// Firm staff only: an organisation has no clients, and a client's own login sees one client.
export const filterOffered = () =>
	boot.accountType === "CA/CS Firm" && !isClientLogin() && !checksOnly();

// An organisation with more than one company narrows the app to one of them instead.
export const companyFilterOffered = () =>
	boot.accountType !== "CA/CS Firm" &&
	!isClientLogin() &&
	!checksOnly() &&
	boot.companies.length > 1;

// The chosen client's companies (or the organisation's one company), or null for all. Until the
// clients are loaded a client cannot be applied, so lists wait for them (see loadClients).
export const chosenCompanies = computed(() => {
	if (filterOffered()) return companiesOf(clientFilter.clients, clientFilter.client);
	if (companyFilterOffered()) return companyChosen(boot.companies, clientFilter.company);
	return null;
});

// The chosen client's name as people know it, for saying which client a page shows.
export const chosenClientName = computed(() => {
	const chosen = clientFilter.clients.find((row) => row.name === clientFilter.client);
	return chosen ? chosen.client_name || chosen.name : clientFilter.client;
});

export function chooseClient(name) {
	clientFilter.client = name || "";
	if (clientFilter.client) localStorage.setItem(KEY, clientFilter.client);
	else localStorage.removeItem(KEY);
}

export function chooseCompany(name) {
	clientFilter.company = name || "";
	if (clientFilter.company) localStorage.setItem(COMPANY_KEY, clientFilter.company);
	else localStorage.removeItem(COMPANY_KEY);
}

let loading;
export function loadClients() {
	if (!filterOffered()) return Promise.resolve();
	loading ??= call("kxcompliance.api.client_choices")
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
