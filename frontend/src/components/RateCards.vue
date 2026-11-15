<template>
	<section class="flex flex-col gap-4" aria-labelledby="cards-heading">
		<div class="flex flex-col gap-0.5">
			<h2 id="cards-heading" class="text-base font-semibold text-ink-gray-8">Rate cards</h2>
			<p class="text-sm text-ink-gray-5">
				What the firm charges: for filing each return, and for services by the hour or item
				or every month, quarter or year. Each client pays its card's rates, the default
				card if it has none, and any own rates set on the client.
			</p>
		</div>
		<p v-if="error" role="alert" class="text-base text-ink-red-4">{{ error }}</p>

		<div class="flex flex-col gap-4 lg:flex-row lg:items-start">
			<nav class="flex flex-col gap-1 lg:w-56 lg:shrink-0" aria-label="Rate cards">
				<button
					v-for="card in cards"
					:key="card.name"
					type="button"
					class="flex items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-base hover:bg-surface-gray-2"
					:class="
						open?.name === card.name
							? 'bg-surface-gray-3 font-medium text-ink-gray-9'
							: 'text-ink-gray-7'
					"
					@click="openCard(card.name)"
				>
					<span class="truncate">{{ card.title }}</span>
					<Badge v-if="card.is_default" label="Default" theme="blue" />
				</button>
				<Button
					class="mt-1 self-start"
					icon-left="lucide-plus"
					label="New rate card"
					@click="newCard"
				/>
			</nav>

			<div v-if="open" class="flex min-w-0 flex-1 flex-col gap-4">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
					<FormControl
						v-model="open.title"
						label="Title"
						placeholder="Standard, Small business"
						:disabled="!open.isNew"
						:description="
							open.isNew ? '' : 'A card keeps its title; make a new one to rename.'
						"
					/>
					<FormControl v-model="open.is_default" type="checkbox" label="Default card" />
				</div>
				<FormControl
					v-model="open.description"
					type="textarea"
					:rows="2"
					label="Description"
					placeholder="Who this card is for"
				/>
				<RateLines v-model="open.lines" empty="No rates on this card yet." />
				<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-end">
					<p v-if="saveError" role="alert" class="text-sm text-ink-red-4 sm:mr-auto">
						{{ saveError }}
					</p>
					<Button
						v-if="!open.isNew"
						theme="red"
						label="Delete card"
						:loading="busy === 'delete'"
						@click="removeCard"
					/>
					<Button
						variant="solid"
						label="Save card"
						:loading="busy === 'save'"
						:disabled="!open.title.trim() || Boolean(ratesProblem(open.lines))"
						@click="save"
					/>
				</div>
			</div>
			<p v-else-if="cards.length" class="text-base text-ink-gray-5">
				Choose a card to see its rates.
			</p>
			<p v-else class="text-base text-ink-gray-5">
				No rate cards yet. Make one; the first is the default.
			</p>
		</div>
	</section>
</template>

<script setup>
// Billing settings, the Rate cards tab: the firm's named rate cards and the rates on each.
import { onMounted, ref } from "vue";
import { Badge, Button, FormControl, dialog, toast } from "frappe-ui";
import { createDoc, deleteDoc, getDoc, getList, updateDoc } from "@/api";
import RateLines from "@/components/RateLines.vue";
import { ratesProblem, ratesToSend } from "@/lib/billing";

const cards = ref([]);
const open = ref(null);
const error = ref("");
const saveError = ref("");
const busy = ref("");

async function loadCards() {
	cards.value = (
		await getList("Rate Card", {
			fields: ["name", "title", "is_default"],
			orderBy: "is_default desc, title asc",
			limit: 200,
		})
	).rows;
}

async function openCard(name) {
	saveError.value = "";
	const card = await getDoc("Rate Card", name);
	open.value = {
		name: card.name,
		title: card.title,
		is_default: Boolean(card.is_default),
		description: card.description || "",
		lines: card.lines.map((line) => ({
			kind: line.kind,
			obligation_template: line.obligation_template || "",
			service: line.service || "",
			unit: line.unit,
			amount: line.amount,
			sac_code: line.sac_code || "",
		})),
	};
}

function newCard() {
	saveError.value = "";
	open.value = {
		isNew: true,
		title: "",
		is_default: !cards.value.length,
		description: "",
		lines: [],
	};
}

async function save() {
	saveError.value = "";
	busy.value = "save";
	const values = {
		title: open.value.title.trim(),
		is_default: open.value.is_default ? 1 : 0,
		description: open.value.description.trim(),
		lines: ratesToSend(open.value.lines),
	};
	try {
		const saved = open.value.isNew
			? await createDoc("Rate Card", values)
			: await updateDoc("Rate Card", open.value.name, values);
		toast.success("Rate card saved");
		await loadCards();
		await openCard(saved.name);
	} catch (err) {
		saveError.value = err.message;
	} finally {
		busy.value = "";
	}
}

function removeCard() {
	dialog.confirm({
		title: `Delete ${open.value.title}?`,
		message: "Clients on this card pay the default card's rates instead.",
		confirmLabel: "Delete card",
		theme: "red",
		onConfirm: async () => {
			busy.value = "delete";
			try {
				await deleteDoc("Rate Card", open.value.name);
				toast.success("Rate card deleted");
				open.value = null;
				await loadCards();
			} catch (err) {
				saveError.value = err.message;
			} finally {
				busy.value = "";
			}
		},
	});
}

onMounted(async () => {
	try {
		await loadCards();
		const first = cards.value.find((card) => card.is_default) || cards.value[0];
		if (first) await openCard(first.name);
	} catch (err) {
		error.value = err.message;
	}
});
</script>
