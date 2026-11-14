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

export function onTimeSummary(onTime) {
	if (onTime.percent === null) return "No filings fell due in the last twelve months.";
	return "of filings due in the last twelve months were filed on time.";
}
