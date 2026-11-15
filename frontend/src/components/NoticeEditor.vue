<template>
	<Editor v-model="model" :extensions="[CommentKit]" placeholder="The privacy notice">
		<EditorContent
			class="prose prose-sm max-h-96 max-w-none overflow-y-auto rounded-lg border border-outline-gray-2 px-3 py-2"
		/>
	</Editor>
</template>

<script setup>
// The privacy notice's editor. It is large, so Settings loads it only when a manager edits the
// notice, and it is not kept for offline use.
import { CommentKit, Editor, EditorContent } from "frappe-ui/editor";

const model = defineModel({ type: String, default: "" });
</script>
