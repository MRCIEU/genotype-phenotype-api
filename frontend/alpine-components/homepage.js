import studies from '../sample_data/studies.json'
import logo from '../assets/images/logo.png'

export default function homepage() {
  return {
    logo,
    count: 0,
    searchOpen: false,
    search: '',
    dummyData: studies,
    modalOpen: false,
    gwasUploadData: null,
    uploadFileName: null,
    uploadPValue: 7.3,

    goToItem(item) {
      window.location.href = 'phenotype.html?id=' + item.id;
      this.search = ''
    },

    openModal() {
      this.modalOpen = true
      console.log(this.modalOpen)
    },

    closeModal() {
      this.modalOpen = false 
      console.log(this.modalOpen)
    },

    closeSearch() {
      this.search = ''
      this.searchOpen = false
    },

    get getItemsForSearch() {
      const filterItems = this.dummyData.filter((item) => {
        return item.name.toLowerCase().includes(this.search.toLowerCase())
      })
      if(filterItems.length < this.dummyData.length && filterItems.length > 0) {
        this.searchOpen = true
        return filterItems
      } else {
        this.searchOpen = false
      }
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