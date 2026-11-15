// How the managers' overview shows its numbers, kept apart from the screen so it can be tested.

const TONE_TEXT = {
	red: "text-ink-red-5",
	amber: "text-ink-amber-5",
	blue: "text-ink-blue-5",
	green: "text-ink-green-5",
	gray: "text-ink-gray-8",
};

// A number is coloured only when there is something to look at; zero stays quiet.
export const valueClass = (card) => (card.value ? TONE_TEXT[card.tone] : "text-ink-gray-4");

// The on-time bar: each part's share of the filings counted, with its colour and words.
export function onTimeParts(onTime) {
	const counted = onTime.on_time + onTime.late + onTime.overdue;
	if (!counted) return [];
	return [
		{ key: "on_time", label: "On time", count: onTime.on_time, colour: "bg-surface-green-5" },
		{ key: "late", label: "Late", count: onTime.late, colour: "bg-surface-amber-5" },
		{ key: "overdue", label: "Overdue", count: onTime.overdue, colour: "bg-surface-red-5" },
	]
		.filter((part) => part.count)
		.map((part) => ({ ...part, share: (part.count * 100) / counted }));
}

// A percentage only means something once filings have been filed; before that, say so instead of 0%.
export const showPercent = (onTime) =>
	onTime.percent !== null && !(onTime.on_time === 0 && onTime.late === 0);

export function onTimeSummary(onTime) {
	if (onTime.percent === null) return "No filings fell due in the last twelve months.";
	if (!showPercent(onTime)) return "Nothing has been filed yet in the last twelve months.";
	return "of filings due in the last twelve months were filed on time.";
}

const URGENCY = { red: 0, amber: 1, blue: 2 };

// The numbers that need someone to act, the most urgent first, each with its section's name.
export function needsYou(sections) {
	return sections
		.flatMap((section) =>
			section.cards
				.filter((card) => card.act && card.value)
				.map((card) => ({ ...card, section: section.title }))
		)
		.sort((a, b) => (URGENCY[a.tone] ?? 3) - (URGENCY[b.tone] ?? 3));
}

// A section with nothing in it is named once at the end rather than shown as a row of zeros.
export const isQuiet = (section) => section.cards.every((card) => !card.value);

// Each area of the Overview, by the server's key: the kind of row whose colour and icon it shares.
const AREA_KINDS = {
	register: "licence",
	filings: "filing",
	legal: "legal",
	trademarks: "trademark",
	"licence-check": "licence-rule",
	privacy: "privacy-request",
};
export const areaKind = (section) => AREA_KINDS[section.key] || "";

// How many of an area's numbers need someone: those with a value and a tone that is not calm.
export const needingCount = (section) =>
	section.cards.filter((card) => card.value && ["red", "amber"].includes(card.tone)).length;
