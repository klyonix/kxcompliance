<template>
	<RecordList title="Legal" list-key="legal" :views="LEGAL_VIEWS" :empty="empty">
		<template #actions>
			<template v-if="mayRecord()">
				<!-- A phone has room for one button beside the title: everything is under New. -->
				<div class="sm:hidden">
					<Dropdown :options="phoneOptions" align="end">
						<Button variant="solid" icon-left="lucide-plus" label="New" />
					</Dropdown>
				</div>
				<div class="hidden sm:block">
					<Dropdown :options="startOptions" align="end">
						<Button icon-right="lucide-chevron-down" label="Start" />
					</Dropdown>
				</div>
				<Button
					class="hidden sm:inline-flex"
					variant="solid"
					icon-left="lucide-plus"
					label="Log notice"
					:route="{ name: 'NewNotice' }"
				/>
			</template>
		</template>
	</RecordList>
</template>

<script setup>
import { useRouter } from "vue-router";
import { Button, Dropdown } from "frappe-ui";
import { mayRecord } from "@/boot";
import RecordList from "@/components/RecordList.vue";
import { LEGAL_VIEWS } from "@/lib/legal";

const router = useRouter();
const startOptions = [
	{
		label: "Start a case",
		icon: "lucide-gavel",
		onClick: () => router.push({ name: "NewCase" }),
	},
	{
		label: "Add a trademark",
		icon: "lucide-stamp",
		onClick: () => router.push({ name: "NewTrademark" }),
	},
];
const phoneOptions = [
	{
		label: "Log a notice",
		icon: "lucide-scale",
		onClick: () => router.push({ name: "NewNotice" }),
	},
	...startOptions,
];

const EMPTY = {
	dates: {
		title: "Nothing coming up",
		detail: "Hearings, reply dates and trademark deadlines appear here, soonest first.",
	},
	cases: {
		title: "No open cases",
		detail: "Cases and notices appear here while they are open.",
	},
	marks: {
		title: "No trademarks",
		detail: "Trademark applications and registrations appear here.",
	},
};

function empty(view, searching) {
	if (searching) return { title: "No matches", detail: "Try another word, or another tab." };
	const actions = {
		cases: { label: "Log a notice", route: { name: "NewNotice" } },
		marks: { label: "Add a trademark", route: { name: "NewTrademark" } },
	};
	const action = mayRecord() ? actions[view] || null : null;
	return { ...EMPTY[view], action };
}
</script>
