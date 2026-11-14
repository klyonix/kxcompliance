// Which help articles a person sees, and how they are found.
import { tourFor } from "@/tours/tours";
import { AREAS, ARTICLES } from "./articles";

// An article shows to the people its page's tour is for, and by its own flags as a tour's.
// `reader` is { tours, client, manager, firm }: the tours this person may take, and who they are.
export function articlesFor(reader, { articles = ARTICLES } = {}) {
	const readable = new Set(reader.tours.map((tour) => tour.id));
	return articles.filter((article) => {
		if (reader.client ? !article.client : article.staff === false) return false;
		if (article.managers && !reader.manager) return false;
		if (article.firm && !reader.firm) return false;
		const tour = tourFor(article.page);
		return !tour || readable.has(tour.id);
	});
}

// Every word of the search in the title, the "when" or the steps.
export function matches(article, query) {
	const words = String(query || "")
		.toLowerCase()
		.split(/\s+/)
		.filter(Boolean);
	const text = [article.title, article.when, ...article.steps, article.tip || ""]
		.join(" ")
		.toLowerCase();
	return words.every((word) => text.includes(word));
}

export function groupArticles(articles, query) {
	return AREAS.map((area) => ({
		area,
		articles: articles.filter((article) => article.area === area && matches(article, query)),
	})).filter((group) => group.articles.length);
}
