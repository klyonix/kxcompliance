<template>
	<RecordList title="Legal" :views="LEGAL_VIEWS" :empty="empty">
		<template #actions>
			<Button
				v-if="mayRecord()"
				variant="solid"
				icon-left="lucide-plus"
				label="Log notice"
				:route="{ name: 'NewNotice' }"
			/>
		</template>
	</RecordList>
</template>

<script setup>
import { Button } from "frappe-ui";
import { mayRecord } from "@/boot";
import RecordList from "@/components/RecordList.vue";
import { LEGAL_VIEWS } from "@/lib/legal";

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
	const action =
		view === "cases" && mayRecord()
			? { label: "Record a notice", route: { name: "NewNotice" } }
			: null;
	return { ...EMPTY[view], action };
}
</script>
