import { stringify } from "flatted";

import constants from "./constants.js";
import graphTransformations from "./graphTransformations.js";
import downloads from "./downloads.js";

export default function region() {
    return {
        data: null,
        downloadClicked: false,
        filteredData: {
            colocs: null,
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
        totalColocGroups: 0,
        totalRareGroups: 0,
        errorMessage: null,
        rPackageModalOpen: false,

        async loadData() {
            const ldBlockId = new URLSearchParams(location.search).get("id");
            try {
                const response = await fetch(constants.apiUrl + "/regions/" + ldBlockId);
                if (!response.ok) {
                    this.errorMessage = `Failed to load region: ${ldBlockId}. Please try again later.`;
                    console.log(this.errorMessage);
                    return;
                }
                this.data = await response.json();
                document.title = "GPMap Region: " + this.regionName;
                this.transformDataForGraphs();
            } catch (error) {
                console.error("Error loading data:", error);
            }
        },

        transformDataForGraphs() {
            this.minMbp = this.data.region.start / 1000000;
            this.maxMbp = this.data.region.stop / 1000000;

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

            this.data.genes_in_region = this.data.genes_in_region.map(gene => ({
                ...gene,
                minMbp: gene.start / 1000000,
                maxMbp: gene.stop / 1000000,
            }));
        },

        filterDataForGraphs() {
            if (!this.data) return;
            const graphOptions = Alpine.store("graphOptionStore");
            const selectedCategories = graphTransformations.selectedTraitCategories(graphOptions);

            this.filteredData.colocs = this.data.coloc_groups.filter(coloc => {
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
                    categoryFilters = selectedCategories.has(coloc.trait_category);
                }

                return graphOptionFilters && categoryFilters;
            });

            this.filteredData.rare = this.data.rare_results.filter(rare => {
                let graphOptionFilters = rare.min_p <= graphOptions.pValue;
                return graphOptionFilters;
            });

            this.filteredData.groupedRare = graphTransformations.groupBySnp(
                this.filteredData.rare,
                null,
                null,
                this.displayFilters
            );
            this.filteredData.groupedColocs = graphTransformations.groupBySnp(
                this.filteredData.colocs,
                null,
                null,
                this.displayFilters
            );
            this.filteredData.groupedResults = { ...this.filteredData.groupedColocs, ...this.filteredData.groupedRare };

            const dropdownColocs = graphTransformations.groupBySnp(
                this.filteredData.colocs, null, null, {}
            );
            const dropdownRare = graphTransformations.groupBySnp(
                this.filteredData.rare, null, null, {}
            );
            this.totalColocGroups = Object.keys(dropdownColocs).length;
            this.totalRareGroups = Object.keys(dropdownRare).length;
            this.traitSearch.orderedTraits = graphTransformations.getOrderedTraits(
                { ...dropdownColocs, ...dropdownRare }
            );
        },

        get regionName() {
            if (this.data === null) return null;
            return (
                this.data.region.ancestry +
                " " +
                this.data.region.chr +
                ":" +
                this.data.region.start +
                "-" +
                this.data.region.stop
            );
        },

        getTraitsToFilterBy() {
            return graphTransformations.buildFilterDropdownItems(this.traitSearch.orderedTraits, this.traitSearch.text);
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

        filterByTrait(item) {
            if (!item) return;
            if (item.type === "trait") {
                this.displayFilters.traitName = item.label;
                this.displayFilters.gene = null;
            } else if (item.type === "gene") {
                this.displayFilters.gene = item.label;
                this.displayFilters.traitName = null;
            }
        },

        openRPackageModal() {
            this.rPackageModalOpen = true;
        },

        closeRPackageModal() {
            this.rPackageModalOpen = false;
        },

        get filteredColocDataExist() {
            this.filterDataForGraphs();
            return this.data && this.filteredData.colocs && this.filteredData.colocs.length > 0;
        },

        async downloadData() {
            this.downloadClicked = true;
            await downloads.downloadDataToZip(this.data, this.data.region.ld_block);
        },

        get hasActiveDisplayFilter() {
            if (this.totalColocGroups < 5 && this.totalRareGroups < 5) return true;
            return (
                this.displayFilters.candidateSnp !== null ||
                this.displayFilters.traitName !== null ||
                this.displayFilters.gene !== null
            );
        },

        get getDataForColocTable() {
            if (!this.hasActiveDisplayFilter) return [];
            if (!this.data || !this.filteredData.colocs || this.filteredData.colocs.length === 0) return [];

            let entries = Object.entries(this.filteredData.groupedColocs);

            if (this.displayFilters.traitName) {
                entries = entries
                    .map(([snp, rows]) => [
                        snp,
                        rows.filter(r => r.trait_name === this.displayFilters.traitName),
                    ])
                    .filter(([_, rows]) => rows.length > 0);
            }

            if (this.displayFilters.gene) {
                const filterGene = this.displayFilters.gene;
                entries = entries
                    .map(([snp, rows]) => [
                        snp,
                        rows.filter(r => r.gene === filterGene || r.situated_gene === filterGene),
                    ])
                    .filter(([_, rows]) => rows.length > 0);
            }

            if (this.displayFilters.candidateSnp) {
                entries = entries.filter(([snp]) => snp === this.displayFilters.candidateSnp);
            }

            return stringify(Object.fromEntries(entries.slice(0, constants.maxSNPGroupsToDisplay)));
        },

        get getDataForRareTable() {
            if (!this.hasActiveDisplayFilter) return [];
            if (!this.filteredData.rare || this.filteredData.rare.length === 0) return [];

            let entries = Object.entries(this.filteredData.groupedRare);

            if (this.displayFilters.traitName) {
                entries = entries
                    .map(([snp, rows]) => [
                        snp,
                        rows.filter(r => r.trait_name === this.displayFilters.traitName),
                    ])
                    .filter(([_, rows]) => rows.length > 0);
            }

            if (this.displayFilters.gene) {
                const filterGene = this.displayFilters.gene;
                entries = entries
                    .map(([snp, rows]) => [
                        snp,
                        rows.filter(r => r.gene === filterGene || r.situated_gene === filterGene),
                    ])
                    .filter(([_, rows]) => rows.length > 0);
            }

            if (this.displayFilters.candidateSnp) {
                entries = entries.filter(([snp]) => snp === this.displayFilters.candidateSnp);
            }

            return stringify(Object.fromEntries(entries.slice(0, constants.maxSNPGroupsToDisplay)));
        },

        initColocByPositionGraph() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("coloc-by-position-chart");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () =>
                this.getColocByPositionGraph()
            );
        },

        getColocByPositionGraph() {
            graphTransformations.colocByPositionGraph.bind(this)();
        },
    };
}
