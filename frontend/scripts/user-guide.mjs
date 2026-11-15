// Rebuilds USER_GUIDE.md at the top of the repository from the app's Help answers.
// Run from frontend/: node scripts/user-guide.mjs
import { writeFileSync } from "node:fs";
import path from "node:path";
import { userGuide } from "../src/help/guide.js";

const target = path.resolve(import.meta.dirname, "../../USER_GUIDE.md");
writeFileSync(target, userGuide());
console.log(`Wrote ${path.relative(process.cwd(), target)}`);
