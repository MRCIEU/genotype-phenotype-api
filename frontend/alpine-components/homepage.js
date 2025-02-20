import logo from '../assets/images/logo.png'
import constants from './constants'

export default function homepage() {
  return {
    logo,
    searchText: '',
    searchOptionData: [],
    uploadMetadata: {
      modalOpen: false,
      gwasUploadData: null,
      uploadFileName: null,
      uploadPValue: 7.3,
    },
    searchMetadata: {
      searchOpen: false,
      searchDelay: 300, // Delay in milliseconds
      minSearchChars: 2, // Minimum characters before searching
      searchTimeout: null, // Timeout reference
    },
    filteredItems: [], // Property to store filtered items

    async loadData() {
      const response = await fetch(constants.apiUrl + '/search/options')
      this.searchOptionData = await response.json()
    },

    goToItem(item) {
      if (item.type === 'study') {
        window.location.href = 'phenotype.html?id=' + item.type_id;
      } else if (item.type === 'gene') {
        window.location.href = 'gene.html?id=' + item.type_id;
      }
      this.search = ''
    },

    openModal() {
      this.uploadMetadata.modalOpen = true
      console.log(this.uploadMetadata.modalOpen)
    },

    closeModal() {
      this.uploadMetadata.modalOpen = false 
      console.log(this.uploadMetadata.modalOpen)
    },

    closeSearch() {
      this.search = ''
      this.searchMetadata.searchOpen = false
    },

    get getItemsForSearch() {
      // Clear the previous timeout if it exists
      if (this.searchMetadata.searchTimeout) {
        clearTimeout(this.searchMetadata.searchTimeout);
      }

      // Return the current filtered items
      if (this.searchText.length < this.searchMetadata.minSearchChars) {
        this.filteredItems = []; // Clear filtered items if not enough characters
        return this.filteredItems;
      }

      // Set a new timeout
      this.searchMetadata.searchTimeout = setTimeout(() => {
        this.filteredItems = this.searchOptionData.filter((item) => {
          return item.name.toLowerCase().includes(this.searchText.toLowerCase());
        });
        console.log(this.filteredItems);
        this.searchMetadata.searchOpen = this.filteredItems.length > 0; // Update searchOpen based on filtered items
      }, this.searchMetadata.searchDelay); // Delay execution by this.searchDelay milliseconds

      return this.filteredItems; // Return the filtered items
    },

    // look into npm library called pako
    filterAndUploadFile(file) {
      const reader = new FileReader();
      reader.onload = function(e) {
        const contents = e.target.result;

        // Process CSV data
        const filteredData = filterCSVData(contents);
        
        // Display filtered data in <pre> tag for preview
        // document.getElementById('output').textContent = filteredData.join('\n');

        // Attach filtered data to upload button
        // document.getElementById('uploadBtn').onclick = function() {
            // uploadFilteredData(filteredData);
        // };
      }; 
      reader.readAsText(file);
    },

      filterCSVData(csvText) {
        const lines = csvText.split('\n');
        
        // Extract header and filter conditions
        const header = lines[0].split(',');
        const dataRows = lines.slice(1);
    
        // Example filter: Keep rows where column 2 value > 100
        const filteredRows = dataRows.filter(row => {
            const cols = row.split(',');
            return cols[1] && parseFloat(cols[1]) > 100;  // Change condition as needed
        });
    
        return [header.join(',')].concat(filteredRows);  // Keep header, return filtered data
    },
  
    uploadFilteredData(filteredData) {
        const csvBlob = new Blob([filteredData.join('\n')], { type: 'text/csv' });
    
        const formData = new FormData();
        formData.append('file', csvBlob, 'filtered-data.csv');
    
        fetch('/upload-endpoint', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(result => {
            alert('Upload successful: ' + JSON.stringify(result));
        })
        .catch(error => {
            alert('Error uploading file: ' + error.message);
        });
    }
  }
}