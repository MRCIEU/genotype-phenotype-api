import { parse } from "flatted";

export class ResultsTable extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: "open" });
        this.data = null;
        this.show = true;
    }

    static get observedAttributes() {
        return ["data", "show"];
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (!newValue) return;
        switch (name) {
            case "data":
                this.data = parse(newValue);
                break;
            case "show":
                this.show = newValue;
                break;
        }
        this.render();
    }

    render() {
        if (!this.data || Object.keys(this.data).length === 0) return;

        const columns = [
            { key: "display_snp", label: "Info" },
            { key: "trait_name", label: "Trait" },
            { key: "data_type", label: "Data Type" },
            { key: "gene", label: "Gene" },
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
                                            return `<td rowspan="${rows.length}">
                                            ${row.display_snp ? `Candidate Variant: <a href="variant.html?id=${row.snp_id}">${row.display_snp}</a><br>` : ""}
                                            ${row.ld_block_id ? `LD Region: <a href="region.html?id=${row.ld_block_id}">${row.ld_block || ""}</a><br>` : ""}
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
                                            return `<td>${row.data_type} (${row.trait_category})</td>`;
                                        } else if (col.key === "gene" && (row.gene || row.situated_gene)) {
                                            return `<td><a href="gene.html?id=${row.gene || row.situated_gene}">${row.gene || row.situated_gene}</a></td>`;
                                        } else if (
                                            col.key === "trait_name" &&
                                            row.data_type === "Phenotype" &&
                                            row.trait_id &&
                                            !row.rare_result_group_id
                                        ) {
                                            return `<td><a href="trait.html?id=${row.trait_id}">${row.trait_name}</a></td>`;
                                        } else if (col.key === "min_p") {
                                            return `<td>${row.min_p.toExponential(2)}</td>`;
                                        } else if (col.key === "tissue" && row.cell_type) {
                                            return `<td>${row.tissue} (${row.cell_type})</td>`;
                                        } else {
                                            return `<td>${row[col.key] ?? ""}</td>`;
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
