// Links that open Google Calendar or Outlook ready to subscribe to a feed.

// Calendar apps subscribe to webcal:// links; the server answers them over https.
export const webcal = (url) => url.replace(/^https?:\/\//, "webcal://");

export const googleLink = (url) =>
	`https://calendar.google.com/calendar/r?cid=${encodeURIComponent(webcal(url))}`;

export const outlookLink = (url, name) =>
	`https://outlook.live.com/calendar/0/addfromweb?${new URLSearchParams({ url, name })}`;
