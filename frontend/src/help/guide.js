// The public user guide (USER_GUIDE.md at the top of the repository), built from the app's own
// Help answers so the two always say the same thing. Run `node scripts/user-guide.mjs` from
// frontend/ after changing articles.js; guide.test.js fails until the guide is rebuilt.
import { AREAS, ARTICLES } from "./articles.js";

const INTRO = `# KlyONIX Compliance: user guide

KlyONIX Compliance keeps a company's statutory filings, licences, registrations, certificates
and legal matters on time, with reminders before anything falls due. A CA or CS firm uses it
for all its clients' companies; an organisation uses it for its own.

This guide is the same as the Help page inside the app. In the app, each answer has a
**Show me** button that opens the page and walks you through it.

## Before you start

- **Signing in.** Open your organisation's address followed by \`/compliance\`, for example
  \`https://yourcompany.example.com/compliance\`, and sign in with the email and password your
  manager set up for you. The first time, you read and accept the privacy notice.
- **On a phone.** The same address works on a phone. Add it to your home screen to use it like
  an app; what you record without a connection is sent when you are back online.
- **Finding your way.** The menu on the left (at the bottom on a phone) lists the areas you
  can use. The question mark at the top of every page replays a short tour of that page, and
  **Help** answers the questions below.
- **Searching.** Press Ctrl+K (⌘K on a Mac) on any page, or choose Search in the menu, and
  type part of a name, number or reference. Every word must appear, in any order. Enter opens
  the result, or a page or action such as "New register item".
- **Notifications.** The bell shows reminders, escalations and answers to your requests. The
  same reminders also come by email when your organisation has switched email on.
- **Your look.** In **Account**, choose light or dark, an accent colour, how close together
  list rows sit, and high contrast.

## Who can do what

| Role | What they do |
| --- | --- |
| Manager | Everything: sets up companies, people, reminders and the obligation library, and sees the Overview. |
| Staff | Keeps the filings, licences and legal work they are responsible for or review. |
| Auditor | Reads everything, including the reminder log, and changes nothing. |
| Client login (CA/CS firms) | Someone at a firm's client: sees their own companies' work and sends documents the firm asks for. |
| Sales and purchase users | Check a customer's or supplier's licences before a sale or purchase. |

Answers marked *Managers*, *CA/CS firms* or *Client logins* are for those people only.
`;

const OUTRO = `
---

This guide is built from the app's Help page. Something missing or unclear? Ask your
manager, or the team that set the app up for you.
`;

// Who an answer is for, as the Help decides: `client` adds client logins to the staff who see it,
// and `staff: false` keeps it to client logins alone.
function audience(article) {
	if (article.staff === false) return "*For: Client logins.*\n\n";
	const marks = [];
	if (article.managers) marks.push("Managers");
	if (article.firm) marks.push("CA/CS firms");
	return marks.length ? `*For: ${marks.join(", ")}.*\n\n` : "";
}

function section(article) {
	const steps = article.steps.map((step, index) => `${index + 1}. ${step}`).join("\n");
	const tip = article.tip ? `\n\n> **Tip.** ${article.tip}` : "";
	return `### ${article.title}\n\n${audience(article)}${article.when}\n\n${steps}${tip}\n`;
}

const anchor = (text) =>
	text
		.toLowerCase()
		.replace(/[^a-z0-9 -]/g, "")
		.trim()
		.replace(/ /g, "-");

export function userGuide(areas = AREAS, articles = ARTICLES) {
	const used = areas.filter((area) => articles.some((article) => article.area === area));
	const contents = used.map((area) => `- [${area}](#${anchor(area)})`).join("\n");
	const body = used
		.map((area) => {
			const answers = articles.filter((article) => article.area === area).map(section);
			return `## ${area}\n\n${answers.join("\n")}`;
		})
		.join("\n");
	return `${INTRO}\n## Contents\n\n${contents}\n\n${body}${OUTRO}`;
}
