document.addEventListener("DOMContentLoaded", async () => {
    const sections = {
        news: ["#news", "Latest News"],
        reviews: ["#reviews", "Phone Reviews"],
        videos: ["#videos", "Videos"],
        featured: ["#featured", "Featured Articles"],
        finder: ["#finder", "Phone Finder"],
        deals: ["#deals", "Daily Deals"],
        toppicks: ["#toppicks", "Top Picks"],
        compare: ["#compare", "Coverage & Comparisons"],
        contact: ["footer", "Contact MobileManch"]
    };
    const key = new URLSearchParams(window.location.search).get("section");
    const config = sections[key];
    if (!config) {
        window.location.replace("index.html#top");
        return;
    }

    const title = document.querySelector("#page-title");
    const content = document.querySelector("#page-content");
    title.textContent = config[1];

    try {
        const response = await fetch("index.html", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const html = await response.text();
        const source = new DOMParser().parseFromString(html, "text/html");
        const section = source.querySelector(config[0]);
        if (!section) throw new Error("Section not found");
        content.replaceChildren(section.cloneNode(true));
        if (key === "news") {
            const latestNews = source.querySelector("#latest-news");
            if (latestNews) content.append(latestNews.cloneNode(true));
        }
        if (window.localizeGsmarenaLinks) window.localizeGsmarenaLinks(content);
        if (key === "news") {
            const newsContainer = content.querySelector("#gsmarena-news-container");
            if (newsContainer && window.loadGsmarenaNews) {
                window.loadGsmarenaNews(newsContainer);
            }
        }
    } catch (error) {
        content.innerHTML = '<p class="loading">This page could not be loaded. <a href="index.html">Return home</a>.</p>';
        console.warn("MobileManch detail page failed to load.", error);
    }
});
