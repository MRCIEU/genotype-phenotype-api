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
            postUploadModalOpen: false,
            uploadSuccess: null,
            message: '',
            formData: {
                studyType: 'continuous',
                ancestry: 'EUR'
            },
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
                const response = await fetch(constants.apiUrl + '/search/options');
                
                if (!response.ok) {
                    this.errorMessage = `Failed to load search options: ${response.status} ${constants.apiUrl + '/search/options'}`
                    return;
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
        },

        closeModal() {
            this.uploadMetadata.modalOpen = false 
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

        doesUploadDataHaveErrors() {
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

            requiredFields.forEach((field) => {
                if (!this.uploadMetadata.formData[field]) {
                    this.uploadMetadata.validationErrors[field] = true;
                    hasErrors = true;
                }
            });

            if (this.uploadMetadata.formData.isPublished && !this.uploadMetadata.formData.doi) {
                this.uploadMetadata.validationErrors.doi = true 
                hasErrors = true;
            }

            return hasErrors;
        },

        async uploadGWAS() {
            if (this.doesUploadDataHaveErrors()) {
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
                    this.openPostUploadModal(false);
                }
                else {
                    const result = await response.json();
                    this.openPostUploadModal(true, result);
                }
            } catch (error) {
                this.openPostUploadModal(false);
            }
        },

        openPostUploadModal(isSuccess, result) {
            this.uploadMetadata.currentlyUploading = false;
            this.uploadMetadata.modalOpen = false;
            this.uploadMetadata.postUploadModalOpen = true;

            if (isSuccess) {
                this.uploadMetadata.uploadSuccess = true;
                this.uploadMetadata.message = 'Upload successful!  An email will be sent to ' + this.uploadMetadata.formData.email +
                    ' once the analysis has been completed.  Or, you can check the status of your upload ' + 
                    '<a href="upload.html?id=' + result.guid + '">here</a>.';
            }
            else {
                this.uploadMetadata.uploadSuccess = false;
                this.uploadMetadata.message = 'There was an error uploading your file. Please try again later.';
            }
        },

        closePostUploadModal() {
            this.uploadMetadata.postUploadModalOpen = false;
            this.uploadMetadata.message = '';
            this.uploadMetadata.uploadSuccess = null;
        },
    }
}