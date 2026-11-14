// How the app writes dates: "14 Nov 2026", in the reader's own locale.
export const formatDate = (value) =>
	value
		? new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
				day: "numeric",
				month: "short",
				year: "numeric",
		  })
		: "";
