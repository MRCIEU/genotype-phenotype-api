import JSZip from 'jszip';
import readme from '../assets/README.txt?raw';

export default {
    /**
     * Downloads a JSON object as a CSV file.
     * @param {Object} snpData - The JSON object to convert to CSV.
     * @param {Object} colocData - The JSON object to convert to CSV.
     * @param {string} filename - The name of the file to save.
     */
    downloadSNPDataToCSV(snpData, colocData, filename = 'coloc_data.csv') {
        const headers = [
            'display_snp', 'rsid', 'chr', 'bp', 'ea', 'oa', 'posterior_prob', 
            'regional_prob', 'posterior_explained_by_snp', 'min_p', 'cis_trans',
            'trait', 'data_type', 'tissue', 'gene',
            'beta', 'se', 'p', 'eaf', 'imputed'
        ];
        
        let csvContent = headers.join(',') + '\n';
        colocData.forEach(coloc => {
            const row = [
                coloc.display_snp || '',
                snpData.rsid || '',
                snpData.chr || '',
                snpData.bp || '',
                snpData.ea || '',
                snpData.oa || '',
                coloc.posterior_prob || '',
                coloc.regional_prob || '',
                coloc.posterior_explained_by_snp || '',
                coloc.min_p || '',
                coloc.cis_trans || '',
                coloc.trait || '',
                coloc.data_type || '',
                coloc.tissue || '',
                coloc.gene || '',
                coloc.association ? coloc.association.beta || '' : '',
                coloc.association ? coloc.association.se || '' : '',
                coloc.association ? coloc.association.p || '' : '',
                coloc.association ? coloc.association.eaf || '' : '',
                coloc.association ? (coloc.association.imputed ? 'true' : 'false') : ''
            ];
            
            const formattedRow = row.map(value => {
                const stringValue = String(value);
                return stringValue.includes(',') ? `"${stringValue}"` : stringValue;
            });
            
            csvContent += formattedRow.join(',') + '\n';
        });
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
    },


    async downloadDataToZip(data, name, zipBlob = null) {
        let zip;
        if (zipBlob) {
            zip = await JSZip.loadAsync(zipBlob);
        } else {
            zip = new JSZip();
        }

        name = name.replace(/[^a-zA-Z0-9_-]+/g, '_');
        name = name.replace(/^_+|_+$/g, '');

        zip.file('README.txt', readme);

        if (data.trait) {
            const traitJSON = JSON.stringify(data.trait, null, 2);
            zip.file('trait.json', traitJSON);
        }

        if (data.gene) {
            const geneJSON = JSON.stringify(data.gene, null, 2);
            zip.file('gene.json', geneJSON);
        }

        if (data.coloc_groups && data.coloc_groups.length > 0) {
            const colocTSV = this.arrayToTSV(data.coloc_groups);
            zip.file('coloc_groups.tsv', colocTSV);
        }

        if (data.variants && data.variants.length > 0) {
            const variantsTSV = this.arrayToTSV(data.variants);
            zip.file('variants.tsv', variantsTSV);
        }

        if (data.variant) {
            const variantJSON = JSON.stringify(data.variant, null, 2);
            zip.file('variant.json', variantJSON);
        }

        if (data.pairwise_colocs && data.pairwise_colocs.length > 0) {
            const pairwiseColocTSV = this.arrayToTSV(data.pairwise_colocs);
            zip.file('coloc_pairs.tsv', pairwiseColocTSV);
        }

        if (data.rare_results && data.rare_results.length > 0) {
            const rareTSV = this.arrayToTSV(data.rare_results);
            zip.file('rare.tsv', rareTSV);
        }

        if (data.study_extractions && data.study_extractions.length > 0) {
            const studyTSV = this.arrayToTSV(data.study_extractions);
            zip.file('study_extractions.tsv', studyTSV);
        }

        const newZipBlob = await zip.generateAsync({ type: 'blob' });
        this.downloadBlob(newZipBlob, `gpmap_${name}.zip`);
    },

    arrayToTSV(data) {
        if (!data.length) return '';
        const keys = Object.keys(data[0]);
        const rows = data.map(row => keys.map(k => row[k]).join('\t'));
        return keys.join('\t') + '\n' + rows.join('\n');
    },

    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        URL.revokeObjectURL(url);
    }
}