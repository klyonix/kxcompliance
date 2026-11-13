// A small client for Frappe's API that keeps what the server said when it refuses.

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

	// No answer from the server at all: the phone is offline or the site is unreachable.
	get isNetwork() {
		return this.status === 0;
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
	return send(url, init, fetcher);
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
	return send("/api/method/upload_file", init, fetcher);
}

async function send(url, init, fetcher) {
	let response;
	try {
		response = await fetcher(url, init);
	} catch {
		throw new ApiError("No connection", { status: 0 });
	}
	let body = {};
	try {
		body = await response.json();
	} catch {
		body = {};
	}
	if (!response.ok) {
		const message =
			plain(serverMessage(body)) ||
			body.exception ||
			response.statusText ||
			"The request failed";
		throw new ApiError(message, { status: response.status, excType: body.exc_type || "" });
	}
	return body.message;
}

export const saveChanges = (doctype, name, values, baseModified, options) =>
	call(
		"compliance_plus.api.save_changes",
		{ doctype, name, values, base_modified: baseModified },
		{ httpMethod: "POST", ...options }
	);
