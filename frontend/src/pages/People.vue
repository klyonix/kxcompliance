<template>
	<AppPageHeader title="People" :parent="{ label: 'Settings', route: { name: 'Settings' } }">
		<template #actions>
			<Button
				variant="solid"
				icon-left="lucide-user-plus"
				:label="isMobile ? 'Invite' : 'Invite someone'"
				data-tour="people-invite"
				@click="inviting = true"
			/>
		</template>
	</AppPageHeader>

	<div class="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 py-6 sm:px-6">
		<p class="text-base text-ink-gray-6">
			Everyone who works in the app. Managers set things up and approve; staff prepare
			filings and keep the register; auditors can read everything and change nothing.
		</p>
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!people" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton v-for="index in 4" :key="index" class="h-12 w-full rounded-lg" />
		</div>
		<RowList
			v-else
			paged="people"
			data-tour="people-list"
			:groups="groups"
			:columns="[{ label: 'Last signed in' }]"
			:date-label="null"
			actions-width="sm:w-44"
		>
			<template #actions="{ row }">
				<!-- Someone off the team has no role: their row opens their page, to hand work over. -->
				<span v-if="row.person.on_team === false" class="text-sm text-ink-gray-5"
					>Hand over</span
				>
				<FormControl
					v-else-if="!row.person.is_me && !row.person.locked"
					:model-value="row.person.role"
					type="select"
					class="w-32"
					:aria-label="`Role of ${row.person.full_name}`"
					:options="ROLES.map((role) => ({ label: role.label, value: role.label }))"
					@update:model-value="(role) => changeRole(row.person, role)"
				/>
				<span v-else class="text-sm text-ink-gray-6">{{
					row.person.locked ? `${row.person.role} · admin` : row.person.role
				}}</span>
				<Dropdown
					v-if="row.person.on_team !== false && !row.person.is_me && !row.person.locked"
					:options="menuFor(row.person)"
					align="end"
				>
					<Button
						variant="ghost"
						icon="lucide-ellipsis"
						:label="`More for ${row.person.full_name}`"
					/>
				</Dropdown>
			</template>
		</RowList>
	</div>

	<Dialog
		v-model:open="inviting"
		title="Invite someone"
		:actions="[{ label: 'Invite', variant: 'solid', onClick: ({ close }) => invite(close) }]"
	>
		<form class="flex flex-col gap-4" @submit.prevent>
			<FormControl v-model="form.full_name" label="Name" placeholder="Neha Joshi" />
			<FormControl
				v-model="form.email"
				type="email"
				label="Email"
				placeholder="neha@yourfirm.in"
			/>
			<fieldset class="flex flex-col gap-2">
				<legend class="mb-1 text-xs text-ink-gray-5">Role</legend>
				<label
					v-for="role in ROLES"
					:key="role.label"
					class="flex cursor-pointer items-start gap-2 rounded-lg px-2 py-1.5 hover:bg-surface-gray-2"
				>
					<input
						v-model="form.role"
						type="radio"
						name="role"
						:value="role.label"
						class="mt-1"
					/>
					<span class="flex flex-col">
						<span class="text-base text-ink-gray-8">{{ role.label }}</span>
						<span class="text-sm text-ink-gray-5">{{ role.detail }}</span>
					</span>
				</label>
			</fieldset>
			<p v-if="inviteError" role="alert" class="text-sm text-ink-red-4">{{ inviteError }}</p>
		</form>
	</Dialog>

	<Dialog
		v-model:open="linkOpen"
		title="Send them this link"
		:actions="[{ label: 'Copy link', variant: 'solid', onClick: copyLink }]"
	>
		<div class="flex flex-col gap-3">
			<p class="text-base text-ink-gray-7">
				This site cannot send email yet, so pass this link on to {{ link.name }} yourself,
				by WhatsApp or email. It lets them set a password and sign in, and works once.
			</p>
			<p
				class="break-all rounded-lg bg-surface-gray-2 px-3 py-2 font-mono text-sm text-ink-gray-8"
			>
				{{ link.url }}
			</p>
			<p class="text-sm text-ink-gray-5">
				Once an email account is set up in Settings, new people get their invitation by
				email.
			</p>
		</div>
	</Dialog>
</template>

<script setup>
// The team: who works in the app and in which role. Managers invite people, change a role, and
// take someone off the team; an administrator's access stays in the Desk.
import { computed, onMounted, reactive, ref } from "vue";
import { Button, Dialog, Dropdown, FormControl, Skeleton, dialog, toast } from "frappe-ui";
import { call } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RowList from "@/components/RowList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { ROLES, personRow } from "@/lib/people";
import { notLoaded } from "@/offline/reachability";

const isMobile = useIsMobile();
const people = ref(null);
// The team, then anyone taken off it who still holds open work, to hand it over.
const former = ref([]);
const groups = computed(() => [
	{ key: "team", label: "", rows: people.value.map(personRow) },
	...(former.value.length
		? [
				{
					key: "former",
					label: "No longer on the team, still holding work",
					rows: former.value.map((person) => ({
						...personRow(person),
						status: "Off the team",
						theme: "amber",
					})),
				},
		  ]
		: []),
]);
const error = ref("");
const inviting = ref(false);
const inviteError = ref("");
const form = reactive({ full_name: "", email: "", role: "Staff" });
const linkOpen = ref(false);
const link = reactive({ name: "", url: "" });

function showLink(name, url) {
	Object.assign(link, { name, url });
	linkOpen.value = true;
}

async function copyLink() {
	await navigator.clipboard.writeText(link.url);
	toast.success("Link copied");
}

async function load() {
	try {
		[people.value, former.value] = await Promise.all([
			call("kxcompliance.api.team"),
			call("kxcompliance.api.former_people").catch(() => []),
		]);
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("the team") : err.message;
	}
}

async function invite(close) {
	inviteError.value = "";
	if (!form.full_name.trim() || !form.email.trim()) {
		inviteError.value = "Give their name and email.";
		return;
	}
	try {
		const result = await call(
			"kxcompliance.api.invite_person",
			{ ...form },
			{ httpMethod: "POST" }
		);
		close();
		toast.success(
			result.emailed ? `Invitation sent to ${form.email}` : `${form.full_name} added`
		);
		if (result.link) showLink(form.full_name, result.link);
		Object.assign(form, { full_name: "", email: "", role: "Staff" });
		await load();
	} catch (err) {
		inviteError.value = err.message;
	}
}

async function changeRole(person, role) {
	try {
		await call(
			"kxcompliance.api.set_person_role",
			{ user: person.user, role },
			{ httpMethod: "POST" }
		);
		toast.success(`${person.full_name} is now ${role}`);
	} catch (err) {
		toast.error(err.message);
	}
	await load();
}

function menuFor(person) {
	const options = [];
	if (!person.last_login) {
		options.push({
			label: "New sign-in link",
			icon: "lucide-link",
			onClick: () => newLink(person),
		});
	}
	options.push({
		label: "Remove from the team",
		icon: "lucide-user-minus",
		onClick: () => removePerson(person),
	});
	return options;
}

async function newLink(person) {
	try {
		const result = await call(
			"kxcompliance.api.new_sign_in_link",
			{ user: person.user },
			{ httpMethod: "POST" }
		);
		showLink(person.full_name, result.link);
	} catch (err) {
		toast.error(err.message);
	}
}

function removePerson(person) {
	dialog.confirm({
		title: "Remove from the team",
		message: `${person.full_name} can no longer open the app. Filings and items they hold stay as they are; give them to someone else from each record.`,
		confirmLabel: "Remove",
		onConfirm: async () => {
			try {
				await call(
					"kxcompliance.api.remove_person",
					{ user: person.user },
					{ httpMethod: "POST" }
				);
				toast.success(`${person.full_name} removed from the team`);
			} catch (err) {
				toast.error(err.message);
			}
			await load();
		},
	});
}

onMounted(load);
</script>
