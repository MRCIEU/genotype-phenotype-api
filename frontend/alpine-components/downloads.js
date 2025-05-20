export default {
  /**
   * Downloads a JSON object as a CSV file.
   * @param {Object} snpData - The JSON object to convert to CSV.
   * @param {Object} colocData - The JSON object to convert to CSV.
   * @param {string} filename - The name of the file to save.
   */
  downloadColocsToCSV(snpData, colocData, filename = 'coloc_data.csv') {
    const headers = [
      'candidate_snp', 'rsid', 'chr', 'bp', 'ea', 'oa', 'posterior_prob', 
      'regional_prob', 'posterior_explained_by_snp', 'min_p', 'cis_trans',
      'trait', 'data_type', 'tissue', 'gene',
      'beta', 'se', 'p', 'eaf', 'imputed'
    ];
    
    let csvContent = headers.join(',') + '\n';
    colocData.forEach(coloc => {
      const row = [
        coloc.candidate_snp || '',
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
  }
}