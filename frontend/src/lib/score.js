// The compliance score and penalty estimate: how they read and what colour they carry.
import { formatMoney } from "@/lib/format";

export function scoreTone(score) {
	if (score === null || score === undefined) return "gray";
	if (score >= 85) return "green";
	if (score >= 60) return "amber";
	return "red";
}

// What lateness costs a filing, in a few lines; nothing for a filing the rule does not count.
export function penaltyLines(penalty, { open = true } = {}) {
	if (!penalty) return [];
	const lines = [];
	if (penalty.counted) {
		if (penalty.days_late) {
			lines.push(
				`Late fee so far: ${formatMoney(penalty.late_fee)} (${penalty.days_late} ${
					penalty.days_late === 1 ? "day" : "days"
				} late).`
			);
		}
		if (open && penalty.late_fee_in_a_week) {
			lines.push(
				`If still not filed in a week: ${formatMoney(penalty.late_fee_in_a_week)}.`
			);
		} else if (open && !penalty.days_late && penalty.days_left > 7) {
			lines.push("No late fee if it is filed by the due date.");
		}
	}
	if (penalty.interest_percent) {
		lines.push(`Plus interest at ${penalty.interest_percent}% a year on tax paid late.`);
	}
	return lines;
}
