<template>
	<Button
		variant="ghost"
		:icon="dark ? 'lucide-sun' : 'lucide-moon'"
		:label="dark ? t('Switch to light') : t('Switch to dark')"
		:aria-label="dark ? t('Switch to light') : t('Switch to dark')"
		:title="dark ? t('Switch to light') : t('Switch to dark')"
		@click="setColorScheme(dark ? 'light' : 'dark')"
	/>
</template>

<script setup>
// One click between light and dark from any page; Account keeps the choice of following the
// device (frappe-ui's useColorScheme, shared, so both stay in step).
import { computed } from "vue";
import { Button, useColorScheme } from "frappe-ui";
import { t } from "@/lib/i18n";

const { resolvedColorScheme, setColorScheme } = useColorScheme();
const dark = computed(() => resolvedColorScheme.value === "dark");
</script>
