<template>
	<AppPageHeader
		:title="data?.full_name || 'Person'"
		:parent="{ label: 'People', route: { name: 'People' } }"
	/>

	<RecordFrame :facts="facts">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!data" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/2 rounded" />
			<Skeleton class="h-32 w-full rounded-lg" />
		</div>

		<template v-else>
			<!-- Their own role, or an administrator's, is changed elsewhere: say so instead. -->
			<p
				v-if="!changeable"
				class="rounded-lg bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-7"
			>
				{{
					data.is_me
						? "This is you. Another manager changes your role or password."
						: "An administrator. Their access is changed in the Desk."
				}}
			</p>

			<section class="flex flex-col gap-3" aria-labelledby="role-heading">
				<h2 id="role-heading" class="text-base font-semibold text-ink-gray-8">Role</h2>
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-3" role="radiogroup">
					<button
						v-for="role in ROLES"
						:key="role.label"
						type="button"
						role="radio"
						:aria-checked="data.role === role.label"
						:disabled="!changeable || saving"
						class="flex flex-col gap-1 rounded-lg border px-3 py-2.5 text-left disabled:cursor-default"
						:class="
							data.role === role.label
								? 'border-outline-gray-4 bg-surface-gray-2'
								: 'border-outline-gray-1 enabled:hover:bg-surface-gray-1'
						"
						@click="changeRole(role.label)"
					>
						<span
							class="flex items-center gap-2 text-base font-medium text-ink-gray-8"
						>
							<span
								class="size-4 shrink-0"
								:class="
									data.role === role.label
										? 'lucide-circle-check text-ink-gray-8'
										: 'lucide-circle text-ink-gray-4'
								"
								aria-hidden="true"
							/>
							{{ role.label }}
						</span>
						<span class="text-sm text-ink-gray-5">{{ role.detail }}</span>
					</button>
				</div>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="work-heading">
				<h2 id="work-heading" class="text-base font-semibold text-ink-gray-8">
					Open work they hold
				</h2>
				<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
					<RouterLink
						v-for="card in data.work"
						:key="card.doctype"
						:to="listRoute(card, data.full_name)"
						class="flex flex-col gap-1 rounded-lg border border-outline-gray-1 px-3 py-3 hover:bg-surface-gray-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
					>
						<span
							class="text-2xl font-semibold tabular-nums"
							:class="card.value ? 'text-ink-gray-8' : 'text-ink-gray-4'"
							>{{ card.value }}</span
						>
						<span class="text-sm text-ink-gray-6">{{ card.label }}</span>
					</RouterLink>
				</div>
				<p class="text-sm text-ink-gray-5">
					Removing someone from the team leaves this work with them; give it to someone
					else from each record.
				</p>
			</section>

			<section
				v-if="changeable"
				class="flex flex-col gap-3"
				aria-labelledby="sign-in-heading"
			>
				<h2 id="sign-in-heading" class="text-base font-semibold text-ink-gray-8">
					Signing in
				</h2>
				<div
					class="flex flex-col rounded-lg border border-outline-gray-1 [&>*+*]:border-t [&>*+*]:border-outline-gray-1"
				>
					<div
						v-if="!data.last_login"
						class="flex flex-col gap-2 px-3 py-3 sm:flex-row sm:items-center"
					>
						<div class="flex flex-1 flex-col gap-0.5">
							<span class="text-base font-medium text-ink-gray-8"
								>New sign-in link</span
							>
							<span class="text-sm text-ink-gray-5">
								They have not signed in yet. A fresh link to set their password, to
								pass on yourself.
							</span>
						</div>
						<Button label="Get a link" @click="newLink" />
					</div>
					<div class="flex flex-col gap-2 px-3 py-3 sm:flex-row sm:items-center">
						<div class="flex flex-1 flex-col gap-0.5">
							<span class="text-base font-medium text-ink-gray-8">
								Email a password reset
							</span>
							<span class="text-sm text-ink-gray-5">
								{{
									data.can_email
										? `${data.full_name} gets a link to set a new password themselves.`
										: "This site cannot send email yet. Set a temporary password instead."
								}}
							</span>
						</div>
						<Button
							label="Send reset email"
							:disabled="!data.can_email"
							:loading="sending"
							@click="sendReset"
						/>
					</div>
					<div class="flex flex-col gap-2 px-3 py-3 sm:flex-row sm:items-center">
						<div class="flex flex-1 flex-col gap-0.5">
							<span class="text-base font-medium text-ink-gray-8">
								Set a temporary password
							</span>
							<span class="text-sm text-ink-gray-5">
								For you to pass on in person. It signs them out everywhere, and is
								noted on their record.
							</span>
						</div>
						<Button label="Set a password" @click="askPassword" />
					</div>
				</div>
			</section>

			<section v-if="changeable" class="flex flex-col gap-3">
				<div
					class="flex flex-col gap-2 rounded-lg border border-outline-red-1 px-3 py-3 sm:flex-row sm:items-center"
				>
					<div class="flex flex-1 flex-col gap-0.5">
						<span class="text-base font-medium text-ink-gray-8"
							>Remove from the team</span
						>
						<span class="text-sm text-ink-gray-5">
							They can no longer open the app. Their user and their work stay.
						</span>
					</div>
					<Button theme="red" label="Remove" @click="remove" />
				</div>
			</section>
		</template>
	</RecordFrame>

	<Dialog
		v-model:open="linkOpen"
		title="Send them this link"
		:actions="[{ label: 'Copy link', variant: 'solid', onClick: copyLink }]"
	>
		<p class="text-base text-ink-gray-7">
			Pass this link on to {{ data?.full_name }} yourself. It lets them set a password once.
		</p>
		<p class="mt-3 break-all rounded bg-surface-gray-2 px-2 py-1.5 text-sm text-ink-gray-8">
			{{ link }}
		</p>
	</Dialog>
</template>

<script setup>
// One person on the team: their role, the open work they hold, and how they sign in. Managers
// change the role, email a password reset or set a temporary password, and take them off the team.
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { Button, Dialog, Skeleton, dialog, toast } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import { formatDate } from "@/lib/format";
import { listRoute } from "@/lib/listFilters";
import { ROLES, personRow } from "@/lib/people";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ user: { type: String, required: true } });
const router = useRouter();

const data = ref(null);
const error = ref("");
const saving = ref(false);
const sending = ref(false);
const linkOpen = ref(false);
const link = ref("");

const changeable = computed(() => data.value && !data.value.is_me && !data.value.locked);

const facts = computed(() => {
	if (!data.value) return [];
	const row = personRow(data.value);
	return [
		{ label: "Email", icon: "lucide-mail", value: data.value.user },
		{ label: "Role", icon: "lucide-badge-check", value: data.value.role },
		{
			label: "Last signed in",
			icon: "lucide-log-in",
			value: data.value.last_login ? formatDate(data.value.last_login) : "Not yet",
		},
		{
			label: "Status",
			icon: "lucide-activity",
			value: row.status,
			tone: row.theme === "green" ? "green" : row.theme === "amber" ? "amber" : "plain",
		},
	];
});

async function load() {
	error.value = "";
	try {
		data.value = await call("kxcompliance.api.person", { user: props.user });
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this person", "opened") : err.message;
	}
}

async function changeRole(role) {
	if (role === data.value.role) return;
	saving.value = true;
	try {
		await call(
			"kxcompliance.api.set_person_role",
			{ user: props.user, role },
			{ httpMethod: "POST" }
		);
		data.value.role = role;
		toast.success(`${data.value.full_name} is now ${role}`);
	} catch (err) {
		toast.error(err.message);
	} finally {
		saving.value = false;
	}
}

async function newLink() {
	try {
		const result = await call(
			"kxcompliance.api.new_sign_in_link",
			{ user: props.user },
			{ httpMethod: "POST" }
		);
		link.value = result.link;
		linkOpen.value = true;
	} catch (err) {
		toast.error(err.message);
	}
}

async function copyLink() {
	await navigator.clipboard.writeText(link.value);
	toast.success("Link copied");
}

async function sendReset() {
	sending.value = true;
	try {
		await call(
			"kxcompliance.api.send_password_reset",
			{ user: props.user },
			{ httpMethod: "POST" }
		);
		toast.success(`Reset email sent to ${data.value.user}`);
	} catch (err) {
		toast.error(err.message);
	} finally {
		sending.value = false;
	}
}

function askPassword() {
	dialog.prompt({
		title: "Set a temporary password",
		message: `At least 8 characters. Tell ${data.value.full_name} in person, and ask them to change it once they are in.`,
		confirmLabel: "Set password",
		fields: [{ name: "password", label: "Password", type: "password", required: true }],
		onConfirm: async ({ values }) => {
			try {
				await call(
					"kxcompliance.api.set_temporary_password",
					{ user: props.user, password: values.password },
					{ httpMethod: "POST" }
				);
				toast.success("Password set. They have been signed out everywhere.");
			} catch (err) {
				// Shown inside the dialog, which stays open to try another password.
				throw new Error(err.message);
			}
		},
	});
}

function remove() {
	dialog.confirm({
		title: "Remove from the team",
		message: `${data.value.full_name} can no longer open the app. Filings and items they hold stay as they are; give them to someone else from each record.`,
		confirmLabel: "Remove",
		theme: "red",
		onConfirm: async () => {
			try {
				await call(
					"kxcompliance.api.remove_person",
					{ user: props.user },
					{ httpMethod: "POST" }
				);
				toast.success(`${data.value.full_name} is off the team`);
				router.push({ name: "People" });
			} catch (err) {
				toast.error(err.message);
			}
		},
	});
}

watch(() => props.user, load);
onMounted(load);
</script>
