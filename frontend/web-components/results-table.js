import { parse } from "flatted";

function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function urlId(value) {
    if (value === null || value === undefined) return "";
    return encodeURIComponent(value);
}

export class ResultsTable extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: "open" });
        this.data = null;
        this.show = true;
        this.hideVariantLink = false;
    }

    static get observedAttributes() {
        return ["data", "show", "hide-variant-link"];
    }

    attributeChangedCallback(name, oldValue, newValue) {
        switch (name) {
            case "data":
                if (!newValue) return;
                this.data = parse(newValue);
                break;
            case "show":
                this.show = newValue;
                break;
            case "hide-variant-link":
                this.hideVariantLink = newValue !== null && newValue !== "false";
                break;
        }
        this.render();
    }

    connectedCallback() {
        const val = this.getAttribute("hide-variant-link");
        this.hideVariantLink = val !== null && val !== "false";
    }

    render() {
        if (!this.data || Object.keys(this.data).length === 0) return;

        const columns = [
            { key: "display_snp", label: "Info" },
            { key: "trait_name", label: "Trait" },
            { key: "data_type", label: "Data Type" },
            { key: "gene", label: "Gene" },
            { key: "situated_gene", label: "Situated Gene" },
            { key: "tissue", label: "Tissue" },
            { key: "cis_trans", label: "Cis/Trans" },
            { key: "min_p", label: "P-value" },
        ];

        const table = this.show
            ? `
            <style>
                table { border-collapse: collapse; width: 100%; font-size: 0.9em; }
                th, td { border: 1px solid #ccc; padding: 4px 8px; font-size: 0.9em; }
                th { background: #f5f5f5; }
                a { color: #1976d2; text-decoration: none; }
            </style>
            <table>
                <thead>
                    <tr>
                        ${columns.map(col => `<th>${col.label}</th>`).join("")}
                    </tr>
                </thead>
                <tbody>
                    ${Object.entries(this.data)
                        .map(([_, rows]) =>
                            rows
                                .map(
                                    (row, i) => `
                            <tr style="${row.color ? `background-color: ${row.color};` : ""}">
                                ${columns
                                    .map(col => {
                                        if (col.key === "display_snp" && i === 0) {
                                            const variantContent = row.display_snp
                                                ? this.hideVariantLink
                                                    ? `Candidate Variant: ${escapeHtml(row.display_snp)}<br>`
                                                    : `Candidate Variant: <a href="variant.html?id=${urlId(row.variant_id)}">${escapeHtml(row.display_snp)}</a><br>`
                                                : "";
                                            return `<td rowspan="${rows.length}">
                                            ${variantContent}
                                            ${row.ld_block_id ? `LD Region: <a href="region.html?id=${urlId(row.ld_block_id)}">${escapeHtml(row.ld_block || "")}</a><br>` : ""}
                                            ${
                                                row.posterior_prob !== undefined && row.posterior_prob !== null
                                                    ? `Posterior Probability (PP): <b>${Number(row.posterior_prob).toFixed(3)}</b><br>
                                                   PP Explained by SNP: <b>${Number(row.posterior_explained_by_snp).toFixed(3)}</b>`
                                                    : ""
                                            }
                                        </td>`;
                                        } else if (col.key === "display_snp") {
                                            return "";
                                        } else if (
                                            col.key === "data_type" &&
                                            row.data_type === "Phenotype" &&
                                            row.trait_category
                                        ) {
                                            return `<td>${escapeHtml(row.data_type)} (${escapeHtml(row.trait_category)})</td>`;
                                        } else if (col.key === "gene" && row.gene) {
                                            return `<td><a href="gene.html?id=${urlId(row.gene)}">${escapeHtml(row.gene)}</a></td>`;
                                        } else if (col.key === "situated_gene" && row.situated_gene) {
                                            return `<td><a href="gene.html?id=${urlId(row.situated_gene)}">${escapeHtml(row.situated_gene)}</a></td>`;
                                        } else if (
                                            col.key === "trait_name" &&
                                            row.data_type === "Phenotype" &&
                                            row.trait_id &&
                                            !row.rare_result_group_id
                                        ) {
                                            return `<td><a href="trait.html?id=${urlId(row.trait_id)}">${escapeHtml(row.trait_name)}</a></td>`;
                                        } else if (col.key === "min_p") {
                                            return `<td>${row.min_p != null ? row.min_p.toExponential(2) : ""}</td>`;
                                        } else if (col.key === "tissue" && row.cell_type) {
                                            return `<td>${escapeHtml(row.tissue)} (${escapeHtml(row.cell_type)})</td>`;
                                        } else {
                                            return `<td>${escapeHtml(row[col.key] ?? "")}</td>`;
                                        }
                                    })
                                    .join("")}
                            </tr>
                        `
                                )
                                .join("")
                        )
                        .join("")}
                </tbody>
            </table>
        `
            : "";
        this.shadowRoot.innerHTML = table;
    }
}
