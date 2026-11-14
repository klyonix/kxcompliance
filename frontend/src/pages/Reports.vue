<template>
	<AppPageHeader title="Reports" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
		<p class="text-base text-ink-gray-6">
			The same reports as the Desk, so the numbers always agree. Each can be filtered and
			downloaded for a spreadsheet.
		</p>
		<section
			v-for="group in groups"
			:key="group.area"
			class="flex flex-col gap-1"
			:aria-label="group.area"
			data-tour="reports-list"
		>
			<h2 class="px-3 pb-1 text-sm font-semibold text-ink-gray-6">{{ group.area }}</h2>
			<RouterLink
				v-for="report in group.reports"
				:key="report.slug"
				:to="{ name: 'Report', params: { report: report.slug } }"
				class="flex items-start gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-4"
			>
				<span
					class="lucide-file-chart-column mt-0.5 size-4 shrink-0 text-ink-gray-5"
					aria-hidden="true"
				/>
				<span class="flex min-w-0 flex-col">
					<span class="text-base font-medium text-ink-gray-8">{{ report.title }}</span>
					<span class="text-sm text-ink-gray-5">{{ report.about }}</span>
				</span>
			</RouterLink>
		</section>
	</div>
</template>

<script setup>
// Every report this person may open, by area, each with a line on what it answers.
import { RouterLink } from "vue-router";
import { boot, isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { AREAS, reportsFor } from "@/lib/reports";

const reports = reportsFor({
	firm: boot.accountType === "CA/CS Firm",
	manager: isManager(),
	auditor: boot.roles.includes("Compliance Auditor"),
});
const groups = AREAS.map((area) => ({
	area,
	reports: reports.filter((report) => report.area === area),
})).filter((group) => group.reports.length);
</script>
