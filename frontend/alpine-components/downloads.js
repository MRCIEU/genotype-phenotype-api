import JSZip from "jszip";
import readme from "../assets/README.txt?raw";
import constants from "./constants.js";

export default {
    async downloadTraitData(traitId, isUserUpload) {
        const baseUrl = constants.apiUrl;
        const traitUrl = isUserUpload
            ? `${baseUrl}/gwas/${traitId}?include_associations=true`
            : `${baseUrl}/traits/${traitId}?include_associations=true`;
        const traitResp = await fetch(traitUrl);
        if (!traitResp.ok) throw new Error(`Failed to fetch trait data: ${traitResp.status}`);
        const data = await traitResp.json();

        if (!isUserUpload) {
            try {
                const pairsResp = await fetch(`${baseUrl}/traits/${traitId}/coloc-pairs`);
                if (pairsResp.ok) {
                    const pairsBody = await pairsResp.json();
                    data.coloc_pairs = this._colocPairRowsToObjects(
                        pairsBody.coloc_pair_column_names,
                        pairsBody.coloc_pair_rows
                    );
                }
            } catch (e) {
                console.warn("Could not fetch coloc pairs for download", e);
            }
        }

        await this.downloadDataToZip(data, data.trait.trait_name || data.trait.name);
    },

    async downloadGeneData(geneId) {
        const url = `${constants.apiUrl}/genes/${geneId}?include_trans=false&include_coloc_pairs=true&include_associations=true`;
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`Failed to fetch gene data: ${resp.status}`);
        const data = await resp.json();
        await this.downloadDataToZip(data, data.gene.gene);
    },

    _colocPairRowsToObjects(columns, rows) {
        if (!columns || !columns.length || !rows || !rows.length) return [];
        return rows.map(row => Object.fromEntries(columns.map((col, i) => [col, row[i]])));
    },

    async downloadDataToZip(data, name, zipBlob = null) {
        let zip;
        if (zipBlob) {
            zip = await JSZip.loadAsync(zipBlob);
        } else {
            zip = new JSZip();
        }

        name = name.replace(/[^a-zA-Z0-9_-]+/g, "_");
        name = name.replace(/^_+|_+$/g, "");

        zip.file("README.txt", readme);

        if (data.trait) {
            const traitJSON = this.objectToTSV(data.trait);
            zip.file("trait.tsv", traitJSON);
        }

        if (data.gene) {
            const geneJSON = this.objectToTSV(data.gene);
            zip.file("gene.tsv", geneJSON);
        }

        if (data.coloc_groups && data.coloc_groups.length > 0) {
            const colocTSV = this.arrayToTSV(data.coloc_groups);
            zip.file("coloc_groups.tsv", colocTSV);
        }

        if (data.upload_study_extractions && data.upload_study_extractions.length > 0) {
            const uploadStudyExtractionsTSV = this.arrayToTSV(data.upload_study_extractions);
            zip.file("upload_study_extractions.tsv", uploadStudyExtractionsTSV);
        }

        if (data.coloc_pairs && data.coloc_pairs.length > 0) {
            const colocPairsTSV = this.arrayToTSV(data.coloc_pairs);
            zip.file("coloc_pairs.tsv", colocPairsTSV);
        }

        if (data.variants && data.variants.length > 0) {
            const variantsTSV = this.arrayToTSV(data.variants);
            zip.file("variants.tsv", variantsTSV);
        }

        if (data.variant) {
            const variantJSON = JSON.stringify(data.variant, null, 2);
            zip.file("variant.json", variantJSON);
        }

        if (data.pairwise_colocs && data.pairwise_colocs.length > 0) {
            const pairwiseColocTSV = this.arrayToTSV(data.pairwise_colocs);
            zip.file("coloc_pairs.tsv", pairwiseColocTSV);
        }

        if (data.rare_results && data.rare_results.length > 0) {
            const rareTSV = this.arrayToTSV(data.rare_results);
            zip.file("rare.tsv", rareTSV);
        }

        if (data.study_extractions && data.study_extractions.length > 0) {
            const studyTSV = this.arrayToTSV(data.study_extractions);
            zip.file("study_extractions.tsv", studyTSV);
        }

        if (data.associations && data.associations.length > 0) {
            const assocTSV = this.arrayToTSV(data.associations);
            zip.file("associations.tsv", assocTSV);
        }

        const newZipBlob = await zip.generateAsync({ type: "blob" });
        this.downloadBlob(newZipBlob, `gpmap_${name}.zip`);
    },

    arrayToTSV(data) {
        if (!data.length) return "";
        const keys = Object.keys(data[0]);
        const rows = data.map(row => keys.map(k => row[k]).join("\t"));
        return keys.join("\t") + "\n" + rows.join("\n");
    },

    objectToTSV(data) {
        if (!data) return "";
        const keys = Object.keys(data);
        const values = keys.map(k => data[k]);
        return keys.join("\t") + "\n" + values.join("\t");
    },

    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        URL.revokeObjectURL(url);
    },

    downloadFile(url) {
        const link = document.createElement("a");
        link.href = url;
        link.download = "";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },
};
