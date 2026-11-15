<template>
	<section
		class="flex flex-col gap-3 rounded-xl border border-outline-gray-1 p-4"
		aria-labelledby="activity-heading"
		data-tour="record-activity"
	>
		<h2 id="activity-heading" class="text-base font-semibold text-ink-gray-8">Activity</h2>
		<!-- Frappe's own timeline: what changed, comments and attachments, with who and when. It grows
		     with what there is, up to a height where it scrolls. -->
		<div class="flex max-h-[28rem] flex-col">
			<TimelineContainer>
				<ActivityTimeline :activities="activities" :loading="loading" :paginate="paginate">
					<template #empty>
						<p class="py-6 text-center text-sm text-ink-gray-5">Nothing yet.</p>
					</template>
				</ActivityTimeline>
			</TimelineContainer>
		</div>
		<form class="flex flex-col gap-2" @submit.prevent="send">
			<FormControl
				v-model="comment"
				type="textarea"
				:rows="2"
				placeholder="Add a comment for the team"
				aria-label="Add a comment"
			/>
			<p v-if="error" role="alert" class="text-sm text-ink-red-4">{{ error }}</p>
			<Button
				type="submit"
				class="self-end"
				label="Comment"
				:disabled="!comment.trim()"
				:loading="sending"
			/>
		</form>
	</section>
</template>

<script setup>
// A record's activity beside its page: Frappe's timeline (changes, comments, attachments), and a
// comment box. The server shows it only to those who may read the record.
import { ref } from "vue";
import { Button, FormControl } from "frappe-ui";
import {
	ActivityTimeline,
	TimelineContainer,
	useActivityTimeline,
} from "@framework/ui/ActivityTimeline";
import { call } from "@/api";
import { boot } from "@/boot";
import { commentHtml } from "@/lib/records";

const props = defineProps({
	doctype: { type: String, required: true },
	name: { type: String, required: true },
});

const { activities, loading, paginate, reload } = useActivityTimeline(props.doctype, props.name, [
	"comment",
	"version",
	"log",
	"attachment_log",
]);

const comment = ref("");
const sending = ref(false);
const error = ref("");

async function send() {
	if (!comment.value.trim()) return;
	sending.value = true;
	error.value = "";
	try {
		await call(
			"frappe.desk.form.utils.add_comment",
			{
				reference_doctype: props.doctype,
				reference_name: props.name,
				content: commentHtml(comment.value),
				comment_email: boot.user,
				comment_by: boot.userFullname || boot.user,
			},
			{ httpMethod: "POST" }
		);
		comment.value = "";
		await reload();
	} catch (err) {
		error.value = err.isNetwork
			? "The comment did not reach the server. Try again when you are back online."
			: err.message;
	} finally {
		sending.value = false;
	}
}
</script>
