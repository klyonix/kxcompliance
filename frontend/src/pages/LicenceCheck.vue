<template>
	<AppPageHeader
		:title="party ? check?.party_name || party : 'Licence Check'"
		:parent="party ? { label: 'Licence Check', route: { query: {} } } : null"
	>
		<template v-if="party" #actions>
			<!-- A phone's header keeps the name: the button is its icon alone there. -->
			<Button
				v-if="isMobile"
				variant="ghost"
				icon="lucide-search"
				label="Check another"
				:route="{ query: {} }"
			/>
			<Button
				v-else
				icon-left="lucide-search"
				label="Check another"
				:route="{ query: {} }"
			/>
		</template>
	</AppPageHeader>

	<!-- Finding the customer or supplier. -->
	<div v-if="!party" class="mx-auto flex w-full max-w-5xl flex-col gap-4 px-4 py-6 sm:px-6">
		<p class="max-w-3xl text-base text-ink-gray-6">
			Find a {{ boot.partyTypes.length > 1 ? "customer or supplier" : partyLabel }} to see
			whether a sale or purchase would go through, and which licences they hold.
		</p>
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
			<TabButtons
				v-if="boot.partyTypes.length > 1"
				v-model="partyType"
				:options="boot.partyTypes.map((value) => ({ label: `${value}s`, value }))"
			/>
			<TextInput
				v-model="search"
				type="search"
				class="flex-1 sm:max-w-sm"
				:placeholder="`Search ${partyLabel}s by name or ID`"
				:aria-label="`Search ${partyLabel}s`"
			>
				<template #prefix
					><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
		</div>

		<p v-if="searchError" role="alert" class="text-base text-ink-red-4">
			{{ searchError }}
		</p>
		<div v-else-if="searching && !results.length" class="flex flex-col gap-3">
			<Skeleton v-for="index in 4" :key="index" class="h-10 w-full rounded-lg" />
		</div>
		<div
			v-else-if="!results.length"
			class="flex flex-col items-center gap-2 py-16 text-center"
		>
			<span
				class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
			>
				<span class="lucide-search-x size-6" aria-hidden="true" />
			</span>
			<p class="text-lg font-medium text-ink-gray-8">
				{{
					search.trim()
						? `No ${partyLabel} matches “${search.trim()}”`
						: `No ${partyLabel}s yet`
				}}
			</p>
			<p v-if="search.trim()" class="max-w-sm text-base text-ink-gray-5">
				Try part of the name or the ID.
			</p>
			<template v-else>
				<p class="max-w-sm text-base text-ink-gray-5">
					Licence Check works from the {{ partyLabel }}s kept in ERPNext. If you bill
					from another system, import them once from a spreadsheet of their names; their
					licences are then recorded and checked here.
				</p>
				<Button
					:link="deskPath(`data-import/new?reference_doctype=${partyType}`)"
					icon-left="lucide-upload"
					:label="`Import ${partyLabel}s`"
				/>
			</template>
		</div>
		<RowList
			v-else
			:rows="results.map((result) => partyRow(result, partyType))"
			:name-label="partyType"
			:columns="[{ label: 'Group' }]"
			:status-label="null"
			:date-label="null"
		/>
		<ListPager
			v-if="results.length || page > 1"
			v-model:page="page"
			v-model:size="pageSize"
			:total="total"
			:loading="searching"
		/>
	</div>

	<!-- One customer's or supplier's check. -->
	<RecordFrame v-else :facts="facts">
		<p
			v-if="checkError"
			role="alert"
			class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
		>
			{{ checkError }}
		</p>
		<div v-else-if="!check" class="flex flex-col gap-3" aria-busy="true">
			<Skeleton class="h-20 w-full rounded-xl" />
			<Skeleton class="h-28 w-full rounded-lg" />
			<Skeleton class="h-16 w-full rounded-lg" />
		</div>

		<template v-else>
			<section
				class="flex items-start gap-4 rounded-xl px-4 py-4"
				:class="VERDICT_STYLES[answer.theme].box"
				role="status"
			>
				<span
					class="flex size-10 shrink-0 items-center justify-center rounded-full"
					:class="VERDICT_STYLES[answer.theme].icon"
				>
					<span :class="answer.icon" class="size-5" aria-hidden="true" />
				</span>
				<div class="flex flex-col gap-0.5">
					<p class="text-lg font-semibold">{{ answer.title }}</p>
					<p v-if="answer.detail" class="text-base">{{ answer.detail }}</p>
					<p class="text-sm opacity-80">
						Checked for {{ formatDate(check.checked_on) }}.
					</p>
				</div>
			</section>

			<section
				v-if="check.requirements.length"
				class="flex flex-col gap-3"
				aria-labelledby="needed-heading"
			>
				<h2 id="needed-heading" class="text-base font-semibold text-ink-gray-8">
					Licences needed
				</h2>
				<ul class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<li
						v-for="requirement in check.requirements"
						:key="requirement.item_type"
						class="flex flex-col gap-2 rounded-lg border border-outline-gray-1 px-4 py-3"
					>
						<div class="flex items-start gap-2">
							<span
								class="mt-0.5 size-4 shrink-0"
								:class="[
									STATUS_ICONS[requirementState(requirement).theme],
									STATUS_TEXT[requirementState(requirement).theme],
								]"
								aria-hidden="true"
							/>
							<span class="flex-1 text-base font-medium text-ink-gray-8">{{
								requirement.item_type
							}}</span>
							<Badge v-bind="requirementState(requirement)" />
						</div>
						<p class="text-sm text-ink-gray-6">
							{{ requirement.action === "Block" ? "Blocks" : "Warns" }}
							<template v-if="requirement.grace_days">
								· {{ requirement.grace_days }} days' grace</template
							>
							· {{ coverage(requirement) }}
						</p>
						<p v-if="requirement.message" class="text-sm text-ink-gray-7">
							{{ requirement.message }}
						</p>
					</li>
				</ul>
			</section>

			<section class="flex flex-col gap-3" aria-labelledby="held-heading">
				<h2 id="held-heading" class="text-base font-semibold text-ink-gray-8">
					Licences held
				</h2>
				<p v-if="!check.licences.length" class="text-base text-ink-gray-5">
					None recorded.
				</p>
				<RowList
					v-else
					paged="licences-held"
					:rows="
						check.licences.map((licence) =>
							heldRow(licence, check.checked_on, { linked: !checksOnly() })
						)
					"
					name-label="Licence"
					:date-label="null"
				/>
			</section>
		</template>
	</RecordFrame>
</template>

<script setup>
// Licence Check: find a customer or supplier, then see whether a sale or purchase with them
// would go through today, the licences it needs and the ones they hold.
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Badge, Button, Skeleton, TabButtons, TextInput } from "frappe-ui";
import { call } from "@/api";
import { boot, checksOnly } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import RecordFrame from "@/components/RecordFrame.vue";
import ListPager from "@/components/ListPager.vue";
import RowList from "@/components/RowList.vue";
import { useIsMobile } from "@/composables/useIsMobile";
import { deskPath } from "@/navigation";
import { formatDate } from "@/lib/format";
import { savePageSize, savedPageSize } from "@/lib/paging";
import { coverage, heldRow, partyRow, requirementState, verdict } from "@/lib/licenceCheck";
import { STATUS_ICONS } from "@/lib/status";
import { notLoaded } from "@/offline/reachability";

// The answer's colours, and its icon on a stronger tint of the same.
const VERDICT_STYLES = {
	red: { box: "bg-surface-red-1 text-ink-red-7", icon: "bg-surface-red-2 text-ink-red-6" },
	amber: {
		box: "bg-surface-amber-1 text-ink-amber-7",
		icon: "bg-surface-amber-2 text-ink-amber-7",
	},
	green: {
		box: "bg-surface-green-1 text-ink-green-7",
		icon: "bg-surface-green-2 text-ink-green-7",
	},
	gray: { box: "bg-surface-gray-2 text-ink-gray-7", icon: "bg-surface-gray-3 text-ink-gray-7" },
};
const STATUS_TEXT = {
	red: "text-ink-red-4",
	amber: "text-ink-amber-5",
	green: "text-ink-green-5",
	gray: "text-ink-gray-5",
};

const route = useRoute();
const isMobile = useIsMobile();

const partyType = ref(
	boot.partyTypes.includes(route.query.party_type) ? route.query.party_type : boot.partyTypes[0]
);
const party = computed(() => route.query.party || "");
const partyLabel = computed(() => partyType.value.toLowerCase());

const search = ref("");
const results = ref([]);
// The search's page, page size (remembered on this device) and how many it finds in all.
const page = ref(1);
const pageSize = ref(savedPageSize("licence-check"));
const total = ref(0);
const searching = ref(false);
const searchError = ref("");

const check = ref(null);
const checkError = ref("");
const answer = computed(() => (check.value ? verdict(check.value) : null));

// The band across the top of a check.
const facts = computed(() => {
	if (!check.value) return [];
	const current = check.value;
	const failing = current.requirements.filter((row) => row.result !== "ok").length;
	return [
		{
			label: partyType.value,
			icon: partyType.value === "Supplier" ? "lucide-truck" : "lucide-store",
			value: current.party,
		},
		{ label: "Group", icon: "lucide-folder", value: current.party_group || "None" },
		{
			label: "Licences needed",
			icon: "lucide-shield-check",
			value: failing
				? `${failing} of ${current.requirements.length} missing`
				: String(current.requirements.length),
			tone: failing ? "red" : "plain",
		},
		{
			label: "Licences held",
			icon: "lucide-file-badge",
			value: String(current.licences.length),
		},
	];
});

const friendly = (err, what) => (err.isNetwork ? notLoaded(what) : err.message);

let typing;
let latest = 0;
async function findParties() {
	const ticket = ++latest;
	searching.value = true;
	searchError.value = "";
	try {
		const asked = { party_type: partyType.value, text: search.value };
		const [found, count] = await Promise.all([
			call("kxcompliance.api.search_parties", {
				...asked,
				start: (page.value - 1) * pageSize.value,
				page_length: pageSize.value,
			}),
			call("kxcompliance.api.count_parties", asked),
		]);
		// A slower earlier search must not replace the answer to a later one.
		if (ticket === latest) {
			results.value = found;
			total.value = count;
		}
	} catch (err) {
		if (ticket === latest) searchError.value = friendly(err, "this search");
	} finally {
		if (ticket === latest) searching.value = false;
	}
}

async function runCheck() {
	check.value = null;
	checkError.value = "";
	if (!party.value) return;
	try {
		check.value = await call("kxcompliance.api.check_party", {
			party_type: partyType.value,
			party: party.value,
		});
	} catch (err) {
		checkError.value = friendly(err, "this check");
	}
}

// A new search starts from its first page; the page watcher searches, or it is searched here.
function fromFirstPage() {
	if (page.value !== 1) page.value = 1;
	else findParties();
}
watch(search, () => {
	clearTimeout(typing);
	typing = setTimeout(fromFirstPage, 250);
});
watch(partyType, () => {
	results.value = [];
	fromFirstPage();
});
watch([page, pageSize], findParties);
watch(pageSize, (size) => savePageSize("licence-check", size));
watch(
	() => route.query,
	(query) => {
		if (boot.partyTypes.includes(query.party_type)) partyType.value = query.party_type;
		runCheck();
	}
);
onMounted(() => {
	findParties();
	runCheck();
});
</script>
