<template>
	<AppPageHeader title="Settings" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!options" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/3 rounded" />
			<Skeleton class="h-40 w-full rounded-lg" />
		</div>

		<template v-else>
			<!-- On a computer these pages are under Settings in the side bar; phones have none. -->
			<nav
				v-if="isMobile"
				class="flex flex-wrap gap-2"
				aria-label="Set up"
				data-tour="settings-setup"
			>
				<Button
					v-for="page in setupPages"
					:key="page.route"
					:icon-left="page.icon"
					:label="page.label"
					:route="{ name: page.route }"
				/>
			</nav>

			<Tabs v-model="tab">
				<!-- A phone has no room for the row of tabs: they become a list to choose from. -->
				<FormControl
					v-if="isMobile"
					v-model="tab"
					type="select"
					:options="tabOptions"
					aria-label="Show"
				/>
				<TabList v-else class="overflow-x-auto">
					<TabTrigger
						value="reminders"
						label="Reminders and email"
						icon-left="lucide-bell"
						data-tour="tab-reminders"
					/>
					<TabTrigger
						value="branding"
						label="Name and logo"
						icon-left="lucide-image"
						data-tour="tab-branding"
					/>
					<TabTrigger
						value="privacy"
						label="Privacy"
						icon-left="lucide-shield-check"
						data-tour="tab-privacy"
					/>
					<TabTrigger
						value="account"
						label="Who this is for"
						icon-left="lucide-building"
						data-tour="tab-account"
					/>
					<TabTrigger
						v-if="firm"
						value="billing"
						label="Billing"
						icon-left="lucide-receipt"
					/>
				</TabList>
				<TabPanel value="reminders" class="flex flex-col gap-8 pt-2 sm:pt-6">
					<section class="flex flex-col gap-4" aria-labelledby="reminders-heading">
						<div class="flex flex-col gap-0.5">
							<h2
								id="reminders-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								Reminders and email
							</h2>
							<p class="text-sm text-ink-gray-5">
								Reminders, escalations and the weekly summary go out once a day.
							</p>
						</div>
						<FormControl
							v-model="form.enabled"
							type="checkbox"
							label="Send reminders, escalations and the weekly summary"
						/>
						<FormControl
							v-model="form.email_account"
							type="select"
							label="Send email from"
							:options="accountOptions"
							description="Without an account, people are told in the app only."
						/>
						<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<FormControl
								v-model="form.due_soon_days"
								type="number"
								label="Due soon (days before expiry)"
							/>
							<FormControl
								v-model="form.escalate_after_days"
								type="number"
								label="Tell managers after (days overdue)"
								:description="
									boot.accountType === 'CA/CS Firm'
										? 'The reviewer and the client\'s relationship manager are told too.'
										: 'The reviewer is told too.'
								"
							/>
							<FormControl
								v-model="form.digest_day"
								type="select"
								label="Weekly summary on"
								:options="
									options.digest_days.map((day) => ({ label: day, value: day }))
								"
							/>
							<FormControl
								v-model="form.generation_horizon_days"
								type="number"
								label="Show filings (days before the period ends)"
							/>
						</div>
						<FormControl
							v-model="form.party_email_template"
							type="select"
							label="Email to customers and suppliers before their licence expires"
							:options="templateOptions"
						/>
					</section>
				</TabPanel>
				<TabPanel value="branding" class="flex flex-col gap-8 pt-2 sm:pt-6">
					<section class="flex flex-col gap-4" aria-labelledby="branding-heading">
						<div class="flex flex-col gap-0.5">
							<h2
								id="branding-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								Name and logo
							</h2>
							<p class="text-sm text-ink-gray-5">
								Shown in the app's header and when it is installed on a phone.
							</p>
						</div>
						<FormControl
							v-model="form.app_name"
							label="Name"
							placeholder="KlyONIX Compliance"
						/>
						<div class="flex items-center gap-3">
							<img
								v-if="form.app_logo"
								:src="form.app_logo"
								alt="Logo"
								class="size-12 rounded-lg object-cover"
							/>
							<span
								v-else
								class="flex size-12 items-center justify-center rounded-lg bg-surface-gray-2 text-ink-gray-5"
								><span class="lucide-image size-5" aria-hidden="true"
							/></span>
							<div class="flex flex-col gap-1">
								<div class="flex gap-2">
									<Button
										:label="form.app_logo ? 'Replace logo' : 'Upload logo'"
										:loading="uploading"
										@click="logoInput?.click()"
									/>
									<Button
										v-if="form.app_logo"
										variant="ghost"
										label="Remove"
										@click="form.app_logo = ''"
									/>
								</div>
								<span class="text-sm text-ink-gray-5"
									>A square image, at least 512 by 512 pixels.</span
								>
							</div>
							<input
								ref="logoInput"
								type="file"
								accept="image/png,image/jpeg,image/svg+xml"
								class="hidden"
								@change="uploadLogo"
							/>
						</div>
					</section>
				</TabPanel>
				<TabPanel value="privacy" class="flex flex-col gap-8 pt-2 sm:pt-6">
					<section
						class="flex flex-col gap-4"
						aria-labelledby="privacy-heading"
						data-tour="settings-privacy"
					>
						<div class="flex flex-col gap-0.5">
							<h2
								id="privacy-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								Privacy
							</h2>
							<p class="text-sm text-ink-gray-5">
								Everyone accepts the privacy notice the first time they use the
								app. Changing it asks everyone to accept it again (now version
								{{ options.notice_version }}).
							</p>
						</div>
						<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
							<FormControl
								v-model="form.grievance_officer"
								label="Grievance officer"
							/>
							<FormControl
								v-model="form.grievance_email"
								type="email"
								label="Grievance email"
							/>
						</div>
						<div class="flex flex-col gap-1.5">
							<div
								class="flex flex-wrap items-center justify-between gap-x-2 gap-y-1"
							>
								<span class="text-xs text-ink-gray-5">Privacy notice</span>
								<Button
									v-if="!form.privacy_notice"
									size="sm"
									variant="ghost"
									label="Write your own from the standard one"
									@click="form.privacy_notice = options.standard_notice"
								/>
							</div>
							<div
								v-if="!form.privacy_notice"
								class="prose prose-sm max-h-64 max-w-none overflow-y-auto rounded-lg bg-surface-gray-1 p-3 text-ink-gray-7"
								v-html="options.standard_notice"
							/>
							<NoticeEditor v-else v-model="form.privacy_notice" />
							<p class="text-xs text-ink-gray-5">
								The standard notice is used until you write your own; it fills in
								your company's name and the grievance officer. Have a lawyer read
								it.
							</p>
						</div>
						<FormControl
							v-model="form.reminder_log_days"
							type="number"
							label="Keep reminder email addresses for (days)"
							description="Older entries in the reminder log keep the date but lose the address. At least 365."
						/>
					</section>
				</TabPanel>
				<TabPanel value="account" class="flex flex-col gap-8 pt-2 sm:pt-6">
					<section class="flex flex-col gap-4" aria-labelledby="account-heading">
						<div class="flex flex-col gap-0.5">
							<h2
								id="account-heading"
								class="text-base font-semibold text-ink-gray-8"
							>
								Who this is for
							</h2>
							<p class="text-sm text-ink-gray-5">
								A CA/CS firm gets clients, client logins, document requests and the
								client filter; an organisation does not.
							</p>
						</div>
						<TabButtons
							v-model="form.account_type"
							:options="
								options.account_types.map((kind) => ({ label: kind, value: kind }))
							"
						/>
					</section>
				</TabPanel>
				<TabPanel v-if="firm" value="billing" class="flex flex-col gap-8 pt-2 sm:pt-6">
					<section class="flex flex-col items-start gap-3">
						<p class="text-base text-ink-gray-6">
							Billing has a page of its own: the firm on its bills, its GST status
							and logo, and its rate cards.
						</p>
						<Button
							icon-left="lucide-receipt"
							label="Open billing settings"
							:route="{ name: 'BillingSettings' }"
						/>
					</section>
				</TabPanel>
			</Tabs>
		</template>
	</div>

	<!-- Billing saves on its own; the other tabs share this. -->
	<div
		v-if="options && tab !== 'billing'"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full max-w-3xl flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
		>
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button
				variant="solid"
				label="Save"
				:loading="saving"
				:disabled="!dirty"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// The app's settings for Compliance Managers: reminders, email, name and logo, and account type.
import { computed, defineAsyncComponent, onMounted, reactive, ref } from "vue";
import {
	Button,
	FormControl,
	Skeleton,
	TabButtons,
	TabList,
	TabPanel,
	TabTrigger,
	Tabs,
	toast,
} from "frappe-ui";
import { call, upload } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { useTabQuery } from "@/composables/useTabQuery";
import { settingsPagesFor } from "@/navigation";
import { notLoaded } from "@/offline/reachability";

const NoticeEditor = defineAsyncComponent(() => import("@/components/NoticeEditor.vue"));

const isMobile = useIsMobile();
// The settings in tabs by what they are about; the open one is kept in the address.
// A firm also bills its clients; an organisation has none to bill.
const firm = boot.accountType === "CA/CS Firm";
const tab = useTabQuery([
	"reminders",
	"branding",
	"privacy",
	"account",
	...(firm ? ["billing"] : []),
]);
const tabOptions = [
	{ label: "Reminders and email", value: "reminders" },
	{ label: "Name and logo", value: "branding" },
	{ label: "Privacy", value: "privacy" },
	{ label: "Who this is for", value: "account" },
	...(firm ? [{ label: "Billing", value: "billing" }] : []),
];
// Every settings page but this one, which the reader is on.
const setupPages = settingsPagesFor().filter((page) => page.route !== "Settings");
const options = ref(null);
const saved = ref({});
const form = reactive({});
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const uploading = ref(false);
const logoInput = ref(null);

const NONE = { label: "None", value: "" };
const accountOptions = computed(() => [
	NONE,
	...options.value.email_accounts.map((row) => ({
		label: row.email_id ? `${row.name} (${row.email_id})` : row.name,
		value: row.name,
	})),
]);
const templateOptions = computed(() => [
	{ label: "Don't email them", value: "" },
	...options.value.email_templates.map((name) => ({ label: name, value: name })),
]);

// Compared as text, as inputs give numbers back as text.
const dirty = computed(() =>
	Object.keys(saved.value).some(
		(key) => String(form[key] ?? "") !== String(saved.value[key] ?? "")
	)
);

function fill(values) {
	// Empty choices come back as null; the dropdowns name them ("None").
	const filled = Object.fromEntries(
		Object.entries(values).map(([key, value]) => [key, value ?? ""])
	);
	saved.value = { ...filled, enabled: Boolean(values.enabled) };
	Object.assign(form, saved.value);
}

async function uploadLogo(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;
	uploading.value = true;
	try {
		const uploaded = await upload(file, {
			doctype: "KX Compliance Settings",
			docname: "KX Compliance Settings",
			isPrivate: false,
		});
		form.app_logo = uploaded.file_url;
	} catch (err) {
		toast.error(err.message);
	} finally {
		uploading.value = false;
	}
}

async function save() {
	saving.value = true;
	saveError.value = "";
	try {
		const changed = Object.fromEntries(
			Object.keys(saved.value)
				.filter((key) => String(form[key] ?? "") !== String(saved.value[key] ?? ""))
				.map((key) => [key, key === "enabled" ? (form.enabled ? 1 : 0) : form[key]])
		);
		fill(
			await call(
				"kxcompliance.api.save_settings",
				{ values: changed },
				{ httpMethod: "POST" }
			)
		);
		toast.success("Settings saved. Reload the app to see a new name or logo.");
	} catch (err) {
		saveError.value = err.isNetwork
			? "The settings did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

onMounted(async () => {
	try {
		options.value = await call("kxcompliance.api.settings_options");
		fill(options.value.values);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the settings", "opened") : err.message;
	}
});
</script>
