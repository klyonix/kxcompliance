// Paging a list: how many rows a page holds (20, 50 or 100, as Frappe's Desk offers its own),
// which rows a page shows, the page numbers to offer, and the size a person chose for each list,
// kept on this device.
export const PAGE_SIZES = [20, 50, 100];
export const DEFAULT_PAGE_SIZE = 20;

const sizeKey = (list) => `kxcompliance:page-size:${list}`;

export function savedPageSize(list, storage = globalThis.localStorage) {
	try {
		const size = Number(storage?.getItem(sizeKey(list)));
		return PAGE_SIZES.includes(size) ? size : DEFAULT_PAGE_SIZE;
	} catch {
		return DEFAULT_PAGE_SIZE;
	}
}

export function savePageSize(list, size, storage = globalThis.localStorage) {
	if (!PAGE_SIZES.includes(size)) return;
	try {
		storage?.setItem(sizeKey(list), String(size));
	} catch {
		// Private browsing or a full store: the size lasts until the page is left.
	}
}

export const pageCount = (total, size) => Math.max(1, Math.ceil((total || 0) / size));

// The first and last row of a page, counted from 1; {0, 0} when there is nothing.
export function pageRange(page, size, total) {
	if (!total) return { from: 0, to: 0 };
	const from = (page - 1) * size + 1;
	return { from, to: Math.min(page * size, total) };
}

const fill = (phrase, ...args) => phrase.replace(/\{(\d+)\}/g, (_match, index) => args[index]);

// "Showing 21–40 of 154", or what an empty or one-page list says; `translate` is i18n's t.
export function rangeLine(page, size, total, translate = fill) {
	if (!total) return translate("No records");
	if (total === 1) return translate("1 record");
	const { from, to } = pageRange(page, size, total);
	return from === 1 && to === total
		? translate("{0} records", total)
		: translate("Showing {0}–{1} of {2}", from, to, total);
}

// The page numbers to offer: the first, the last, and two either side of the current one, with
// null where more than one page is skipped. 1 … 4 5 [6] 7 8 … 20
export function pageNumbers(page, count) {
	const shown = new Set([1, count]);
	for (let near = page - 2; near <= page + 2; near += 1) {
		if (near >= 1 && near <= count) shown.add(near);
	}
	const sorted = [...shown].sort((a, b) => a - b);
	const numbers = [];
	for (const [index, number] of sorted.entries()) {
		const gap = index ? number - sorted[index - 1] : 1;
		// One page skipped is shown; more become a gap.
		if (gap === 2) numbers.push(number - 1);
		if (gap > 2) numbers.push(null);
		numbers.push(number);
	}
	return numbers;
}

// The rows of one page of a list already loaded whole.
export const pageOf = (rows, page, size) => rows.slice((page - 1) * size, page * size);

// The page to stay on when the list shrinks (a filter, a search): never past its last page.
export const clampPage = (page, total, size) =>
	Math.min(Math.max(1, page), pageCount(total, size));
