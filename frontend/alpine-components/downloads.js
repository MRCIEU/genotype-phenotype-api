export default {
  /**
   * Downloads a JSON object as a CSV file.
   * @param {Object} snpData - The JSON object to convert to CSV.
   * @param {Object} colocData - The JSON object to convert to CSV.
   * @param {string} filename - The name of the file to save.
   */
  downloadToCSV(snpData, colocData, filename = 'coloc_data.csv') {
    // Define the CSV headers based on the coloc and association properties
    const headers = [
      'candidate_snp', 'rsid', 'chr', 'bp', 'ea', 'oa', 'posterior_prob', 
      'regional_prob', 'posterior_explained_by_snp', 'min_p', 'cis_trans',
      'trait', 'data_type', 'tissue', 'known_gene',
      'beta', 'se', 'p', 'eaf', 'imputed'
    ];
    
    // Create CSV content starting with headers
    let csvContent = headers.join(',') + '\n';
    
    // Add each row of data
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
        coloc.known_gene || '',
        // Association data if available
        coloc.association ? coloc.association.beta || '' : '',
        coloc.association ? coloc.association.se || '' : '',
        coloc.association ? coloc.association.p || '' : '',
        coloc.association ? coloc.association.eaf || '' : '',
        coloc.association ? (coloc.association.imputed ? 'true' : 'false') : ''
      ];
      
      // Handle values that might contain commas by quoting them
      const formattedRow = row.map(value => {
        // Convert to string and check if it needs quotes
        const stringValue = String(value);
        return stringValue.includes(',') ? `"${stringValue}"` : stringValue;
      });
      
      csvContent += formattedRow.join(',') + '\n';
    });
    
    // Create a Blob with the CSV content
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // Create a download link and trigger the download
    const link = document.createElement('a');
    
    // Create a URL for the blob
    const url = URL.createObjectURL(blob);
    
    // Set link properties
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    // Add to document, click to download, then remove
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up by revoking the object URL
    URL.revokeObjectURL(url);
  }
}