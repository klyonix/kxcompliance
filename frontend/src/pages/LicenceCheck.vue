<template>
	<AppPageHeader title="Licence Check" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
		<template v-if="!party">
			<p class="text-base text-ink-gray-6">
				Find a {{ boot.partyTypes.length > 1 ? "customer or supplier" : partyLabel }} to
				see whether a sale or purchase would go through, and which licences they hold.
			</p>
			<div class="flex flex-col gap-3 sm:flex-row sm:items-center">
				<TabButtons
					v-if="boot.partyTypes.length > 1"
					v-model="partyType"
					:options="boot.partyTypes.map((value) => ({ label: value, value }))"
				/>
				<TextInput
					v-model="search"
					type="search"
					class="flex-1"
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
			<p v-else-if="!results.length" class="py-10 text-center text-base text-ink-gray-5">
				{{ search.trim() ? `No ${partyLabel} matches “${search.trim()}”.` : "" }}
			</p>
			<ul v-else class="flex flex-col gap-1">
				<li v-for="result in results" :key="result.name">
					<RouterLink
						:to="{ query: { party_type: partyType, party: result.name } }"
						class="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
					>
						<Avatar :label="result.party_name || result.name" size="lg" />
						<span class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-base font-medium text-ink-gray-8">{{
								result.party_name || result.name
							}}</span>
							<span class="truncate text-sm text-ink-gray-5">{{
								[
									result.name !== result.party_name && result.name,
									result.party_group,
								]
									.filter(Boolean)
									.join(" · ")
							}}</span>
						</span>
						<span
							class="lucide-chevron-right size-4 text-ink-gray-4"
							aria-hidden="true"
						/>
					</RouterLink>
				</li>
			</ul>
		</template>

		<template v-else>
			<div class="flex items-center gap-3">
				<Avatar :label="check?.party_name || party" size="xl" />
				<div class="flex min-w-0 flex-1 flex-col">
					<span class="truncate text-lg font-semibold text-ink-gray-8">{{
						check?.party_name || party
					}}</span>
					<span class="truncate text-sm text-ink-gray-5">{{
						[partyType, check?.party_group].filter(Boolean).join(" · ")
					}}</span>
				</div>
				<Button label="Check another" :route="{ query: {} }" />
			</div>

			<p
				v-if="checkError"
				role="alert"
				class="rounded-lg bg-surface-red-1 px-3 py-2 text-base text-ink-red-4"
			>
				{{ checkError }}
			</p>
			<div v-else-if="!check" class="flex flex-col gap-3" aria-busy="true">
				<Skeleton class="h-20 w-full rounded-lg" />
				<Skeleton class="h-16 w-full rounded-lg" />
				<Skeleton class="h-16 w-full rounded-lg" />
			</div>

			<template v-else>
				<section
					class="flex items-start gap-3 rounded-lg px-4 py-3"
					:class="VERDICT_STYLES[answer.theme]"
					role="status"
				>
					<span :class="answer.icon" class="mt-0.5 size-5 shrink-0" aria-hidden="true" />
					<div class="flex flex-col gap-0.5">
						<p class="text-base font-semibold">{{ answer.title }}</p>
						<p v-if="answer.detail" class="text-base">{{ answer.detail }}</p>
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
					<ul class="flex flex-col">
						<li
							v-for="requirement in check.requirements"
							:key="requirement.item_type"
							class="flex flex-col gap-1 border-b border-outline-gray-1 py-3 last:border-b-0"
						>
							<div class="flex flex-wrap items-center gap-2">
								<span class="text-base font-medium text-ink-gray-8">{{
									requirement.item_type
								}}</span>
								<Badge v-bind="requirementState(requirement)" />
								<span class="text-sm text-ink-gray-5">
									{{ requirement.action === "Block" ? "Blocks" : "Warns" }}
									<template v-if="requirement.grace_days">
										· {{ requirement.grace_days }} days' grace</template
									>
								</span>
							</div>
							<p class="text-sm text-ink-gray-6">{{ coverage(requirement) }}</p>
							<p v-if="requirement.message" class="text-base text-ink-gray-7">
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
					<ul v-else class="flex flex-col">
						<li
							v-for="(licence, index) in check.licences"
							:key="index"
							class="flex items-center gap-3 border-b border-outline-gray-1 py-2.5 last:border-b-0"
						>
							<span class="flex min-w-0 flex-1 flex-col">
								<span class="truncate text-base text-ink-gray-8">{{
									licence.item_type
								}}</span>
								<span class="truncate text-sm text-ink-gray-5">{{
									[
										licence.reference_number,
										licenceState(licence, check.checked_on).detail,
									]
										.filter(Boolean)
										.join(" · ")
								}}</span>
							</span>
							<Badge v-bind="licenceState(licence, check.checked_on)" />
						</li>
					</ul>
				</section>

				<p class="text-sm text-ink-gray-5">
					Checked for {{ formatDate(check.checked_on) }}.
				</p>
			</template>
		</template>
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Avatar, Badge, Button, Skeleton, TabButtons, TextInput } from "frappe-ui";
import { call } from "@/api";
import { boot } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { formatDate } from "@/lib/format";
import { coverage, licenceState, requirementState, verdict } from "@/lib/licenceCheck";
import { notLoaded } from "@/offline/reachability";

const VERDICT_STYLES = {
	red: "bg-surface-red-1 text-ink-red-7",
	amber: "bg-surface-amber-1 text-ink-amber-7",
	green: "bg-surface-green-1 text-ink-green-7",
	gray: "bg-surface-gray-2 text-ink-gray-7",
};

const route = useRoute();

const partyType = ref(
	boot.partyTypes.includes(route.query.party_type) ? route.query.party_type : boot.partyTypes[0]
);
const party = computed(() => route.query.party || "");
const partyLabel = computed(() => partyType.value.toLowerCase());

const search = ref("");
const results = ref([]);
const searching = ref(false);
const searchError = ref("");

const check = ref(null);
const checkError = ref("");
const answer = computed(() => (check.value ? verdict(check.value) : null));

const friendly = (err, what) => (err.isNetwork ? notLoaded(what) : err.message);

let typing;
let latest = 0;
async function findParties() {
	const ticket = ++latest;
	searching.value = true;
	searchError.value = "";
	try {
		const found = await call("compliance_plus.api.search_parties", {
			party_type: partyType.value,
			text: search.value,
		});
		// A slower earlier search must not replace the answer to a later one.
		if (ticket === latest) results.value = found;
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
		check.value = await call("compliance_plus.api.check_party", {
			party_type: partyType.value,
			party: party.value,
		});
	} catch (err) {
		checkError.value = friendly(err, "this check");
	}
}

watch(search, () => {
	clearTimeout(typing);
	typing = setTimeout(findParties, 250);
});
watch(partyType, () => {
	results.value = [];
	findParties();
});
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
