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
			<PersonPhoto
				v-model="data.user_image"
				:user="data.user"
				:name="data.full_name"
				:editable="!data.locked || data.is_me"
			/>
			<p
				v-if="!data.on_team"
				class="rounded-lg bg-surface-amber-1 px-3 py-2 text-base text-ink-amber-7"
			>
				No longer on the team, but still holding open work. Hand it over to someone below.
			</p>
			<!-- Their own role, or an administrator's, is changed elsewhere: say so instead. -->
			<p
				v-else-if="!changeable"
				class="rounded-lg bg-surface-gray-2 px-3 py-2 text-base text-ink-gray-7"
			>
				{{
					data.is_me
						? "This is you. Another manager changes your role or password."
						: "An administrator. Their access is changed in the Desk."
				}}
			</p>

			<section
				v-if="data.on_team"
				class="flex flex-col gap-3"
				aria-labelledby="role-heading"
			>
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
			</section>

			<!-- Leaving, on leave or moving to other clients: everything open goes to one person. -->
			<section
				v-if="!data.is_me && handingOver.length"
				class="flex flex-col gap-3"
				aria-labelledby="handover-heading"
			>
				<div class="flex flex-col gap-0.5">
					<h2 id="handover-heading" class="text-base font-semibold text-ink-gray-8">
						Hand over their work
					</h2>
					<p class="text-sm text-ink-gray-5">
						Everything still open moves to one person, with their places on companies,
						obligations and clients. Work already done stays with them.
					</p>
				</div>
				<ul
					class="flex flex-col rounded-lg border border-outline-gray-1 px-3 py-1 [&>*+*]:border-t [&>*+*]:border-outline-gray-1"
				>
					<li
						v-for="kind in handingOver"
						:key="kind.label"
						class="flex items-center justify-between gap-3 py-2 text-base"
					>
						<span class="text-ink-gray-7">{{ kind.label }}</span>
						<span class="font-medium tabular-nums text-ink-gray-8">{{
							kind.count
						}}</span>
					</li>
				</ul>
				<div class="flex flex-col gap-2 sm:flex-row sm:items-end">
					<FormControl
						v-model="handTo"
						type="select"
						class="sm:w-72"
						label="Give it to"
						:options="[{ label: 'Choose someone', value: '' }, ...takers]"
					/>
					<Button
						variant="solid"
						label="Hand over"
						:disabled="!handTo"
						:loading="handing"
						@click="handOver"
					/>
				</div>
			</section>

			<section
				v-if="changeable && data.enabled"
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
					class="flex flex-col gap-2 rounded-lg border px-3 py-3 sm:flex-row sm:items-center"
					:class="data.enabled ? 'border-outline-red-1' : 'border-outline-gray-2'"
				>
					<div class="flex flex-1 flex-col gap-0.5">
						<span class="text-base font-medium text-ink-gray-8">
							{{ data.enabled ? "Switch off" : "Switched off" }}
						</span>
						<span class="text-sm text-ink-gray-5">
							{{
								data.enabled
									? "They can no longer sign in. Their role, records and history stay; switch them on again any time."
									: "They cannot sign in. Switch them on to let them back, with the role they had."
							}}
						</span>
					</div>
					<Button
						:theme="data.enabled ? 'red' : 'gray'"
						:variant="data.enabled ? 'subtle' : 'solid'"
						:label="data.enabled ? 'Switch off' : 'Switch on'"
						:loading="switching"
						@click="switchSignIn(!data.enabled)"
					/>
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
import { RouterLink } from "vue-router";
import { Button, Dialog, FormControl, Skeleton, dialog, toast } from "frappe-ui";
import { call } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import PersonPhoto from "@/components/PersonPhoto.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import { formatDate } from "@/lib/format";
import { listRoute } from "@/lib/listFilters";
import { personOptions, personRow, roleChoices, switchWords } from "@/lib/people";
import { notLoaded } from "@/offline/reachability";

const ROLES = roleChoices(boot.accountType === "CA/CS Firm");

const props = defineProps({ user: { type: String, required: true } });

const data = ref(null);
const error = ref("");
const saving = ref(false);
const sending = ref(false);
const linkOpen = ref(false);
const link = ref("");

const changeable = computed(
	() => data.value && data.value.on_team && !data.value.is_me && !data.value.locked
);
// What a hand-over would move, kind by kind; and who on the team could take it.
const handingOver = computed(() => (data.value?.handover || []).filter((kind) => kind.count));
const takers = ref([]);
const handTo = ref("");
const handing = ref(false);

const facts = computed(() => {
	if (!data.value) return [];
	const row = personRow(data.value);
	return [
		{ label: "Email", icon: "lucide-mail", value: data.value.user },
		{ label: "Role", icon: "lucide-badge-check", value: data.value.role || "Off the team" },
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

async function loadTakers() {
	try {
		const team = await call("kxcompliance.api.people_options");
		takers.value = personOptions(team.filter((person) => person.name !== props.user));
	} catch {
		// Without the list nobody can be chosen; the rest of the page still works.
		takers.value = [];
	}
}

function handOver() {
	const to = takers.value.find((option) => option.value === handTo.value);
	const total = handingOver.value.reduce((sum, kind) => sum + kind.count, 0);
	dialog.confirm({
		title: "Hand over their work",
		message: `Everything open of ${data.value.full_name}'s (${total} in all) moves to ${to?.label}. It runs in the background; you are told when it is done.`,
		confirmLabel: "Hand over",
		onConfirm: async () => {
			handing.value = true;
			try {
				await call(
					"kxcompliance.api.hand_over_work",
					{ from_user: props.user, to_user: handTo.value },
					{ httpMethod: "POST" }
				);
				toast.success(`Handing over to ${to?.label}. You will be told when it is done.`);
				handTo.value = "";
			} catch (err) {
				toast.error(err.message);
			} finally {
				handing.value = false;
			}
		},
	});
}

async function load() {
	error.value = "";
	try {
		data.value = await call("kxcompliance.api.person", { user: props.user });
		if (data.value.handover?.some((kind) => kind.count)) loadTakers();
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

const switching = ref(false);
function switchSignIn(on) {
	const words = switchWords(data.value, on);
	dialog.confirm({
		title: words.title,
		message: words.message,
		confirmLabel: words.confirmLabel,
		theme: on ? "gray" : "red",
		onConfirm: async () => {
			switching.value = true;
			try {
				await call(
					"kxcompliance.api.switch_person",
					{ user: props.user, enabled: on },
					{ httpMethod: "POST" }
				);
				data.value.enabled = on;
				toast.success(words.done);
			} catch (err) {
				toast.error(err.message);
			} finally {
				switching.value = false;
			}
		},
	});
}

watch(() => props.user, load);
onMounted(load);
</script>
