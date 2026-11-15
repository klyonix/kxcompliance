<template>
	<AppPageHeader :title="name ? `Edit ${name}` : 'New client'" :parent="parent" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-6 sm:px-6">
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ error }}
		</p>
		<div v-else-if="!ready" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-6 w-1/3 rounded" />
			<Skeleton class="h-40 w-full rounded-lg" />
		</div>

		<template v-else>
			<section class="flex flex-col gap-4" aria-labelledby="client-heading">
				<h2 id="client-heading" class="text-base font-semibold text-ink-gray-8">Client</h2>
				<FormControl
					v-if="!name"
					v-model="form.client_name"
					label="Name"
					placeholder="Sunrise Group"
					:error="checking && !form.client_name.trim() ? 'Give the client a name' : ''"
				/>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<FormControl
						v-model="form.client_kind"
						type="select"
						label="Kind"
						:options="KINDS"
					/>
					<FormControl
						v-if="name"
						v-model="form.status"
						type="select"
						label="Status"
						:options="STATUSES"
					/>
					<FormControl
						v-model="form.relationship_manager"
						type="select"
						label="Relationship manager"
						:options="[{ label: 'None', value: '' }, ...peopleOptions]"
					/>
					<FormControl
						v-model="form.contact_email"
						type="email"
						label="Contact email"
						placeholder="accounts@client.example.com"
						description="Without a login, the client is asked for documents and reminded here, and can reply with the file."
					/>
					<FormControl v-model="form.contact_phone" label="Contact phone" />
				</div>
				<FormControl
					v-model="form.licence_check"
					type="checkbox"
					label="Check their customers' and suppliers' licences"
					description="Sales and purchases of this client's companies are checked against your licence rules before they are saved."
				/>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="team-heading">
				<div class="flex flex-col gap-0.5">
					<h2 id="team-heading" class="text-base font-semibold text-ink-gray-8">Team</h2>
					<p class="text-sm text-ink-gray-5">
						The firm's people who work on this client see all its companies.
					</p>
				</div>
				<ul v-if="form.team.length" class="flex flex-col">
					<li
						v-for="user in form.team"
						:key="user"
						class="flex items-center gap-3 border-b border-outline-gray-1 py-2 last:border-b-0"
					>
						<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{
							nameOf(user)
						}}</span>
						<Button
							variant="ghost"
							icon="lucide-x"
							:label="`Take ${nameOf(user)} off the team`"
							@click="form.team = form.team.filter((member) => member !== user)"
						/>
					</li>
				</ul>
				<FormControl
					v-if="addablePeople.length"
					:model-value="''"
					type="select"
					:options="[{ label: 'Add someone to the team', value: '' }, ...addablePeople]"
					aria-label="Add someone to the team"
					@update:model-value="(user) => user && form.team.push(user)"
				/>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="logins-heading">
				<div class="flex flex-col gap-0.5">
					<h2 id="logins-heading" class="text-base font-semibold text-ink-gray-8">
						Client logins
					</h2>
					<p class="text-sm text-ink-gray-5">
						People at the client who may sign in to see their companies and upload
						documents. Each is emailed a link to set a password when saved.
					</p>
				</div>
				<div
					v-for="(login, index) in form.logins"
					:key="index"
					class="flex flex-col gap-2 rounded-lg bg-surface-gray-1 p-3 sm:flex-row sm:items-end"
				>
					<FormControl v-model="login.full_name" label="Name" class="sm:flex-1" />
					<FormControl
						v-model="login.email"
						type="email"
						label="Email"
						class="sm:flex-1"
						:disabled="Boolean(login.user)"
					/>
					<div class="flex items-center gap-2 sm:pb-1">
						<FormControl v-model="login.enabled" type="checkbox" label="Login on" />
						<Button
							variant="ghost"
							icon="lucide-trash-2"
							label="Remove login"
							@click="form.logins.splice(index, 1)"
						/>
					</div>
				</div>
				<div>
					<Button
						icon-left="lucide-plus"
						label="Add a login"
						@click="form.logins.push({ full_name: '', email: '', enabled: true })"
					/>
				</div>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="notes-heading">
				<h2 id="notes-heading" class="text-base font-semibold text-ink-gray-8">Notes</h2>
				<FormControl
					v-model="form.notes"
					type="textarea"
					:rows="3"
					placeholder="For the firm only; clients do not see these."
				/>
			</section>
		</template>
	</div>

	<div
		v-if="ready"
		class="sticky bottom-0 z-10 mt-auto border-t border-outline-gray-1 bg-surface-base"
	>
		<div
			class="mx-auto flex w-full max-w-3xl flex-col-reverse gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-end sm:px-6"
		>
			<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
				{{ saveError }}
			</p>
			<Button label="Cancel" @click="goBack(router, parent.route)" />
			<Button
				variant="solid"
				:label="name ? 'Save' : 'Add client'"
				:loading="saving"
				@click="save"
			/>
		</div>
	</div>
</template>

<script setup>
// Add a client, or change one: its details, the firm's team on it and the client's own logins.
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { Button, FormControl, Skeleton, toast } from "frappe-ui";
import { call, createDoc, getDoc, updateDoc } from "@/api";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { learnNames, nameOf } from "@/composables/usePeople";
import { personOptions } from "@/lib/people";
import { goBack } from "@/navigation";
import { notLoaded } from "@/offline/reachability";

const props = defineProps({ name: { type: String, default: "" } });

const KINDS = ["Business Group", "Individual"].map((value) => ({ label: value, value }));
const STATUSES = ["Active", "On Hold", "Left"].map((value) => ({ label: value, value }));

const router = useRouter();
const people = ref([]);
const ready = ref(false);
const error = ref("");
const saveError = ref("");
const saving = ref(false);
const checking = ref(false);
const form = reactive({
	client_name: "",
	client_kind: "Business Group",
	status: "Active",
	relationship_manager: "",
	contact_email: "",
	contact_phone: "",
	licence_check: false,
	team: [],
	logins: [],
	notes: "",
});

const parent = computed(() =>
	props.name
		? { label: props.name, route: { name: "Client", params: { name: props.name } } }
		: { label: "Clients", route: { name: "Clients" } }
);
const peopleOptions = computed(() => personOptions(people.value));
const addablePeople = computed(() =>
	peopleOptions.value.filter((option) => !form.team.includes(option.value))
);

function values() {
	return {
		client_kind: form.client_kind,
		relationship_manager: form.relationship_manager || null,
		contact_email: form.contact_email.trim() || null,
		contact_phone: form.contact_phone.trim() || null,
		licence_check: form.licence_check ? 1 : 0,
		team: form.team.map((user) => ({ user })),
		logins: form.logins.map((login) => ({
			full_name: login.full_name.trim(),
			email: login.email.trim(),
			enabled: login.enabled ? 1 : 0,
		})),
		notes: form.notes,
	};
}

async function save() {
	checking.value = true;
	saveError.value = "";
	if (!props.name && !form.client_name.trim()) return;
	saving.value = true;
	try {
		const saved = props.name
			? await updateDoc("Compliance Client", props.name, {
					...values(),
					status: form.status,
			  })
			: await createDoc("Compliance Client", {
					client_name: form.client_name.trim(),
					...values(),
			  });
		toast.success(props.name ? "Client saved" : "Client added");
		router.replace({ name: "Client", params: { name: saved.name } });
	} catch (err) {
		saveError.value = err.isNetwork
			? "The client did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		saving.value = false;
	}
}

onMounted(async () => {
	try {
		people.value = await call("kxcompliance.api.people_options");
		learnNames(people.value.map((person) => person.name));
		if (props.name) {
			const client = await getDoc("Compliance Client", props.name);
			Object.assign(form, {
				client_kind: client.client_kind || "Business Group",
				status: client.status || "Active",
				relationship_manager: client.relationship_manager || "",
				contact_email: client.contact_email || "",
				contact_phone: client.contact_phone || "",
				licence_check: Boolean(client.licence_check),
				team: client.team.map((row) => row.user),
				logins: client.logins.map((row) => ({
					full_name: row.full_name,
					email: row.email,
					enabled: Boolean(row.enabled),
					user: row.user,
				})),
				notes: client.notes || "",
			});
		}
		ready.value = true;
	} catch (err) {
		error.value = err.isNetwork ? notLoaded("this client", "opened") : err.message;
	}
});
</script>
