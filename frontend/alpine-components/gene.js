import Alpine from "alpinejs";
import { stringify } from "flatted";
import * as d3 from "d3";
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
                const response = await fetch(constants.apiUrl + "/genes/" + geneId);
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

            this.data.coloc_groups = this.data.coloc_groups.filter(coloc => {
                let graphOptionFilters =
                    coloc.min_p <= graphOptions.pValue &&
                    graphOptions.colocType === coloc.group_threshold &&
                    (graphOptions.includeTrans ? true : coloc.cis_trans !== "trans") &&
                    (graphOptions.traitType === "all"
                        ? true
                        : graphOptions.traitType === "molecular"
                          ? coloc.data_type !== "Phenotype"
                          : graphOptions.traitType === "Phenotype"
                            ? coloc.data_type === "Phenotype"
                            : true);

                if (Object.values(graphOptions.categories).some(c => c)) {
                    graphOptionFilters = graphOptionFilters && graphOptions.categories[coloc.trait_category] === true;
                }

                return graphOptionFilters;
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

                if (Object.values(graphOptions.categories).some(c => c)) {
                    graphOptionFilters = graphOptionFilters && graphOptions.categories[study.trait_category] === true;
                }

                return graphOptionFilters;
            });

            // Then, organise data for graphs, once filtering is done
            this.filteredData.studies.sort((a, b) => a.mbp - b.mbp);
            this.minMbp = Math.min(
                ...this.data.coloc_groups.map(d => d.mbp),
                ...this.filteredData.rare.map(d => d.mbp),
                this.data.gene.minMbp
            );
            this.maxMbp = Math.max(
                ...this.data.coloc_groups.map(d => d.mbp),
                ...this.filteredData.rare.map(d => d.mbp),
                this.data.gene.maxMbp
            );

            this.filteredData.groupedRare = graphTransformations.groupBySnp(
                this.filteredData.rare,
                "gene",
                this.data.gene.id,
                this.displayFilters
            );
            this.filteredData.groupedColocs = graphTransformations.groupBySnp(
                this.data.coloc_groups,
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
            return this.data.coloc_groups && this.data.coloc_groups.length > 0;
        },

        get genomicRange() {
            return this.data ? `${this.data.gene.chr}:${this.data.gene.start}-${this.data.gene.stop}` : "...";
        },

        get ldBlockId() {
            return this.data && this.data.coloc_groups && this.data.coloc_groups.length > 0
                ? this.data.coloc_groups[0].ld_block_id
                : null;
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

            const tableData = Object.fromEntries(
                Object.entries(this.filteredData.groupedColocs).filter(([candidateSnp]) => {
                    return (
                        this.displayFilters.candidateSnp === null || candidateSnp === this.displayFilters.candidateSnp
                    );
                })
            );
            return stringify(Object.fromEntries(Object.entries(tableData).slice(0, constants.maxSNPGroupsToDisplay)));
        },

        get getDataForRareTable() {
            if (!this.filteredData.rare || this.filteredData.rare.length === 0) return [];
            const tableData = Object.fromEntries(
                Object.entries(this.filteredData.groupedRare).filter(([candidateSnp]) => {
                    return (
                        this.displayFilters.candidateSnp === null || candidateSnp === this.displayFilters.candidateSnp
                    );
                })
            );
            return stringify(Object.fromEntries(Object.entries(tableData).slice(0, constants.maxSNPGroupsToDisplay)));
        },

        initTraitByPositionGraph() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("trait-by-position-chart");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () =>
                this.getTraitByPositionGraph()
            );
        },

        initAssociatedGenesGraph() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("associated-genes-plot");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () =>
                this.getAssociatedGenesGraph()
            );
        },

        getTraitByPositionGraph() {
            graphTransformations.traitByPositionGraph.bind(this)();
        },

        getAssociatedGenesGraph() {
            const container = document.getElementById("associated-genes-plot");
            if (!container || !this.filteredData.associatedGenes) return;
            container.innerHTML = "";

            const graphConstants = {
                width: container.clientWidth,
                height: 300,
                outerMargin: {
                    top: 20,
                    right: 20,
                    bottom: 80,
                    left: 60,
                },
            };

            const innerWidth =
                graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
            const innerHeight =
                graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

            const svg = d3
                .select("#associated-genes-plot")
                .append("svg")
                .attr("viewBox", `0 0 ${graphConstants.width} ${graphConstants.height}`)
                .attr("preserveAspectRatio", "xMidYMid meet")
                .style("width", "100%")
                .style("height", "100%")
                .append("g")
                .attr("transform", `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

            // Convert associatedGenes to array and sort by count
            const geneData = Object.entries(this.filteredData.associatedGenes)
                .map(([gene, entries]) => ({
                    gene,
                    count: entries.length,
                }))
                .sort((a, b) => b.count - a.count);

            // Create scales
            const x = d3
                .scaleBand()
                .domain(geneData.map(d => d.gene))
                .range([0, innerWidth])
                .padding(0.1);

            const y = d3
                .scaleLinear()
                .domain([0, d3.max(geneData, d => d.count)])
                .nice()
                .range([innerHeight, 0]);

            // Add bars
            svg.selectAll("rect")
                .data(geneData)
                .enter()
                .append("rect")
                .attr("x", d => x(d.gene))
                .attr("y", d => y(d.count))
                .attr("width", x.bandwidth())
                .attr("height", d => innerHeight - y(d.count))
                .attr("fill", "#7eb0d5")
                .on("mouseover", function (event, d) {
                    d3.select(this)
                        .attr("fill", "#fd7f6f")
                        .style("cursor", "pointer")
                        .style("stroke", "#808080")
                        .style("stroke-width", 3);
                    graphTransformations.getTooltip(`Gene: ${d.gene}<br>Count: ${d.count}`, event);
                })
                .on("click", (event, d) => {
                    this.displayFilters.gene = d.gene;
                })
                .on("mouseout", function () {
                    d3.select(this).attr("fill", "#7eb0d5").style("stroke", null).style("stroke-width", null);
                    d3.selectAll(".tooltip").remove();
                });

            // Add x-axis
            svg.append("g")
                .attr("transform", `translate(0,${innerHeight})`)
                .call(d3.axisBottom(x))
                .selectAll("text")
                .attr("transform", "rotate(-45)")
                .style("text-anchor", "end")
                .style("font-size", "10px");

            // Add y-axis
            const maxCount = d3.max(geneData, d => d.count);
            svg.append("g").call(d3.axisLeft(y).ticks(Math.min(5, maxCount)).tickFormat(d3.format("d")));

            // Add labels
            svg.append("text")
                .attr("x", innerWidth / 2)
                .attr("y", innerHeight + graphConstants.outerMargin.bottom - 10)
                .style("text-anchor", "middle")
                .text("Gene");

            svg.append("text")
                .attr("transform", "rotate(-90)")
                .attr("x", -innerHeight / 2)
                .attr("y", -40)
                .style("text-anchor", "middle")
                .text("Number of Associations");
        },
    };
}
