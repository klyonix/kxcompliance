// The app's words in the reader's language (RK, 15 Nov 2026: Hindi for client logins first).
// `t("Filings")` gives the reader's translation, or the English when there is none, so a phrase
// not yet translated still reads. `{0}`, `{1}` in a phrase take the extra arguments.
// Translations live in locales/<code>.js, keyed by the English; locales.test.js holds every phrase
// the client screens use to the Hindi dictionary.
import hi from "@/locales/hi";

const DICTIONARIES = { hi };
// The languages a person may choose in the app, in their own words.
export const LANGUAGES = [
	{ value: "en", label: "English" },
	{ value: "hi", label: "हिन्दी" },
];

let current = "en";

export function setLanguage(code) {
	current = DICTIONARIES[code] ? code : "en";
	if (typeof document !== "undefined") document.documentElement.lang = current;
}

export const language = () => current;

export function t(text, ...args) {
	const phrase = DICTIONARIES[current]?.[text] || text;
	return args.length
		? phrase.replace(/\{(\d+)\}/g, (match, index) =>
				index in args ? String(args[index]) : match
		  )
		: phrase;
}
