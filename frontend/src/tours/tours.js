// The app's tours: one per page, in the words its screens use.
//
// RK, 15 Nov 2026: "Short walk-throughs of the page you are on and the others you use... if anyone
// signs up they have to use the app without any training." As in KlyONIX One, the tours live here
// in the code. Each step points at something the page draws: a `data-tour` marker, or a section by
// its heading's id ("section:penalty-heading"). A step whose target is not on screen is left out,
// so one tour fits every reader: someone who cannot record anything simply meets fewer steps.
// tours.test.js fails the build when a step points at something no page draws.
//
// Who is offered a tour follows the side bar: `managers` for Compliance Managers, `firm` and
// `organisation` for the kind of site, `client` for a client's own login (`staff: false` keeps a
// tour from the firm's people). A `record` tour needs a record, so it plays on that page and is not
// offered from the list of tours. Within a tour, a step marked `client: false` is left out for a
// client's login, and `clientTitle` / `clientText` say the step in a client's words. The ids are
// the server's too: kx_compliance/tours.py lists the
// same ones, and a test holds the two equal.

export const TOURS = [
	{
		id: "welcome",
		title: "Getting around the app",
		route: "MyWork",
		steps: [
			{
				title: "Welcome",
				text: "This is where you keep every filing, licence and legal date on time. This short tour shows where things are. Take it again any time from the question mark at the top of each page.",
			},
			{
				target: ["nav"],
				title: "Your menu",
				text: "Filings, the register of licences and registrations, legal work and the calendar. You see what your role gives you.",
			},
			{
				target: ["notifications"],
				title: "Notifications",
				text: "Reminders, escalations and answers to your requests come here as well as by email. The number shows how many you have not read.",
			},
			{
				target: ["getting-started"],
				title: "Getting started",
				text: "A few steps that make the app useful. Each one opens the screen that does it, and ticks itself off once done.",
			},
			{
				target: ["my-work-summary"],
				title: "Your day at a glance",
				text: "What is overdue and what falls due soon, among the things you hold or review.",
			},
			{
				target: ["client-filter"],
				title: "One client at a time",
				text: "Choose a client to see only their work, here and on every list. Choose All clients to see everything again.",
			},
			{
				target: ["my-work-list"],
				title: "What needs you",
				text: "Overdue first, then this week, then later. Open any row to act on it.",
			},
			{
				target: ["help"],
				title: "Help is always here",
				text: "The question mark replays this page's tour, lists the others, and opens the user manual.",
			},
		],
	},
	{
		id: "overview",
		title: "The overview",
		route: "Overview",
		managers: true,
		steps: [
			{
				target: ["overview-tiles"],
				title: "What is late and what is close",
				text: "Overdue, due this week and due in the month, across filings, licences and legal dates, with what each is made of. Each part opens the list of exactly those.",
			},
			{
				target: ["overview-charts"],
				title: "Month by month",
				text: "What falls due in the next six months, and how filings were filed in the last six: on time, late, or not yet.",
			},
			{
				target: ["section:needs-heading"],
				title: "Needs you now",
				text: "Everything someone has to act on, the most urgent first. Each number opens its list.",
			},
			{
				target: ["section:on-time-heading"],
				title: "Filed on time",
				text: "How many filings due in the last twelve months were filed on time, filed late, or are still overdue.",
			},
			{
				target: ["section:scores-heading"],
				title: "Compliance score",
				text: "Each company starts at 100 and loses points for what needs fixing, so you see where to look first.",
			},
			{
				target: ["overview-areas"],
				title: "Each area",
				text: "The register, filings, legal work and the rest, each number with its status. Open one to see the list it counts.",
			},
		],
	},
	{
		id: "calendar",
		title: "The calendar",
		route: "MonthCalendar",
		steps: [
			{
				target: ["calendar-grid"],
				title: "At a glance",
				text: "Filings on their due dates, licences on the day they expire, hearings, and documents due from clients. Overdue shows in red; filed is struck through.",
			},
			{
				target: ["calendar-views"],
				title: "Month, week or day",
				text: "A month's grid, a week day by day, or everything on one day.",
			},
			{
				target: ["calendar-filters"],
				title: "Show what you need",
				text: "Switch each kind on or off, show only yours or someone else's, or only what is still open.",
			},
			{
				target: ["page-actions"],
				title: "Move in time",
				text: "The arrows go back and forward a month, week or day; Today brings you back.",
			},
			{
				target: ["section:day-heading"],
				title: "One day",
				text: "Choose a day to list what falls on it. Open any of them to act on it.",
			},
		],
	},
	{
		id: "filings",
		title: "Filings",
		route: "Filings",
		steps: [
			{
				title: "Filings",
				text: "Every return, payment and form the statutory calendar makes from each company's registrations, with its due date.",
			},
			{
				target: ["list-tabs"],
				title: "To file, for review, done",
				text: "To file is what is still open. For review is what someone has filed and a second person checks. Done keeps what was filed.",
			},
			{
				target: ["list-search"],
				title: "Find a filing",
				text: "Type part of a return's name, such as 3B or TDS.",
			},
			{
				target: ["filings-bulk", "filings-more"],
				title: "File in bulk",
				text: "On filing day, record one return for many companies in one table. On a phone it is under More, with due-date extensions.",
			},
			{
				target: ["filings-extensions"],
				title: "Due-date extensions",
				text: "When the government extends a due date, record it here and the open filings move to the new date.",
			},
			{
				target: ["list-rows"],
				title: "Open a filing",
				text: "Each row shows the period, the company and when it is due. Open it to record the filing.",
			},
			{
				target: ["list-filter"],
				title: "Filter and sort",
				text: "Narrow the list to one company, one type, or only what you are responsible for, and sort it by date or name. Your choice stays in the address, so Back returns to it.",
			},
			{
				target: ["list-layout"],
				title: "List, table or Kanban",
				text: "Show the list as rows, as a table whose columns you choose, or as a Kanban board. A board moves a record when you drag its card, or from its arrows on a phone.",
			},
			{
				target: ["list-views"],
				title: "Your views",
				text: "Save the filters, sort and layout you use as a view, and open it from here. A manager can share a view with everyone, or pin it beside the tabs.",
			},
		],
	},
	{
		id: "filing",
		title: "A filing",
		route: "ComplianceTask",
		record: true,
		client: true,
		steps: [
			{
				target: ["filing-steps"],
				title: "Where it is",
				text: "File, then review where the return needs a second look, then filed.",
				clientText:
					"Your firm prepares it, checks it where it needs a second look, then files it.",
			},
			{
				target: ["section:penalty-heading"],
				title: "What filing late costs",
				text: "The late fee and interest if it is filed after the due date, and what it has already run up if it is late.",
			},
			{
				target: ["section:filing-heading"],
				title: "Record the filing",
				text: "Once it is filed on the portal, record the date, the acknowledgement number and a copy of the acknowledgement.",
				clientTitle: "The filing",
				clientText:
					"Once it is filed: the date, the acknowledgement number and a copy of the acknowledgement.",
			},
			{
				target: ["section:requests-heading"],
				title: "Ask the client",
				text: "Ask the client for what you need, such as a sales register. They upload it from their own login and you are told.",
				clientTitle: "What your firm needs",
				clientText:
					"Documents your firm has asked you for. Upload each one here, or reply to its email with the file attached.",
			},
			{
				target: ["filing-actions"],
				client: false,
				title: "The next step",
				text: "Send it for review, or mark it filed where no review is needed. A reviewer marks it filed or sends it back with a note.",
			},
			{
				target: ["record-facts"],
				title: "At a glance",
				text: "When it is due, who looks after it and whose it is, in one band across the top.",
			},
			{
				target: ["record-activity"],
				title: "Activity",
				text: "Every change, with who made it and when, and comments for the team. On a phone it is at the foot of the page.",
			},
		],
	},
	{
		id: "bulk-filing",
		title: "Filing in bulk",
		route: "BulkFiling",
		steps: [
			{
				target: ["bulk-choose"],
				title: "Pick a return and period",
				text: "Only returns with open filings are offered, the soonest due first.",
			},
			{
				target: ["bulk-date"],
				title: "One date for all",
				text: "The date they were filed on, for every row without its own.",
			},
			{
				target: ["bulk-proofs"],
				title: "Many proofs at once",
				text: "Choose all the acknowledgements together. A file goes to the row whose GSTIN, TAN or acknowledgement number is in its name.",
			},
			{
				target: ["bulk-rows"],
				title: "Each company",
				text: "Add each acknowledgement number, and attach any proof that did not match by itself.",
			},
			{
				target: ["bulk-save"],
				title: "Save them together",
				text: "Each row is saved on its own, so the good ones are saved and any other says what is missing.",
			},
		],
	},
	{
		id: "extensions",
		title: "Due-date extensions",
		route: "Extensions",
		steps: [
			{
				title: "Due-date extensions",
				text: "When the government extends a due date by notification, record it here. Open filings for the periods it covers move to the new date; filed ones keep theirs.",
			},
			{
				target: ["page-actions"],
				title: "Extend a due date",
				text: "Choose the return, the periods it covers and the new date. You see how many filings it moves before you save.",
			},
		],
	},
	{
		id: "register",
		title: "The register",
		route: "Register",
		client: true,
		steps: [
			{
				title: "The register",
				text: "Licences, registrations, certificates, insurance, subscriptions and digital signatures, each with the date it expires.",
			},
			{
				target: ["list-tabs"],
				title: "What needs attention",
				text: "Items expiring soon, expired, or being renewed come first.",
			},
			{
				target: ["page-actions"],
				title: "Add an item, or a signatory",
				text: "New item adds a licence or certificate. Signatories lists the directors and partners who hold digital signatures.",
			},
			{
				target: ["list-rows"],
				title: "Open an item",
				text: "See its validity and certificate, and start a renewal when it is due.",
			},
			{
				target: ["list-filter"],
				title: "Filter and sort",
				text: "Narrow the list to one company, one type, or only what you are responsible for, and sort it by date or name. Your choice stays in the address, so Back returns to it.",
			},
			{
				target: ["list-layout"],
				title: "List, table or Kanban",
				text: "Show the list as rows, as a table whose columns you choose, or as a Kanban board. A board moves a record when you drag its card, or from its arrows on a phone.",
			},
			{
				target: ["list-views"],
				title: "Your views",
				text: "Save the filters, sort and layout you use as a view, and open it from here. A manager can share a view with everyone, or pin it beside the tabs.",
			},
		],
	},
	{
		id: "item",
		title: "A register item",
		route: "ComplianceItem",
		record: true,
		client: true,
		steps: [
			{
				target: ["section:open-renewal-heading"],
				title: "A renewal under way",
				text: "When an item is being renewed, its progress is here. Record the new validity and certificate; a manager completes it.",
			},
			{
				target: ["section:certificate-heading"],
				title: "The certificate",
				text: "The current certificate, ready to open or share.",
			},
			{
				target: ["section:details-heading"],
				title: "Details",
				text: "Who holds it, who is responsible, the issuing authority and its dates.",
			},
			{
				target: ["page-actions"],
				title: "Renew or change it",
				text: "Start a renewal or edit the item from here.",
			},
			{
				target: ["record-facts"],
				title: "At a glance",
				text: "When it is due, who looks after it and whose it is, in one band across the top.",
			},
			{
				target: ["record-activity"],
				title: "Activity",
				text: "Every change, with who made it and when, and comments for the team. On a phone it is at the foot of the page.",
			},
		],
	},
	{
		id: "signatories",
		title: "Signatories",
		route: "Signatories",
		steps: [
			{
				title: "Signatories",
				text: "Directors, partners and authorised signatories, the companies they sign for, and the digital signatures they hold.",
			},
			{
				target: ["page-actions"],
				title: "Add a signatory",
				text: "Add someone once and link them to every company they sign for.",
			},
		],
	},
	{
		id: "legal",
		title: "Legal work",
		route: "Legal",
		client: true,
		steps: [
			{
				target: ["list-tabs"],
				title: "Coming up, cases, trademarks",
				text: "Coming up lists hearings, reply dates and trademark deadlines, soonest first. Cases and Trademarks list each one.",
			},
			{
				target: ["page-actions"],
				title: "A notice has come",
				text: "Log a notice the day it arrives, with its reply date, so the date is never missed.",
			},
			{
				target: ["list-rows"],
				title: "Open one",
				text: "See its dates, documents and what happened at each hearing.",
			},
		],
	},
	{
		id: "case",
		title: "A notice or case",
		route: "LegalCase",
		record: true,
		client: true,
		steps: [
			{
				target: ["section:dates-heading"],
				title: "Its dates",
				text: "Hearings and reply dates. After each one, record what happened and the next date.",
			},
			{
				target: ["section:details-heading"],
				title: "Details",
				text: "The forum, the reference, the amount involved and who handles it.",
			},
			{
				target: ["section:documents-heading"],
				title: "Documents",
				text: "The notice, replies and orders, kept together.",
			},
			{
				target: ["record-facts"],
				title: "At a glance",
				text: "When it is due, who looks after it and whose it is, in one band across the top.",
			},
			{
				target: ["record-activity"],
				title: "Activity",
				text: "Every change, with who made it and when, and comments for the team. On a phone it is at the foot of the page.",
			},
		],
	},
	{
		id: "trademark",
		title: "A trademark",
		route: "Trademark",
		record: true,
		client: true,
		steps: [
			{
				target: ["section:dates-heading"],
				title: "Its deadlines",
				text: "Examination report replies, hearings and the renewal date.",
			},
			{
				target: ["section:details-heading"],
				title: "Details",
				text: "The application number, classes, status and who handles it.",
			},
			{
				target: ["record-facts"],
				title: "At a glance",
				text: "When it is due, who looks after it and whose it is, in one band across the top.",
			},
			{
				target: ["record-activity"],
				title: "Activity",
				text: "Every change, with who made it and when, and comments for the team. On a phone it is at the foot of the page.",
			},
		],
	},
	{
		id: "clients",
		title: "Clients",
		route: "Clients",
		firm: true,
		steps: [
			{
				target: ["clients-list"],
				title: "Your clients",
				text: "Each client with its lowest compliance score and what is next. Open one to see all its companies and work.",
			},
			{
				target: ["page-actions"],
				title: "Add clients",
				text: "Add one client at a time, or many at once from a spreadsheet.",
			},
		],
	},
	{
		id: "client",
		title: "A client",
		route: "Client",
		record: true,
		firm: true,
		steps: [
			{
				target: ["section:open-heading"],
				title: "What is open",
				text: "The client's open filings and items, soonest first.",
			},
			{
				target: ["section:requests-heading"],
				title: "Documents asked for",
				text: "What you have asked the client for, and whether it has come.",
			},
			{
				target: ["section:companies-heading"],
				title: "Companies",
				text: "Each company of the client and its compliance score.",
			},
			{
				target: ["section:year-heading"],
				title: "The year so far",
				text: "Filed on time, filed late and fees paid in this financial year.",
			},
			{
				target: ["record-facts"],
				title: "At a glance",
				text: "Who at the firm looks after the client, its companies, open filings and documents asked for, in one band across the top.",
			},
			{
				target: ["record-activity"],
				title: "Activity",
				text: "Every change, with who made it and when, and comments for the team. On a phone it is at the foot of the page.",
			},
		],
	},
	{
		id: "client-home",
		title: "Your home",
		route: "ClientHome",
		client: true,
		staff: false,
		steps: [
			{
				title: "Welcome",
				text: "Your firm uses this to keep your filings, licences and legal dates on time. Here you see what they are doing for you, and send them what they ask for.",
			},
			{
				target: ["section:requests-heading"],
				title: "What your firm needs",
				text: "Documents your firm has asked you for. Open one to upload it from your computer or phone.",
			},
			{
				target: ["section:open-heading"],
				title: "What is open",
				text: "Your filings and items coming up, and those overdue.",
			},
			{
				target: ["section:companies-heading"],
				title: "Your companies",
				text: "Each of your companies with its compliance score.",
			},
			{
				target: ["help"],
				title: "Help",
				text: "The question mark replays this tour and opens short answers to common questions.",
			},
		],
	},
	{
		id: "document-request",
		title: "A document request",
		route: "DocumentRequest",
		record: true,
		client: true,
		steps: [
			{
				target: ["section:needed-heading"],
				title: "What is needed",
				text: "What the firm asked for and by when.",
			},
			{
				target: ["section:documents-heading"],
				title: "Upload it",
				text: "Upload the file here. The firm is told, accepts it, or sends it back with a note.",
			},
		],
	},
	{
		id: "bulk-setup",
		title: "Setting up from a spreadsheet",
		route: "BulkSetup",
		managers: true,
		firm: true,
		steps: [
			{
				target: ["bulk-setup-sheet"],
				title: "Download the sheet",
				text: "One row per company: its client, kind, registrations and people.",
			},
			{
				target: ["bulk-setup-upload"],
				title: "Upload it back",
				text: "Every row is checked first. Fix what is marked, then set them all up at once.",
			},
		],
	},
	{
		id: "settings",
		title: "Settings",
		route: "Settings",
		managers: true,
		steps: [
			{
				target: ["settings-setup", "settings-nav"],
				title: "Setting up",
				text: "People, companies, the obligation library, due-date extensions and register item types each have a page under Settings.",
			},
			{
				target: ["section:reminders-heading", "tab-reminders"],
				title: "Reminders",
				text: "Choose the email account and switch reminders on. People are reminded before things fall due, and managers are told when they are overdue.",
			},
			{
				target: ["section:branding-heading", "tab-branding"],
				title: "Your name and logo",
				text: "Shown in the app and on phones where it is installed.",
			},
			{
				target: ["settings-privacy", "tab-privacy"],
				title: "Privacy",
				text: "The privacy notice everyone accepts, your grievance officer, and how long reminder email addresses are kept.",
			},
		],
	},
	{
		id: "people",
		title: "People",
		route: "People",
		managers: true,
		steps: [
			{
				target: ["people-invite"],
				title: "Invite someone",
				text: "Add a colleague by name and email, as Manager, Staff or Auditor. They get an email to set a password.",
			},
			{
				target: ["people-list"],
				title: "The team",
				text: "Change someone's role here, or open them for their password and the work they hold.",
			},
		],
	},
	{
		id: "person",
		title: "A person",
		route: "Person",
		record: true,
		managers: true,
		steps: [
			{
				target: ["section:role-heading"],
				title: "Their role",
				text: "Manager, Staff or Auditor. Choose another and it changes at once.",
			},
			{
				target: ["section:work-heading"],
				title: "What they hold",
				text: "Their open filings, register items, cases and trademarks. Each number opens the list.",
			},
			{
				target: ["section:handover-heading"],
				title: "Hand over their work",
				text: "When they leave or move to other clients, give everything they hold to one person in one go.",
			},
			{
				target: ["section:sign-in-heading"],
				title: "Signing in",
				text: "Email them a password reset, or set a temporary password to pass on in person.",
			},
		],
	},
	{
		id: "companies",
		title: "Companies",
		route: "Companies",
		managers: true,
		steps: [
			{
				target: ["list-rows"],
				title: "Set up, and not yet",
				text: "First the companies the calendar makes filings for: open one to change its registrations or who handles each obligation. Under them, companies in ERPNext not tracked yet: open one to set it up.",
			},
		],
	},
	{
		id: "company",
		title: "A company",
		route: "Company",
		record: true,
		managers: true,
		steps: [
			{
				target: ["section:company-heading", "tab-company"],
				title: "The company",
				text: "Its kind and the people who handle and review its work by default.",
			},
			{
				target: ["section:registrations-heading", "tab-registrations"],
				title: "Registrations",
				text: "GST, TAN, PF and the rest. Each one brings the returns it needs.",
			},
			{
				target: ["section:obligations-heading", "tab-obligations"],
				title: "Obligations",
				text: "Every return that applies, who handles it, and which ones do not apply.",
			},
		],
	},
	{
		id: "obligations",
		title: "The obligation library",
		route: "ObligationLibrary",
		managers: true,
		steps: [
			{
				target: ["list-tabs"],
				title: "In use or off",
				text: "Switch off an obligation your clients never have, and it stops making filings.",
			},
			{
				target: ["list-rows"],
				title: "Grouped by law",
				text: "Standard ones come with the app and stay current with each update. Open one to see its rules or set your own late fees.",
			},
			{
				target: ["page-actions"],
				title: "Your own",
				text: "Add an obligation the library does not have, such as a local body return.",
			},
		],
	},
	{
		id: "item-types",
		title: "Register item types",
		route: "ItemTypes",
		managers: true,
		steps: [
			{
				target: ["list-rows"],
				title: "Kinds of item",
				text: "How often each kind renews, how long it stays valid after expiry, and when reminders go out.",
			},
		],
	},
	{
		id: "licence-check",
		title: "Licence Check",
		route: "LicenceCheck",
		licenceCheck: true,
		steps: [
			{
				title: "Licence Check",
				text: "Before you sell to a customer or buy from a supplier, check they hold the licences the sale needs.",
			},
			{
				target: ["section:needed-heading"],
				title: "What is needed",
				text: "The licences the customer or supplier must hold for this kind of sale.",
			},
			{
				target: ["section:held-heading"],
				title: "What they hold",
				text: "Their licences on record and whether each is valid today.",
			},
		],
	},
	{
		id: "licence-rules",
		title: "Customer and supplier licences",
		route: "LicenceRules",
		managers: true,
		licenceCheck: true,
		steps: [
			{
				title: "Licence rules",
				text: "Say which licences a customer or supplier must hold. A sale or purchase without them can be saved as a draft but not submitted, or is only warned about.",
			},
			{
				target: ["list-rows"],
				title: "Each rule",
				text: "The licence, who must hold it, and the documents it is checked on. Open one to change it or switch it off.",
			},
			{
				target: ["page-actions"],
				title: "Add a rule, see what was blocked",
				text: "Add a rule for each licence, and see the sales and purchases that were stopped.",
			},
		],
	},
	{
		id: "licence-blocks",
		title: "Blocks and warnings",
		route: "LicenceBlocks",
		managers: true,
		licenceCheck: true,
		steps: [
			{
				target: ["licence-blocks-tabs"],
				title: "Blocked, warned, let through",
				text: "What a rule stopped, what it only warned about, and what a manager let through once.",
			},
			{
				target: ["licence-blocks-list"],
				title: "Let one through",
				text: "When a sale must go ahead, Allow this once with a reason. The reason is kept, and only that document goes through.",
			},
		],
	},
	{
		id: "reminder-log",
		title: "The reminder log",
		route: "ReminderLog",
		steps: [
			{
				title: "What was sent",
				text: "Every reminder, escalation and summary the app sent, to whom and when, newest first.",
			},
			{
				target: ["list-tabs"],
				title: "One kind at a time",
				text: "Reminders before things fall due, escalations to managers when they are overdue, and the rest.",
			},
			{
				target: ["list-search"],
				title: "Did they get it?",
				text: "Type part of someone's email address to see everything sent to them.",
			},
		],
	},
	{
		id: "reports",
		title: "Reports",
		route: "Reports",
		steps: [
			{
				target: ["reports-list"],
				title: "Reports",
				text: "The same reports as the Desk, so the numbers agree. Open one to filter it and download it.",
			},
		],
	},
	{
		id: "report",
		title: "A report",
		route: "Report",
		record: true,
		steps: [
			{
				target: ["report-filters"],
				title: "Filters",
				text: "Narrow it down; the report runs again as you change them. Leave a filter on All to include everything.",
			},
			{
				target: ["report-table"],
				title: "The results",
				text: "Press a column's name to sort by it. A name in a link opens that record.",
			},
			{
				target: ["report-download"],
				title: "Download",
				text: "As Excel or CSV, for a spreadsheet or to send on.",
			},
		],
	},
	{
		id: "account",
		title: "Account",
		route: "Account",
		client: true,
		steps: [
			{
				target: ["privacy-actions"],
				title: "Your privacy",
				text: "Read the privacy notice again, ask to see, correct or erase your data, or withdraw your consent. The answers to your requests show here.",
			},
		],
	},
	{
		id: "privacy-requests",
		title: "Privacy requests",
		route: "PrivacyRequests",
		managers: true,
		steps: [
			{
				title: "Privacy requests",
				text: "Anyone using the app can ask from Account to see, correct or erase their data, or raise a grievance. Each comes here, to be answered within 90 days.",
			},
			{
				target: ["list-tabs"],
				title: "To answer, then answered",
				text: "Waiting requests come first, the one due soonest on top. Open one to answer it.",
			},
		],
	},
	{
		id: "privacy-request",
		title: "A privacy request",
		route: "PrivacyRequest",
		managers: true,
		steps: [
			{
				target: ["privacy-answer"],
				title: "Answer it",
				text: "Mark it in progress while you work on it. When it is done or declined, write the answer: the person is told in the app, and by email when the app sends email.",
			},
		],
	},
	{
		id: "breaches",
		title: "Data breaches",
		route: "Breaches",
		managers: true,
		steps: [
			{
				title: "Data breaches",
				text: "If personal data is lost, stolen, or seen by someone who should not see it, record it here at once. The Data Protection Board must be told within 72 hours, and each person affected without delay.",
			},
			{
				target: ["page-actions"],
				title: "Record a breach",
				text: "Say when it was found and what happened. The list shows how many hours are left to tell the Board.",
			},
		],
	},
	{
		id: "breach",
		title: "A data breach",
		route: "Breach",
		managers: true,
		steps: [
			{
				target: ["breach-reported"],
				title: "Who was told",
				text: "Fill in when the Board and the people affected were told. Until both are in, the breach stays on the Overview.",
			},
		],
	},
	{
		id: "help",
		title: "The user manual",
		route: "Help",
		client: true,
		steps: [
			{
				target: ["help-search"],
				title: "Ask a question",
				text: "Type what you want to do, such as file a return or renew a licence.",
			},
			{
				target: ["help-articles"],
				title: "Short answers",
				text: "Each answer says when you need it and the steps. Show me opens the page and plays its tour.",
			},
		],
	},
];

export const tourById = (id) => TOURS.find((tour) => tour.id === id);
export const tourFor = (route) => TOURS.find((tour) => tour.route === route);
