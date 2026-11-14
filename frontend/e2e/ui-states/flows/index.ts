import type { AnyFlow } from "../flow";
import { account, licenceCheck, myWorkEmpty, overview, salesCheck } from "./more";
import { myWork } from "./myWork";
import { filings, legal, register } from "./recordList";
import { filing, item, legalCase, notice, review, trademark } from "./records";

/** The canvas lays the flows out in this order. */
export const flows: AnyFlow[] = [
	...myWork,
	...myWorkEmpty,
	...overview,
	...register,
	...item,
	...filings,
	...filing,
	...review,
	...legal,
	...legalCase,
	...trademark,
	...notice,
	...licenceCheck,
	...salesCheck,
	...account,
];
