import frappeUIPreset, { content as frappeUIContent } from "frappe-ui/tailwind";

export default {
	presets: [frappeUIPreset],
	content: [
		"./index.html",
		"./src/**/*.{vue,js}",
		...frappeUIContent,
		// Frappe's shared components (@framework/ui, linked from apps/frappe/ui): without this
		// their layout classes are never built and the timeline, filters and lists lose their shape.
		"../../frappe/ui/src/components/**/*.{vue,ts}",
	],
};
