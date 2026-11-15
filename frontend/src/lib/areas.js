// Each area of the app has a colour of its own, on its menu icon and on the icon of its rows, so
// people learn where they are at a glance. These are accents only: status colours (red for
// overdue, amber for due soon) stay the same everywhere. Full class names, for Tailwind to find.
const TINTS = {
	blue: { icon: "text-ink-blue-5", tile: "bg-surface-blue-2 text-ink-blue-6" },
	cyan: { icon: "text-ink-cyan-6", tile: "bg-surface-cyan-2 text-ink-cyan-7" },
	green: { icon: "text-ink-green-6", tile: "bg-surface-green-2 text-ink-green-7" },
	teal: { icon: "text-ink-teal-6", tile: "bg-surface-teal-2 text-ink-teal-7" },
	violet: { icon: "text-ink-violet-6", tile: "bg-surface-violet-2 text-ink-violet-7" },
	purple: { icon: "text-ink-purple-6", tile: "bg-surface-purple-2 text-ink-purple-7" },
	pink: { icon: "text-ink-pink-6", tile: "bg-surface-pink-2 text-ink-pink-7" },
	orange: { icon: "text-ink-orange-6", tile: "bg-surface-orange-2 text-ink-orange-7" },
	amber: { icon: "text-ink-amber-6", tile: "bg-surface-amber-2 text-ink-amber-7" },
	red: { icon: "text-ink-red-5", tile: "bg-surface-red-2 text-ink-red-6" },
	gray: { icon: "text-ink-gray-6", tile: "bg-surface-gray-2 text-ink-gray-6" },
};

// The colour of each menu section, by its route.
const SECTION_HUES = {
	MyWork: "cyan",
	Overview: "violet",
	ClientHome: "cyan",
	Clients: "orange",
	Filings: "blue",
	MonthCalendar: "teal",
	Register: "green",
	Legal: "purple",
	LicenceCheck: "amber",
	Reports: "pink",
};

// The colour of each kind of row (myWork.js KINDS), matching its area.
const KIND_HUES = {
	licence: "green",
	filing: "blue",
	legal: "purple",
	trademark: "pink",
	request: "orange",
	signatory: "teal",
	extension: "blue",
	reminder: "amber",
	"privacy-request": "violet",
	breach: "red",
	client: "orange",
	company: "cyan",
	person: "violet",
	"item-type": "green",
	"licence-rule": "amber",
	obligation: "blue",
	"licence-check": "amber",
};

export const sectionTint = (route) => TINTS[SECTION_HUES[route] || "gray"];
export const kindTint = (kind) => TINTS[KIND_HUES[kind] || "gray"];
