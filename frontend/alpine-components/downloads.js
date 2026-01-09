import JSZip from "jszip";
import readme from "../assets/README.txt?raw";

export default {
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
};
