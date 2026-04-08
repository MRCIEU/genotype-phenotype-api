import constants from "../alpine-components/constants.js";

export class NavigationBar extends HTMLElement {
    constructor() {
        super();
        this.searchOptions = [];
        this.searchTimeout = null;
        this.filteredItems = [];
    }

    connectedCallback() {
        fetch("web-components/navigation-bar.html")
            .then(stream => stream.text())
            .then(text => {
                this.innerHTML = text;
                this.setupBurgerMenu();
                this.setupSearch();
            });
    }

    setupBurgerMenu() {
        const burger = this.querySelector(".navbar-burger");
        const menu = this.querySelector("#navbarBasicExample");
        if (burger && menu) {
            burger.addEventListener("click", () => {
                burger.classList.toggle("is-active");
                menu.classList.toggle("is-active");
                burger.setAttribute("aria-expanded", burger.classList.contains("is-active"));
            });
        }
    }

    setupSearch() {
        const container = this.querySelector("#nav-search-container");
        if (!container) return;

        const filename = window.location.pathname.split("/").pop();
        if (filename === "" || filename === "index.html") {
            container.style.display = "none";
            return;
        }

        this.searchInput = this.querySelector("#nav-search-input");
        this.searchDropdown = this.querySelector("#nav-search-dropdown");

        this.fetchSearchOptions();

        this.searchInput.addEventListener("input", () => this.handleInput());
        this.searchInput.addEventListener("keyup", e => {
            if (e.key === "Enter") this.handleEnter();
        });
        this.searchInput.addEventListener("focus", () => {
            if (this.filteredItems.length > 0) {
                this.searchDropdown.style.display = "block";
            }
        });
        document.addEventListener("click", e => {
            if (!container.contains(e.target)) {
                this.searchDropdown.style.display = "none";
            }
        });
    }

    async fetchSearchOptions() {
        try {
            const response = await fetch(constants.apiUrl + "/search/options");
            if (response.ok) {
                const data = await response.json();
                this.searchOptions = data.search_terms || [];
            }
        } catch (e) {
            // silently fail — search just won't have typeahead
        }
    }

    handleInput() {
        if (this.searchTimeout) clearTimeout(this.searchTimeout);

        const text = this.searchInput.value.trim().toLowerCase();
        if (text.length < 2) {
            this.filteredItems = [];
            this.renderItems([]);
            return;
        }

        this.searchTimeout = setTimeout(() => {
            this.filteredItems = this.searchOptions
                .filter(
                    item =>
                        item.name.toLowerCase().includes(text) ||
                        (item.alt_name && item.alt_name.toLowerCase().includes(text)),
                )
                .sort((a, b) => b.num_rare_results + b.num_coloc_groups - (a.num_rare_results + a.num_coloc_groups))
                .slice(0, 20);
            this.renderItems(this.filteredItems);
        }, 200);
    }

    handleEnter() {
        const query = this.searchInput.value.trim();
        if (!query || query.length < 2) return;

        const isRsid = query.toLowerCase().startsWith("rs");
        const isChrBp = /^\d+:\d+(_[ACGT]+_[ACGT]+)?$/.test(query);

        if (isRsid || isChrBp) {
            this.searchVariant(query);
            return;
        }

        if (this.filteredItems.length === 1) {
            this.navigateToItem(this.filteredItems[0]);
        }
    }

    async searchVariant(query) {
        this.renderMessage("Searching...");
        try {
            const response = await fetch(
                constants.apiUrl + "/search/variant/" + encodeURIComponent(query),
            );
            if (!response.ok) {
                this.renderMessage("No variants found");
                return;
            }
            const data = await response.json();
            const originals = (data.original_variants || []).map(v => ({
                ...v,
                _label: "Match",
            }));
            const proxies = (data.proxy_variants || []).map(v => ({
                ...v,
                _label: "Proxy",
            }));
            const allVariants = [...originals, ...proxies];
            if (allVariants.length > 0) {
                this.renderVariants(allVariants);
            } else {
                this.renderMessage("No variants found");
            }
        } catch {
            this.renderMessage("Search failed");
        }
    }

    navigateToItem(item) {
        if (item.type === "trait") {
            window.location.href = "trait.html?id=" + item.type_id;
        } else if (item.type === "gene") {
            window.location.href = "gene.html?id=" + item.type_id;
        }
    }

    renderItems(items) {
        this.searchDropdown.innerHTML = "";
        if (items.length === 0) {
            this.searchDropdown.style.display = "none";
            return;
        }

        items.forEach(item => {
            const a = document.createElement("a");
            const typeLabel = item.type === "trait" ? "Trait" : "Gene";
            const counts = [];
            if (item.num_coloc_groups > 0) counts.push(item.num_coloc_groups + " coloc groups");
            if (item.num_rare_results > 0) counts.push(item.num_rare_results + " rare results");
            a.innerHTML =
                `<div style="font-weight: 600">${this.esc(item.name)}</div>` +
                (counts.length > 0
                    ? `<div class="nav-search-subtitle">${typeLabel} · ${counts.join(", ")}</div>`
                    : `<div class="nav-search-subtitle">${typeLabel}</div>`);
            a.href =
                item.type === "trait"
                    ? "trait.html?id=" + item.type_id
                    : "gene.html?id=" + item.type_id;
            this.searchDropdown.appendChild(a);
        });

        this.searchDropdown.style.display = "block";
    }

    renderVariants(variants) {
        this.searchDropdown.innerHTML = "";

        variants.forEach(v => {
            const a = document.createElement("a");
            const display = v.rsid || v.snp || `${v.chr}:${v.bp}`;
            const pos = v.chr && v.bp ? `${v.chr}:${v.bp}` : "";
            const details = [v._label];
            if (pos && pos !== display) details.push(pos);
            if (v.symbol) details.push(v.symbol);
            if (v.num_colocs > 0) details.push(v.num_colocs + " colocalization groups");
            if (v.num_rare_results > 0) details.push(v.num_rare_results + " rare results");
            a.innerHTML =
                `<div style="font-weight: 600">${this.esc(display)}</div>` +
                `<div class="nav-search-subtitle">${details.join(" · ")}</div>`;
            a.href = "variant.html?id=" + v.id;
            this.searchDropdown.appendChild(a);
        });

        this.searchDropdown.style.display = "block";
    }

    renderMessage(text) {
        this.searchDropdown.innerHTML = `<div class="nav-search-message">${this.esc(text)}</div>`;
        this.searchDropdown.style.display = "block";
    }

    esc(text) {
        const el = document.createElement("span");
        el.textContent = text;
        return el.innerHTML;
    }
}
