import Alpine from "alpinejs";
import { stringify } from "flatted";
import constants from "./constants.js";
import downloads from "./downloads.js";
import graphTransformations from "./graphTransformations.js";

export default function gene() {
    return {
        data: null,
        downloadClicked: false,
        filteredData: {
            coloc_groups: null,
            groupedColocs: null,
            rare: null,
            groupedRare: null,
            associatedGenes: null,
            studies: null,
        },
        displayFilters: {
            candidateSnp: null,
            traitName: null,
            gene: null,
        },
        traitSearch: {
            text: "",
            showDropDown: false,
            orderedTraits: null,
        },
        svg: null,
        showTables: {
            coloc: true,
            rare: true,
            soloStudies: true,
        },
        minMbp: null,
        maxMbp: null,
        errorMessage: null,

        async loadData() {
            const geneId = new URLSearchParams(location.search).get("id");
            document.title = "GP Map: " + geneId;
            try {
                const response = await fetch(constants.apiUrl + "/genes/" + geneId + "?include_trans=false");
                if (!response.ok) {
                    this.errorMessage = `Failed to load gene: ${geneId}. Please try again later.`;
                    console.log(this.errorMessage);
                    return;
                }
                this.data = await response.json();
                this.transformDataForGraphs();
            } catch (error) {
                console.error("Error loading data:", error);
            }
        },

        transformDataForGraphs() {
            this.data.gene.minMbp = this.data.gene.start / 1000000;
            this.data.gene.maxMbp = this.data.gene.stop / 1000000;

            this.data.coloc_groups = this.data.coloc_groups.map(coloc => {
                const variantType = this.data.variants.find(variant => variant.SNP === coloc.display_snp);
                return {
                    ...coloc,
                    type: "coloc",
                    mbp: coloc.bp / 1000000,
                    variantType: variantType ? variantType.Consequence.split(",")[0] : null,
                };
            });
            this.data.coloc_groups = graphTransformations.addColorForSNPs(this.data.coloc_groups);

            this.data.rare_results = this.data.rare_results.map(rareResult => {
                const variantType = this.data.variants.find(variant => variant.SNP === rareResult.display_snp);
                return {
                    ...rareResult,
                    type: "rare",
                    mbp: rareResult.bp / 1000000,
                    variantType: variantType ? variantType.Consequence.split(",")[0] : null,
                };
            });
            this.data.rare_results = graphTransformations.addColorForSNPs(this.data.rare_results);

            this.data.study_extractions = this.data.study_extractions.map(study => ({
                ...study,
                mbp: study.bp / 1000000,
            }));

            this.data.gene.genes_in_region = this.data.gene.genes_in_region.map(gene => ({
                ...gene,
                minMbp: gene.start / 1000000,
                maxMbp: gene.stop / 1000000,
                focus: gene.gene === this.data.gene.gene,
            }));

            this.data.study_extractions = this.data.study_extractions.map(study => ({
                ...study,
                mbp: study.bp / 1000000,
            }));
        },

        filterDataForGraphs() {
            if (!this.data) return;
            const graphOptions = Alpine.store("graphOptionStore");
            const selectedCategories = graphTransformations.selectedTraitCategories(graphOptions);

            this.filteredData.coloc_groups = this.data.coloc_groups.filter(coloc => {
                let graphOptionFilters =
                    coloc.min_p <= graphOptions.pValue &&
                    (graphOptions.includeTrans ? true : coloc.cis_trans !== "trans") &&
                    (graphOptions.traitType === "all"
                        ? true
                        : graphOptions.traitType === "molecular"
                          ? coloc.data_type !== "Phenotype"
                          : graphOptions.traitType === "Phenotype"
                            ? coloc.data_type === "Phenotype"
                            : true);

                let categoryFilters = true;
                if (selectedCategories.size > 0) {
                    categoryFilters =
                        selectedCategories.has(coloc.trait_category) || coloc.gene_id === this.data.gene.id;
                }

                return graphOptionFilters && categoryFilters;
            });

            this.filteredData.rare = this.data.rare_results.filter(rare => {
                let graphOptionFilters = rare.min_p <= graphOptions.pValue;
                return graphOptionFilters;
            });

            this.filteredData.studies = this.data.study_extractions.filter(study => {
                let graphOptionFilters =
                    study.min_p <= graphOptions.pValue &&
                    (graphOptions.includeTrans ? true : study.cis_trans !== "trans") &&
                    (graphOptions.onlyMolecularTraits ? study.data_type !== "Phenotype" : true);

                if (selectedCategories.size > 0) {
                    graphOptionFilters = graphOptionFilters && selectedCategories.has(study.trait_category);
                }

                return graphOptionFilters;
            });

            // Then, organise data for graphs, once filtering is done
            this.filteredData.studies.sort((a, b) => a.mbp - b.mbp);
            this.minMbp = Math.min(
                ...this.filteredData.coloc_groups.map(d => d.mbp),
                ...this.filteredData.rare.map(d => d.mbp),
                this.data.gene.minMbp
            );
            this.maxMbp = Math.max(
                ...this.filteredData.coloc_groups.map(d => d.mbp),
                ...this.filteredData.rare.map(d => d.mbp),
                this.data.gene.maxMbp
            );

            this.filteredData.groupedRare = graphTransformations.groupBySnp(
                this.filteredData.rare,
                "situated_gene",
                this.data.gene.situated_gene_id,
                this.displayFilters
            );
            this.filteredData.groupedColocs = graphTransformations.groupBySnp(
                this.filteredData.coloc_groups,
                "gene",
                this.data.gene.id,
                this.displayFilters
            );
            this.filteredData.groupedResults = { ...this.filteredData.groupedColocs, ...this.filteredData.groupedRare };

            // Flatten all groupedResults arrays, then group by gene
            const allGroupedEntries = Object.values(this.filteredData.groupedResults).flat();
            this.filteredData.associatedGenes = Object.groupBy(allGroupedEntries, ({ gene }) => gene);
            delete this.filteredData.associatedGenes[null];
            delete this.filteredData.associatedGenes["NA"];
            delete this.filteredData.associatedGenes[this.data.gene.gene];

            this.filteredData.studies = [];
            this.traitSearch.orderedTraits = graphTransformations.getOrderedTraits(this.filteredData.groupedResults);
        },

        get geneName() {
            return new URLSearchParams(location.search).get("id");
        },

        get filteredColocDataExist() {
            if (!this.data) return false;
            this.filterDataForGraphs();
            return this.filteredData.coloc_groups && this.filteredData.coloc_groups.length > 0;
        },

        get genePleiotropy() {
            return this.data && this.data.gene.distinct_trait_categories && this.data.gene.distinct_protein_coding_genes
                ? `Pleiotropy info: ${this.data.gene.distinct_trait_categories} distinct trait categories, ${this.data.gene.distinct_protein_coding_genes} distinct protein coding genes`
                : "";
        },

        get genomicRange() {
            return this.data ? `${this.data.gene.chr}:${this.data.gene.start}-${this.data.gene.stop}` : "...";
        },

        get ldBlockId() {
            return this.data && this.data.coloc_groups ? this.data.coloc_groups[0].ld_block_id : null;
        },

        getTraitsToFilterBy() {
            if (this.traitSearch.orderedTraits === null) return [];
            return this.traitSearch.orderedTraits.filter(
                text => !this.traitSearch.text || text.toLowerCase().includes(this.traitSearch.text.toLowerCase())
            );
        },

        removeDisplayFilters() {
            this.downloadClicked = false;
            this.displayFilters = {
                traitName: null,
                candidateSnp: null,
                gene: null,
            };
            this.traitSearch.text = "";
        },

        filterByTrait(trait) {
            if (trait !== null) {
                this.displayFilters.traitName = trait;
            }
        },

        async downloadData() {
            this.downloadClicked = true;
            await downloads.downloadDataToZip(this.data, this.data.gene.gene);
        },

        get getDataForColocTable() {
            if (!this.data || !this.data.coloc_groups || this.data.coloc_groups.length === 0) return [];

            let tableData = Object.fromEntries(Object.entries(this.filteredData.groupedColocs));

            // If a SNP is selected, reorder so that its group appears first
            if (this.displayFilters.candidateSnp) {
                const entries = Object.entries(tableData);
                const selectedIndex = entries.findIndex(([snp]) => snp === this.displayFilters.candidateSnp);
                if (selectedIndex > 0) {
                    const selectedEntry = entries[selectedIndex];
                    entries.splice(selectedIndex, 1);
                    entries.unshift(selectedEntry);
                    tableData = Object.fromEntries(entries);
                }
            }

            return stringify(Object.fromEntries(Object.entries(tableData).slice(0, constants.maxSNPGroupsToDisplay)));
        },

        get getDataForRareTable() {
            if (!this.filteredData.rare || this.filteredData.rare.length === 0) return [];

            let tableData = Object.fromEntries(Object.entries(this.filteredData.groupedRare));

            // If a SNP is selected, reorder so that its group appears first
            if (this.displayFilters.candidateSnp) {
                const entries = Object.entries(tableData);
                const selectedIndex = entries.findIndex(([snp]) => snp === this.displayFilters.candidateSnp);
                if (selectedIndex > 0) {
                    const selectedEntry = entries[selectedIndex];
                    entries.splice(selectedIndex, 1);
                    entries.unshift(selectedEntry);
                    tableData = Object.fromEntries(entries);
                }
            }

            return stringify(Object.fromEntries(Object.entries(tableData).slice(0, constants.maxSNPGroupsToDisplay)));
        },

        initTraitByPositionGraph() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("trait-by-position-chart");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () =>
                this.getTraitByPositionGraph()
            );
        },

        getTraitByPositionGraph() {
            graphTransformations.traitByPositionGraph.bind(this)();
        },
    };
}
