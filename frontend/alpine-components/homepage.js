import mrc_logo from "../assets/images/mrc_ieu.svg";
import logoLight from "../assets/images/logo.svg";
import logoDark from "../assets/images/logo-dark.svg";
import constants from "./constants";

export default function homepage() {
    return {
        logo: constants.darkMode ? logoDark : logoLight,
        mrc_logo,
        searchText: "",
        searchOptionData: [],
        variantSearchInProgress: false,
        variantSearchResponse: null,
        gpmapMetadata: null,
        rPackageModalOpen: false,
        uploadMetadata: {
            currentlyUploading: false,
            modalOpen: false,
            postUploadModalOpen: false,
            uploadSuccess: null,
            message: "",
            formData: {
                studyType: "continuous",
                ancestry: "EUR",
                pValueIndex: 7,
                pValue: 0.00000005,
                pValueOptions: [
                    0.00015, // 1.5e-4
                    0.00005, // 5e-5
                    0.00001, // 1e-5
                    0.000005, // 5e-6
                    0.000001, // 1e-6
                    0.0000005, // 5e-7
                    0.0000001, // 1e-7
                    0.00000005, // 5e-8
                ],
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

        async loadHomepage() {
            try {
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get("showUpload") === "true") {
                    this.openModal();
                }
                const response = await fetch(constants.apiUrl + "/search/options");

                if (!response.ok) {
                    this.errorMessage = `Failed to load search options: ${response.status} ${constants.apiUrl + "/search/options"}`;
                    return;
                }

                this.searchOptionData = await response.json();
                this.searchOptionData = this.searchOptionData.search_terms;
            } catch (error) {
                console.error("Error loading data:", error);
            }
        },

        async loadGPMapMetadata() {
            const response = await fetch(constants.apiUrl + "/info/gpmap_metadata");
            this.gpmapMetadata = await response.json();
        },

        async getVariantSearchResponse(variantText) {
            try {
                this.variantSearchInProgress = true;
                const response = await fetch(constants.apiUrl + "/search/variant/" + variantText);

                if (!response.ok) {
                    this.errorMessage = `Failed to load search options: ${response.status} ${constants.apiUrl + "/search/variant/" + variantText}`;
                    return;
                }

                this.variantSearchResponse = await response.json();
                this.variantSearchInProgress = false;
            } catch (error) {
                console.error("Error loading data:", error);
            }
        },

        goToItem(item) {
            console.log(item);
            if (item.type === "trait") {
                window.location.href = "trait.html?id=" + item.type_id;
            } else if (item.type === "gene") {
                window.location.href = "gene.html?id=" + item.type_id;
            }
            this.search = "";
        },

        openModal() {
            this.uploadMetadata.modalOpen = true;
        },

        closeModal() {
            if (!this.uploadMetadata.currentlyUploading) {
                this.uploadMetadata.modalOpen = false;
            }
        },

        closeSearch() {
            this.search = "";
            this.searchMetadata.searchOpen = false;
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
                this.filteredItems = this.searchOptionData.filter(item => {
                    return (
                        item.name.toLowerCase().includes(this.searchText.toLowerCase()) ||
                        (item.alt_name && item.alt_name.toLowerCase().includes(this.searchText.toLowerCase()))
                    );
                });
                this.searchMetadata.searchOpen = this.filteredItems.length > 0;
            }, this.searchMetadata.searchDelay);

            this.filteredItems.sort((a, b) => {
                const totalResultsA = a.num_rare_results + a.num_coloc_groups;
                const totalResultsB = b.num_rare_results + b.num_coloc_groups;
                return totalResultsB - totalResultsA;
            });
            return this.filteredItems;
        },

        get proxyVariants() {
            let pv = (this.variantSearchResponse && this.variantSearchResponse.proxy_variants) || [];
            return pv;
        },

        get originalVariants() {
            let ov = (this.variantSearchResponse && this.variantSearchResponse.original_variants) || [];
            return ov;
        },

        get getGPMapMetadata() {
            return this.gpmapMetadata
                ? this.gpmapMetadata
                : {
                      num_common_studies: 0,
                      num_rare_studies: 0,
                      num_molecular_studies: 0,
                      num_causal_variants: 0,
                  };
        },

        searchVariant() {
            const query = this.searchText.trim();
            if (!query || query.length < this.searchMetadata.minSearchChars) {
                return;
            }

            const isRsid = query.toLowerCase().startsWith("rs");
            const isChrBp = /^\d+:\d+(_[ACGT]+_[ACGT]+)?$/.test(query);

            if (isRsid || isChrBp) {
                this.getVariantSearchResponse(query);
                this.filteredItems = [];
            }
        },

        doesUploadDataHaveErrors() {
            this.uploadMetadata.validationErrors = {};
            let hasErrors = false;
            const requiredFields = [
                "traitName",
                "file",
                "email",
                "sampleSize",
                "genomeBuild",
                "pValueThreshold",
                "chr",
                "bp",
                "ea",
                "oa",
                "p",
                "eaf",
            ];

            // Check base required fields
            requiredFields.forEach(field => {
                if (!this.uploadMetadata.formData[field]) {
                    this.uploadMetadata.validationErrors[field] = true;
                    hasErrors = true;
                }
            });

            // Check effect size fields - must have either beta/SE or OR/LB/UB
            const hasBetaSE = this.uploadMetadata.formData.beta && this.uploadMetadata.formData.se;
            const hasORCI =
                this.uploadMetadata.formData.or && this.uploadMetadata.formData.lb && this.uploadMetadata.formData.ub;

            if (!hasBetaSE && !hasORCI) {
                this.uploadMetadata.validationErrors.beta = true;
                this.uploadMetadata.validationErrors.se = true;
                this.uploadMetadata.validationErrors.or = true;
                this.uploadMetadata.validationErrors.lb = true;
                this.uploadMetadata.validationErrors.ub = true;
                hasErrors = true;
            }

            if (this.uploadMetadata.formData.isPublished && !this.uploadMetadata.formData.doi) {
                this.uploadMetadata.validationErrors.doi = true;
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
                name: this.uploadMetadata.formData.traitName,
                reference_build: this.uploadMetadata.formData.genomeBuild,
                email: this.uploadMetadata.formData.email,
                category: this.uploadMetadata.formData.studyType.toLowerCase(),
                is_published: !!this.uploadMetadata.formData.isPublished,
                doi: this.uploadMetadata.formData.doi,
                should_be_added: !!this.uploadMetadata.formData.shouldBeAdded,
                sample_size: this.uploadMetadata.formData.sampleSize,
                ancestry: this.uploadMetadata.formData.ancestry,
                column_names: {
                    CHR: this.uploadMetadata.formData.chr,
                    BP: this.uploadMetadata.formData.bp,
                    EA: this.uploadMetadata.formData.ea,
                    OA: this.uploadMetadata.formData.oa,
                    BETA: this.uploadMetadata.formData.beta,
                    SE: this.uploadMetadata.formData.se,
                    OR: this.uploadMetadata.formData.or,
                    LB: this.uploadMetadata.formData.lb,
                    UB: this.uploadMetadata.formData.ub,
                    P: this.uploadMetadata.formData.p,
                    EAF: this.uploadMetadata.formData.eaf,
                },
            };

            const formData = new FormData();
            formData.append("file", this.uploadMetadata.formData.file);
            formData.append("request", JSON.stringify(gwasRequest));

            try {
                const response = await fetch(constants.apiUrl + "/gwas/", {
                    method: "POST",
                    body: formData,
                });

                if (!response.ok) {
                    this.openPostUploadModal(false);
                } else {
                    const result = await response.json();
                    this.openPostUploadModal(true, result);
                }
            } catch (error) {
                console.error(error);
                this.openPostUploadModal(false);
            }
        },

        openPostUploadModal(isSuccess, result) {
            this.uploadMetadata.currentlyUploading = false;
            this.uploadMetadata.modalOpen = false;
            this.uploadMetadata.postUploadModalOpen = true;

            if (isSuccess) {
                this.uploadMetadata.uploadSuccess = true;
                this.uploadMetadata.message =
                    "Upload successful!  An email will be sent to " +
                    this.uploadMetadata.formData.email +
                    " once the analysis has been completed.  Or, you can check the status of your upload " +
                    '<a href="trait.html?id=' +
                    result.guid +
                    '">here</a>.';
            } else {
                this.uploadMetadata.uploadSuccess = false;
                this.uploadMetadata.message = "There was an error uploading your file. Please try again later.";
            }
        },

        closePostUploadModal() {
            this.uploadMetadata.postUploadModalOpen = false;
            this.uploadMetadata.message = "";
            this.uploadMetadata.uploadSuccess = null;
        },

        openRPackageModal() {
            this.rPackageModalOpen = true;
        },

        closeRPackageModal() {
            this.rPackageModalOpen = false;
        },
    };
}
