function loadGsmarenaNews(container) {
	const updatesPath = container.dataset.updatesPath || "updates.json";

	return fetch(updatesPath, { cache: "no-store" })
		.then((response) => {
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			return response.json();
		})
		.then((data) => {
			const articles = Array.isArray(data.articles) ? data.articles : [];
			if (!articles.length) throw new Error("No articles in updates.json");

			container.replaceChildren();
			articles.forEach((article, index) => {
				const item = document.createElement("article");
				item.className = "news-item";

				if (article.image) {
					const image = document.createElement("img");
					image.className = "news-thumb";
					const imagePath = updatesPath.startsWith("../")
						? `../${article.image}`
						: article.image;
					image.src = imagePath;
					image.alt = article.title || "GSMArena news image";
					image.loading = "lazy";
					image.referrerPolicy = "no-referrer";
					image.addEventListener("error", () => image.remove());
					item.append(image);
				}

				const number = document.createElement("span");
				number.className = "news-index";
				number.textContent = String(index + 1).padStart(2, "0");

				const content = document.createElement("div");
				const heading = document.createElement("h3");
				const link = document.createElement("a");
				link.href = article.link;
				link.target = "_blank";
				link.rel = "noopener noreferrer";
				link.textContent = article.title;
				heading.append(link);

				const summary = document.createElement("p");
				summary.textContent = "Latest mobile news from GSMArena.";

				const meta = document.createElement("span");
				meta.className = "news-meta";
				meta.textContent = data.last_updated
					? `Updated ${new Date(data.last_updated).toLocaleDateString()}`
					: "Live from GSMArena";

				content.append(heading, summary, meta);
				item.append(number, content);
				container.append(item);
			});
		})
		.catch((error) => {
			console.warn("GSMArena updates are unavailable; showing fallback news.", error);
		});
}

window.loadGsmarenaNews = loadGsmarenaNews;

document.addEventListener("DOMContentLoaded", () => {
	const container = document.querySelector("#gsmarena-news-container");
	if (container) loadGsmarenaNews(container);
});