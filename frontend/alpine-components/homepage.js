import logo from '../assets/images/logo.png'
import constants from './constants'

export default function homepage() {
    return {
        logo,
        searchText: '',
        searchOptionData: [],
        uploadMetadata: {
            currentlyUploading: false,
            modalOpen: false,
            successModalOpen: false,
            successMessage: '',
            formData: {},
            validationErrors: {},
        },
        searchMetadata: {
            searchOpen: false,
            searchDelay: 300,
            minSearchChars: 2,
            searchTimeout: null,
        },
        filteredItems: [],
        errorMessage: null,

        async loadData() {
            try {
                console.log(import.meta.env)
                const response = await fetch(constants.apiUrl + '/search/options', {
                    method: 'GET',
                    headers: {
                        'Cache-Control': 'no-cache',  // Forces revalidation
                        'Pragma': 'no-cache'          // For older browsers
                    },
                });
                
                if (!response.ok) {
                    this.errorMessage = `Failed to load search options: ${response.status} ${constants.apiUrl + '/search/options'}`
                    return;
                }

                // Check if response was from cache
                if (response.headers.get('x-cache') === 'HIT') {
                    console.log('Data loaded from cache');
                }

                this.searchOptionData = await response.json();
            } catch (error) {
                console.error('Error loading data:', error);
            }
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
            if (this.searchMetadata.searchTimeout) {
                clearTimeout(this.searchMetadata.searchTimeout);
            }

            if (this.searchText.length < this.searchMetadata.minSearchChars) {
                this.filteredItems = [];
                return this.filteredItems;
            }

            this.searchMetadata.searchTimeout = setTimeout(() => {
                this.filteredItems = this.searchOptionData.filter((item) => {
                    return item.name.toLowerCase().includes(this.searchText.toLowerCase());
                });
                this.searchMetadata.searchOpen = this.filteredItems.length > 0;
            }, this.searchMetadata.searchDelay);

            return this.filteredItems;
        },

        doesUploadHaveErrors() {
            this.uploadMetadata.validationErrors = {};
            let hasErrors = false;
            const requiredFields = [
                'traitName',
                'file',
                'email',
                'sampleSize',
                'genomeBuild',
                'chr',
                'bp',
                'ea',
                'oa',
                'beta',
                'se',
                'pval',
                'eaf'
            ];
            console.log('genomeBuild')
            console.log(this.uploadMetadata.formData.genomeBuild)

            requiredFields.forEach((field) => {
                if (!this.uploadMetadata.formData[field]) {
                    this.uploadMetadata.validationErrors[field] = true;
                    hasErrors = true;
                }
            });
            console.log(this.uploadMetadata.validationErrors)

            if (this.uploadMetadata.formData.isPublished && !this.uploadMetadata.formData.doi) {
                this.uploadMetadata.validationErrors.doi = true 
                hasErrors = true;
            }

            return hasErrors;
        },

        async uploadGWAS() {
            if (this.doesUploadHaveErrors()) {
                return;
            }

            this.uploadMetadata.currentlyUploading = true;

            const gwasRequest = {
                trait_name: this.uploadMetadata.formData.traitName,
                reference_build: this.uploadMetadata.formData.genomeBuild,
                email: this.uploadMetadata.formData.email,
                study_type: this.uploadMetadata.formData.studyType.toLowerCase(),
                is_published: !!this.uploadMetadata.formData.isPublished,
                doi: this.uploadMetadata.formData.doi,
                permanent: !!this.uploadMetadata.formData.permanent,
                sample_size: this.uploadMetadata.formData.sampleSize,
                study_name: this.uploadMetadata.formData.studyName,
                ancestry: this.uploadMetadata.formData.ancestry,
                column_names: {
                    chr: this.uploadMetadata.formData.chr,
                    bp: this.uploadMetadata.formData.bp,
                    ea: this.uploadMetadata.formData.ea,
                    oa: this.uploadMetadata.formData.oa,
                    beta: this.uploadMetadata.formData.beta,
                    se: this.uploadMetadata.formData.se,
                    pval: this.uploadMetadata.formData.pval,
                    eaf: this.uploadMetadata.formData.eaf,
                    rsid: this.uploadMetadata.formData.rsid
                }
            };

            const formData = new FormData();
            formData.append('file', this.uploadMetadata.formData.file);
            formData.append('request', JSON.stringify(gwasRequest));

            try {
                const response = await fetch(constants.apiUrl + '/gwas/', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
                }
                const result = await response.json();
                this.uploadMetadata.currentlyUploading = false;
                this.uploadMetadata.modalOpen = false;
                this.uploadMetadata.successMessage = 'Upload successful: ' + JSON.stringify(result);
                this.uploadMetadata.successModalOpen = true;
            } catch (error) {
                alert('Error uploading file: ' + error.message);
                this.uploadMetadata.currentlyUploading = false;
            }
        },

        closeSuccessModal() {
            this.uploadMetadata.successModalOpen = false;
            this.uploadMetadata.successMessage = '';
        },
    }
}