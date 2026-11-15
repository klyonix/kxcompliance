<template>
	<AppPageHeader title="Reports" />

	<div class="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 sm:px-6">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<p class="max-w-xl text-base text-ink-gray-6">
				The same reports as the Desk, so the numbers always agree. Each can be filtered and
				downloaded for a spreadsheet.
			</p>
			<TextInput
				v-model="query"
				type="search"
				class="w-full sm:w-64"
				placeholder="Find a report"
				aria-label="Find a report"
			>
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
			</TextInput>
		</div>

		<section
			v-if="recent.length && !query"
			class="flex flex-col gap-2"
			aria-labelledby="recent-reports-heading"
		>
			<h2 id="recent-reports-heading" class="text-sm font-semibold text-ink-gray-6">
				Opened lately
			</h2>
			<div class="flex flex-wrap gap-2">
				<Button
					v-for="report in recent"
					:key="report.slug"
					icon-left="lucide-history"
					:label="report.title"
					:route="{ name: 'Report', params: { report: report.slug } }"
				/>
			</div>
		</section>

		<p v-if="!groups.length" class="py-12 text-center text-base text-ink-gray-5">
			No report matches "{{ query }}".
		</p>
		<div v-else class="gap-4 lg:columns-2" data-tour="reports-list">
			<section
				v-for="group in groups"
				:key="group.area"
				class="mb-4 flex break-inside-avoid flex-col rounded-lg border border-outline-gray-1"
				:aria-labelledby="`area-${group.area}`"
			>
				<h2
					:id="`area-${group.area}`"
					class="flex items-center gap-2 border-b border-outline-gray-1 px-4 py-3 text-base font-semibold text-ink-gray-8"
				>
					<span
						:class="AREA_ICONS[group.area]"
						class="size-4 text-ink-gray-5"
						aria-hidden="true"
					/>
					{{ group.area }}
					<span class="text-sm font-normal text-ink-gray-5">{{
						group.reports.length
					}}</span>
				</h2>
				<ul class="flex flex-col p-1">
					<li v-for="report in group.reports" :key="report.slug">
						<RouterLink
							:to="{ name: 'Report', params: { report: report.slug } }"
							class="group flex items-center gap-3 rounded-md px-3 py-2.5 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
						>
							<span class="flex min-w-0 flex-1 flex-col gap-0.5">
								<span class="text-base font-medium text-ink-gray-8">{{
									report.title
								}}</span>
								<span class="text-sm text-ink-gray-5">{{ report.about }}</span>
							</span>
							<span
								class="lucide-chevron-right size-4 shrink-0 text-ink-gray-4 group-hover:text-ink-gray-6"
								aria-hidden="true"
							/>
						</RouterLink>
					</li>
				</ul>
			</section>
		</div>
	</div>
</template>

<script setup>
// Every report this person may open, by area, each with a line on what it answers; the ones
// opened lately on this device first, and a search across titles and descriptions.
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";
import { Button, TextInput } from "frappe-ui";
import { boot, isManager, licenceCheckOn } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { AREA_ICONS, AREAS, matchReports, recentReports, reportsFor } from "@/lib/reports";

const reports = reportsFor({
	licenceCheck: licenceCheckOn(),
	firm: boot.accountType === "CA/CS Firm",
	manager: isManager(),
	auditor: boot.roles.includes("Compliance Auditor"),
	bills: boot.mayBill,
});
const recent = recentReports(reports);
const query = ref("");

const groups = computed(() => {
	const shown = matchReports(reports, query.value);
	return AREAS.map((area) => ({
		area,
		reports: shown.filter((report) => report.area === area),
	})).filter((group) => group.reports.length);
});
</script>
