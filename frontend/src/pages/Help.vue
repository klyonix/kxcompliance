<template>
	<AppPageHeader title="Help" />

	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
		<div class="flex flex-col gap-2">
			<p class="text-base text-ink-gray-6">
				Short answers to what people ask most. "Show me" opens the page and walks you
				through it.
			</p>
			<TextInput
				v-model="query"
				type="search"
				placeholder="What do you want to do?"
				aria-label="Search the help"
				data-tour="help-search"
			>
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
			</TextInput>
		</div>

		<p v-if="!groups.length" class="py-10 text-center text-base text-ink-gray-5">
			Nothing matches. Try other words, or ask the question mark on the page you are on.
		</p>

		<div class="flex flex-col gap-6" data-tour="help-articles">
			<section
				v-for="group in groups"
				:key="group.area"
				class="flex flex-col gap-1"
				:aria-label="group.area"
			>
				<h2 class="pb-1 text-sm font-semibold uppercase tracking-wide text-ink-gray-5">
					{{ group.area }}
				</h2>
				<details
					v-for="article in group.articles"
					:key="article.id"
					class="group rounded-lg border border-outline-gray-1"
					:open="article.id === openId"
					@toggle="(event) => remember(article.id, event.target.open)"
				>
					<summary
						class="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-base font-medium text-ink-gray-8"
					>
						<span
							class="lucide-chevron-right size-4 shrink-0 text-ink-gray-5 transition-transform group-open:rotate-90"
							aria-hidden="true"
						/>
						{{ article.title }}
					</summary>
					<div class="flex flex-col gap-3 px-3 pb-3 pl-9">
						<p class="text-sm text-ink-gray-5">{{ article.when }}</p>
						<ol
							class="flex list-decimal flex-col gap-1.5 pl-4 text-base text-ink-gray-8"
						>
							<li v-for="step in article.steps" :key="step">{{ step }}</li>
						</ol>
						<p
							v-if="article.tip"
							class="rounded-lg bg-surface-gray-2 px-3 py-2 text-sm text-ink-gray-7"
						>
							{{ article.tip }}
						</p>
						<Button
							v-if="article.page && tourFor(article.page)"
							class="self-start"
							icon-left="lucide-play"
							label="Show me"
							@click="showMe(article)"
						/>
					</div>
				</details>
			</section>
		</div>
	</div>
</template>

<script setup>
// The user manual: short answers, grouped by area, for what this person's role lets them do.
// The search and the open answer are kept in the address, so someone can be sent a link to it.
import { computed, nextTick, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button, TextInput } from "frappe-ui";
import { boot, isClientLogin, isManager } from "@/boot";
import AppPageHeader from "@/components/AppPageHeader.vue";
import { articlesFor, groupArticles } from "@/help/manual";
import { tourFor } from "@/tours/tours";
import { startTour, toursForReader } from "@/tours/useTours";

const route = useRoute();
const router = useRouter();
const query = ref(typeof route.query.q === "string" ? route.query.q : "");
const openId = ref(typeof route.query.article === "string" ? route.query.article : "");

const articles = articlesFor({
	tours: toursForReader(),
	client: isClientLogin(),
	manager: isManager(),
	firm: boot.accountType === "CA/CS Firm",
});
const groups = computed(() => groupArticles(articles, query.value));

function remember(id, isOpen) {
	if (isOpen) openId.value = id;
	else if (openId.value === id) openId.value = "";
}

watch([query, openId], () => {
	router.replace({
		query: { q: query.value.trim() || undefined, article: openId.value || undefined },
	});
});

async function showMe(article) {
	const tour = tourFor(article.page);
	await router.push({ name: article.page });
	await nextTick();
	startTour(tour.id);
}
</script>
