// Sending changes: straight away when online, through the outbox when not.
import { ApiError, saveChanges, upload } from "@/api";
import { addEntry, allEntries, deleteEntry, putEntry } from "./db";

// A change: { doctype, name, values, baseModified, files: [{ field, blob, fileName }] }
// Files are kept as their bytes, type and name: storing raw bytes works in every browser's
// IndexedDB, where a stored Blob has not always survived.
export async function enqueue(change) {
	const files = await Promise.all(
		(change.files || []).map(async (file) => ({
			field: file.field,
			fileName: file.fileName,
			type: file.blob.type,
			bytes: await file.blob.arrayBuffer(),
		}))
	);
	return addEntry({ ...change, files, status: "waiting", error: "", createdAt: Date.now() });
}

const asBlob = (file) => file.blob || new Blob([file.bytes], { type: file.type });

export async function entries() {
	const all = await allEntries();
	return all.sort((a, b) => a.id - b.id);
}

// Send one change: its files first, then the save that names them.
export async function sendChange(change, { fetcher } = {}) {
	const values = { ...change.values };
	for (const file of change.files || []) {
		const uploaded = await upload(asBlob(file), {
			doctype: change.doctype,
			docname: change.name,
			fileName: file.fileName,
			fetcher,
		});
		values[file.field] = uploaded.file_url;
	}
	return saveChanges(change.doctype, change.name, values, change.baseModified, { fetcher });
}

// Try now; keep it for later only when there is no connection.
export async function submit(change, options = {}) {
	try {
		return { queued: false, result: await sendChange(change, options) };
	} catch (error) {
		if (error instanceof ApiError && error.isNetwork) {
			await enqueue(change);
			return { queued: true };
		}
		throw error;
	}
}

// Send what is waiting, oldest first. Stops at the first lost connection so order is kept.
export async function flush(options = {}) {
	const summary = { sent: 0, conflicts: 0, failed: 0, stoppedOffline: false };
	for (const entry of await entries()) {
		if (entry.status !== "waiting") continue;
		try {
			await sendChange(entry, options);
			await deleteEntry(entry.id);
			summary.sent += 1;
		} catch (error) {
			if (error instanceof ApiError && error.isNetwork) {
				summary.stoppedOffline = true;
				break;
			}
			const status = error instanceof ApiError && error.isConflict ? "conflict" : "failed";
			await putEntry({ ...entry, status, error: error.message });
			summary[status === "conflict" ? "conflicts" : "failed"] += 1;
		}
	}
	return summary;
}

// Put a change that needed a second look back in line, or drop it.
export async function retry(entry, baseModified) {
	return putEntry({ ...entry, status: "waiting", error: "", baseModified });
}

export const discard = (entry) => deleteEntry(entry.id);
