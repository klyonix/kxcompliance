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

// With `full`, the answer's message and the titles Frappe sends for Link values ("Doctype::name").
export async function call(
	method,
	params = {},
	{ httpMethod = "GET", fetcher = fetch, full = false } = {}
) {
	const headers = { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" };
	let url = `/api/method/${method}`;
	const init = { method: httpMethod, headers, credentials: "same-origin" };
	if (httpMethod === "GET") {
		// A value not set is left out, not sent as the text "undefined".
		const query = new URLSearchParams(
			Object.entries(params)
				.filter(([, value]) => value !== undefined)
				.map(([key, value]) => [
					key,
					typeof value === "string" ? value : JSON.stringify(value),
				])
		).toString();
		if (query) url += `?${query}`;
	} else {
		headers["Content-Type"] = "application/json";
		init.body = JSON.stringify(params);
	}
	const body = await send(url, init, fetcher);
	return full ? { message: body.message, linkTitles: body._link_titles || {} } : body.message;
}

// Files are private unless asked otherwise (an app logo has to be public, for instance).
export async function upload(
	file,
	{ doctype, docname, fileName, isPrivate = true, fetcher = fetch }
) {
	const form = new FormData();
	form.append("file", file, fileName || file.name || "upload");
	form.append("doctype", doctype);
	form.append("docname", docname);
	form.append("is_private", isPrivate ? "1" : "0");
	const init = {
		method: "POST",
		headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" },
		credentials: "same-origin",
		body: form,
	};
	return (await sendFile("/api/method/upload_file", init, fetcher, file)).message;
}

// A file the server fails on with no word of why is almost always one it cannot read.
async function sendFile(url, init, fetcher, file) {
	try {
		return await send(url, init, fetcher);
	} catch (err) {
		if (err.status === 413) {
			throw new ApiError(`${file.name || "This file"} is too large to upload.`, err);
		}
		if (err.status >= 500 && err.message === SERVER_FAILED) {
			throw new ApiError(
				`The server could not read ${
					file.name || "this file"
				}. Check that it opens on your device and is a PDF, image, spreadsheet or document, then upload it again.`,
				err
			);
		}
		throw err;
	}
}

// Upload a file to one of the app's own upload methods, with the record it is for.
async function uploadTo(method, fields, file, fetcher) {
	const form = new FormData();
	form.append("file", file, file.name || "upload");
	for (const [key, value] of Object.entries(fields)) form.append(key, value);
	const init = {
		method: "POST",
		headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" },
		credentials: "same-origin",
		body: form,
	};
	return (await sendFile(`/api/method/${method}`, init, fetcher, file)).message;
}

// A client's login adds a document to one of its filings (it cannot change the filing itself).
export const uploadClientDocument = (file, task, { fetcher = fetch } = {}) =>
	uploadTo("kxcompliance.api.add_client_document", { task }, file, fetcher);

// What a document request asks for, from the client (or from the firm, received another way).
export const uploadRequestDocument = (file, request, { fetcher = fetch } = {}) =>
	uploadTo("kxcompliance.api.add_request_document", { request }, file, fetcher);

const SERVER_FAILED = "The server could not complete this. Try again, or tell your administrator.";

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
				? SERVER_FAILED
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
		"kxcompliance.api.save_changes",
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

// Change fields of a record, with the same permissions and rules as the Desk.
export async function updateDoc(doctype, name, values, { fetcher = fetch } = {}) {
	return (await send(documentPath(doctype, name), json("PUT", values), fetcher)).data;
}

// Delete a record, with the same permissions as the Desk.
export async function deleteDoc(doctype, name, { fetcher = fetch } = {}) {
	await send(documentPath(doctype, name), json("DELETE"), fetcher);
}

// A document method that only reads, called with GET as the server requires.
export async function readMethod(doctype, name, method, { fetcher = fetch } = {}) {
	return (await send(`${documentPath(doctype, name)}method/${method}/`, json("GET"), fetcher))
		.data;
}

export async function runMethod(doctype, name, method, args = {}, { fetcher = fetch } = {}) {
	return (
		await send(`${documentPath(doctype, name)}method/${method}/`, json("POST", args), fetcher)
	).data;
}
