// The outbox: changes made while offline, kept in the browser's IndexedDB until sent.

const DB_NAME = "kxcompliance";
const STORE = "outbox";

function open() {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, 1);
		request.onupgradeneeded = () => {
			request.result.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
		};
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}

async function withStore(mode, work) {
	const db = await open();
	return new Promise((resolve, reject) => {
		const transaction = db.transaction(STORE, mode);
		const result = work(transaction.objectStore(STORE));
		transaction.oncomplete = () => resolve(result.result);
		transaction.onerror = () => reject(transaction.error);
	});
}

export const addEntry = (entry) => withStore("readwrite", (store) => store.add(entry));
export const putEntry = (entry) => withStore("readwrite", (store) => store.put(entry));
export const deleteEntry = (id) => withStore("readwrite", (store) => store.delete(id));
export const allEntries = () => withStore("readonly", (store) => store.getAll());
export const clearEntries = () => withStore("readwrite", (store) => store.clear());
