// A small client for Frappe's API that keeps what the server said when it refuses.
import { GATEWAY_STATUSES, noteNoResponse, noteResponse } from "@/offline/reachability";

export class ApiError extends Error {
	constructor(message, { status = 0, excType = "" } = {}) {
		super(message);
		this.name = "ApiError";
		this.status = status;
		this.excType = excType;
	}

	get isConflict() {
		return this.excType === "TimestampMismatchError";
	}

	// No answer from the server: the phone is offline, the site is unreachable, or the gateway
	// in front of it says the app server behind it did not answer.
	get isNetwork() {
		return this.status === 0 || GATEWAY_STATUSES.includes(this.status);
	}
}

function serverMessage(body) {
	try {
		const messages = JSON.parse(body._server_messages || "[]");
		return messages.map((entry) => JSON.parse(entry).message).join("\n");
	} catch {
		return "";
	}
}

function plain(html) {
	const element = document.createElement("div");
	element.innerHTML = html;
	return element.textContent || "";
}

export async function call(method, params = {}, { httpMethod = "GET", fetcher = fetch } = {}) {
	const headers = { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" };
	let url = `/api/method/${method}`;
	const init = { method: httpMethod, headers, credentials: "same-origin" };
	if (httpMethod === "GET") {
		const query = new URLSearchParams(
			Object.entries(params).map(([key, value]) => [
				key,
				typeof value === "string" ? value : JSON.stringify(value),
			])
		).toString();
		if (query) url += `?${query}`;
	} else {
		headers["Content-Type"] = "application/json";
		init.body = JSON.stringify(params);
	}
	return (await send(url, init, fetcher)).message;
}

export async function upload(file, { doctype, docname, fileName, fetcher = fetch }) {
	const form = new FormData();
	form.append("file", file, fileName || file.name || "upload");
	form.append("doctype", doctype);
	form.append("docname", docname);
	form.append("is_private", "1");
	const init = {
		method: "POST",
		headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" },
		credentials: "same-origin",
		body: form,
	};
	return (await send("/api/method/upload_file", init, fetcher)).message;
}

async function send(url, init, fetcher) {
	let response;
	try {
		response = await fetcher(url, init);
	} catch {
		noteNoResponse();
		throw new ApiError("No connection", { status: 0 });
	}
	// The service worker marks a read it answered from its saved copy.
	noteResponse({
		status: response.status,
		fromCache: Boolean(response.headers?.get?.("X-Served-From")),
	});
	if (GATEWAY_STATUSES.includes(response.status)) {
		throw new ApiError("The server is not answering", { status: response.status });
	}
	let body = {};
	try {
		body = await response.json();
	} catch {
		body = {};
	}
	if (!response.ok) {
		// Version 1 answers carry _server_messages and exc_type; version 2 an errors list.
		const v2Error = (body.errors || [])[0] || {};
		const message =
			plain(serverMessage(body)) ||
			plain(v2Error.message || "") ||
			// Frappe's raw exception text is for the Error Log, not for people.
			(response.status >= 500
				? "The server could not complete this. Try again, or tell your administrator."
				: "This could not be saved. Check the details and try again.");
		throw new ApiError(message, {
			status: response.status,
			excType: body.exc_type || v2Error.type || "",
		});
	}
	return body;
}

export const saveChanges = (doctype, name, values, baseModified, options) =>
	call(
		"compliance_plus.api.save_changes",
		{ doctype, name, values, base_modified: baseModified },
		{ httpMethod: "POST", ...options }
	);

// Frappe's version 2 REST API, which applies the same permissions as the Desk.
const json = (method, body) => ({
	method,
	headers: {
		Accept: "application/json",
		"Content-Type": "application/json",
		"X-Frappe-CSRF-Token": window.csrf_token || "",
	},
	credentials: "same-origin",
	body: body === undefined ? undefined : JSON.stringify(body),
});

const documentPath = (doctype, name) =>
	`/api/v2/document/${encodeURIComponent(doctype)}` +
	(name ? `/${encodeURIComponent(name)}/` : "");

export async function getList(
	doctype,
	{ fields, filters, orderBy, start = 0, limit = 20, fetcher = fetch } = {}
) {
	const query = new URLSearchParams({ start: String(start), limit: String(limit) });
	if (fields) query.set("fields", JSON.stringify(fields));
	if (filters) query.set("filters", JSON.stringify(filters));
	if (orderBy) query.set("order_by", orderBy);
	const body = await send(`${documentPath(doctype)}?${query}`, json("GET"), fetcher);
	return { rows: body.data || [], hasMore: Boolean(body.has_next_page) };
}

export async function getDoc(doctype, name, { fetcher = fetch } = {}) {
	return (await send(documentPath(doctype, name), json("GET"), fetcher)).data;
}

export async function createDoc(doctype, values, { fetcher = fetch } = {}) {
	return (await send(documentPath(doctype), json("POST", values), fetcher)).data;
}

export async function runMethod(doctype, name, method, args = {}, { fetcher = fetch } = {}) {
	return (
		await send(`${documentPath(doctype, name)}method/${method}/`, json("POST", args), fetcher)
	).data;
}
