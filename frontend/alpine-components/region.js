import { stringify } from 'flatted';

import constants from './constants.js';
import graphTransformations from './graphTransformations.js';
import downloads from './downloads.js';

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
            text: '',
            showDropDown: false,
            orderedTraits: null,
        },
        svg: null,
        showTables: {
            coloc: true,
            rare: true,
            soloStudies: true
        },
        minMbp: null,
        maxMbp: null,
        errorMessage: null,

        async loadData() {
            const ldBlockId = new URLSearchParams(location.search).get('id')
            try {
                const response = await fetch(constants.apiUrl + '/regions/' + ldBlockId);
                if (!response.ok) {
                    this.errorMessage = `Failed to load region: ${ldBlockId}. Please try again later.`
                    console.log(this.errorMessage)
                    return
                }
                this.data = await response.json();
                document.title = 'GP Map Region: ' + this.regionName
                this.transformDataForGraphs()

            } catch (error) {
                console.error('Error loading data:', error);
            }
        },

        transformDataForGraphs() {
            this.minMbp = this.data.region.start / 1000000
            this.maxMbp = this.data.region.stop / 1000000

            this.data.coloc_groups = this.data.coloc_groups.map(coloc => {
                const variantType = this.data.variants.find(variant => variant.SNP === coloc.display_snp)
                return {
                    ...coloc,
                    type: 'coloc',
                    mbp : coloc.bp / 1000000,
                    variantType: variantType ? variantType.Consequence.split(",")[0] : null,
                }
            })
            this.data.coloc_groups = graphTransformations.addColorForSNPs(this.data.coloc_groups)

            this.data.rare_results = this.data.rare_results.map(rareResult => {
                const variantType = this.data.variants.find(variant => variant.SNP === rareResult.display_snp)
                return {
                    ...rareResult,
                    type: 'rare',
                    mbp : rareResult.bp / 1000000,
                    variantType: variantType ? variantType.Consequence.split(",")[0] : null,
                }
            })
            this.data.rare_results = graphTransformations.addColorForSNPs(this.data.rare_results)

            this.data.genes_in_region = this.data.genes_in_region.map(gene => ({
                ...gene,
                minMbp : gene.start / 1000000,
                maxMbp : gene.stop / 1000000,
            }))
        },

        filterDataForGraphs() {
            if (!this.data) return
            const graphOptions = Alpine.store('graphOptionStore');

            this.data.coloc_groups = this.data.coloc_groups.filter(coloc => {
                let graphOptionFilters = (coloc.min_p <= graphOptions.pValue &&
                    (graphOptions.colocType === coloc.group_threshold) &&
                   (graphOptions.includeTrans ? true : coloc.cis_trans !== 'trans') &&
                   (graphOptions.traitType === 'all' ? true : 
                    graphOptions.traitType === 'molecular' ? coloc.data_type !== 'Phenotype' :
                    graphOptions.traitType === 'Phenotype' ? coloc.data_type === 'Phenotype' : true))

                if (Object.values(graphOptions.categories).some(c => c)) {
                    graphOptionFilters = graphOptionFilters && graphOptions.categories[coloc.trait_category] === true
                }

                return graphOptionFilters
            })

            this.filteredData.rare = this.data.rare_results.filter(rare => {
                let graphOptionFilters = (rare.min_p <= graphOptions.pValue)
                return graphOptionFilters
            })

            this.filteredData.groupedRare = graphTransformations.groupBySnp(this.filteredData.rare, null, null, this.displayFilters)
            this.filteredData.groupedColocs = graphTransformations.groupBySnp(this.data.coloc_groups, null, null, this.displayFilters)
            this.filteredData.groupedResults = {...this.filteredData.groupedColocs, ...this.filteredData.groupedRare}

            this.traitSearch.orderedTraits = graphTransformations.getOrderedTraits(this.filteredData.groupedResults)
        },

        get regionName() {
            if (this.data === null) return null
            return this.data.region.ancestry + ' ' + this.data.region.chr + ':' + this.data.region.start + '-' + this.data.region.stop
        },

        getTraitsToFilterBy() {
            if (this.traitSearch.orderedTraits === null) return []
            return this.traitSearch.orderedTraits.filter(text =>
                !this.traitSearch.text || text.toLowerCase().includes(this.traitSearch.text.toLowerCase())
            )
        },

        removeDisplayFilters() {
            this.downloadClicked = false;
            this.displayFilters = {
                traitName: null,
                candidateSnp: null,
                gene: null,
            }
            this.traitSearch.text = ''
        },

        filterByTrait(trait) {
            if (trait !== null) {
                this.displayFilters.traitName = trait
            } 
        },

        get filteredColocDataExist() {
            this.filterDataForGraphs()
            return this.data && this.data.coloc_groups && this.data.coloc_groups.length > 0
        },

        async downloadData() {
            this.downloadClicked = true;
            await downloads.downloadDataToZip(this.data, this.data.region.ld_block);
        },

        get getDataForColocTable() {
            if (!this.data || !this.data.coloc_groups || this.data.coloc_groups.length === 0) return []

            const tableData = Object.fromEntries(
                Object.entries(this.filteredData.groupedColocs).filter(([candidateSnp, _]) => {
                    return this.displayFilters.candidateSnp === null || candidateSnp === this.displayFilters.candidateSnp
                })
            )
            return stringify(Object.fromEntries(Object.entries(tableData).slice(0, constants.maxSNPGroupsToDisplay)))
        },

        get getDataForRareTable() {
            if (!this.filteredData.rare || this.filteredData.rare.length === 0) return []
            const tableData = Object.fromEntries(
                Object.entries(this.filteredData.groupedRare).filter(([candidateSnp, _]) => {
                    return this.displayFilters.candidateSnp === null || candidateSnp === this.displayFilters.candidateSnp
                })
            )
            return stringify(Object.fromEntries(Object.entries(tableData).slice(0, constants.maxSNPGroupsToDisplay)))
        },

        initTraitByPositionGraph() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("trait-by-position-chart");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () => this.getTraitByPositionGraph())
        },

        getTraitByPositionGraph() {
            graphTransformations.traitByPositionGraph.bind(this)()
        },
    }
}