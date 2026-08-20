document.addEventListener("DOMContentLoaded", async () => {
    const page = document.querySelector("#device-page");
    const slug = new URLSearchParams(window.location.search).get("slug");
    if (!slug) {
        page.innerHTML = '<div class="container"><p class="device-error">No device was selected.</p></div>';
        return;
    }

    try {
        const dataPath = document.body.dataset.deviceData || "data/gsmarena_mobiles.json";
        const response = await fetch(dataPath, { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const devices = await response.json();
        const device = devices.find((item) => item.slug === slug);
        if (!device) throw new Error("Device not found");

        document.title = `${device.name} | MobileManch`;
        const specs = device.specifications || {};
        const getSpec = (terms, fallback = "Not listed") => {
            for (const section of Object.values(specs)) {
                for (const [label, value] of Object.entries(section || {})) {
                    if (terms.some((term) => label.toLowerCase().includes(term))) return value;
                }
            }
            return fallback;
        };
        const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[char]));
        const image = device.image_url || "";
        const highlights = [
            ["Release", getSpec(["status", "announced"])],
            ["Display", getSpec(["size", "resolution", "display"])],
            ["Chipset", getSpec(["chipset"])],
            ["Battery", getSpec(["battery", "type"])],
        ];
        const sections = Object.entries(specs).map(([section, values]) => `<section class="spec-section"><h2>${esc(section)}</h2><table class="spec-table">${Object.entries(values || {}).map(([label, value]) => `<tr><td>${esc(label)}</td><td>${esc(value)}</td></tr>`).join("")}</table></section>`).join("");
        page.innerHTML = `<div class="container"><div class="device-hero"><img class="device-poster" src="${esc(image)}" alt="${esc(device.name)}" onerror="this.remove()"><div><div class="device-kicker">MobileManch device profile</div><h1 class="device-title">${esc(device.name)}</h1><p class="device-description">${esc(device.description || "Complete specifications and details for this device.")}</p></div></div><div class="device-highlights">${highlights.map(([label, value]) => `<div class="device-highlight"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("")}</div>${sections}</div>`;
    } catch (error) {
        page.innerHTML = `<div class="container"><p class="device-error">Device details could not be loaded. Open the site through a local server and check that the device has been imported.</p></div>`;
        console.warn(error);
    }
});