import Alpine from "alpinejs";
import * as d3 from "d3";

import constants from "./constants.js";
import downloads from "./downloads.js";
import graphTransformations from "./graphTransformations.js";

export default function snp() {
    return {
        data: null,
        filteredData: {
            colocs: null,
            colocPairs: null,
            rare: null,
            studies: null,
        },
        errorMessage: null,

        async loadData() {
            let variantId = new URLSearchParams(location.search).get("id");

            try {
                const response = await fetch(
                    constants.apiUrl + "/variants/" + variantId + "?include_coloc_pairs=true&h4_threshold=0.5"
                );
                if (!response.ok) {
                    this.errorMessage = `Failed to load variant: ${response.status} ${constants.apiUrl + "/variants/" + variantId}`;
                    return;
                }
                this.data = await response.json();

                document.title = "GP Map: " + this.getSNPName();

                this.data.coloc_groups = this.data.coloc_groups.map(coloc => ({
                    ...coloc,
                    tissue: coloc.tissue ? coloc.tissue : "N/A",
                    cis_trans: coloc.cis_trans ? coloc.cis_trans : "N/A",
                }));
                this.data.coloc_groups.sort((a, b) => a.data_type.localeCompare(b.data_type));

                // let colocGroupIds = this.data.coloc_groups.map(coloc => coloc.coloc_group_id);
                // colocGroupIds = [...new Set(colocGroupIds)];
                const snpGraphStore = Alpine.store("snpGraphStore");
                snpGraphStore.colocs = this.data.coloc_groups;
                snpGraphStore.variant = this.data.variant;

                const ld_block = this.data.coloc_groups[0].ld_block;
                const ld_info = ld_block.split(/[/-]/);
                this.data.variant.min_bp = ld_info[2];
                this.data.variant.max_bp = ld_info[3];
            } catch (error) {
                console.error("Error loading data:", error);
            }
        },

        getSNPName() {
            return this.data ? this.data.variant.rsid.split(",")[0] : "...";
        },

        getVariantData() {
            return this.data ? this.data.variant : {};
        },

        getDataForTable() {
            return this.data ? this.filteredData.colocs : [];
        },

        downloadDataOnly() {
            if (!this.data || !this.filteredData.colocs || this.filteredData.colocs.length === 0) {
                return;
            }
            downloads.downloadDataToZip(this.data, this.getSNPName());
        },

        async downloadDataAndGWAS() {
            if (!this.data || !this.filteredData.colocs || this.filteredData.colocs.length === 0) {
                return;
            }
            const response = await fetch(constants.apiUrl + "/variants/" + this.data.variant.id + "/summary-stats");
            if (!response.ok) {
                this.errorMessage = `Failed to download summary stats: ${response.status} ${constants.apiUrl + "/variants/" + this.data.variant.id}`;
                return;
            }
            const zipBlob = await response.blob();
            downloads.downloadDataToZip(this.data, this.getSNPName(), zipBlob);
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
                          : graphOptions.traitType === "phenotype"
                            ? coloc.data_type === "Phenotype"
                            : true);

                let categoryFilters = true;
                if (selectedCategories.size > 0) {
                    categoryFilters = selectedCategories.has(coloc.trait_category);
                }

                return graphOptionFilters && categoryFilters;
            });

            const allRelevantStudyExtractionIds = new Set(
                this.filteredData.colocs.map(coloc => coloc.study_extraction_id)
            );
            this.filteredData.colocPairs = this.data.coloc_pairs.filter(colocPair => {
                return (
                    allRelevantStudyExtractionIds.has(colocPair.study_extraction_a_id) &&
                    allRelevantStudyExtractionIds.has(colocPair.study_extraction_b_id)
                );
            });
        },

        initForestPlot() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("forest-plot");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () => this.getForestPlot());
        },

        initGraphClusterDiagram() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("graph-cluster-diagram");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () =>
                this.getGraphClusterDiagram()
            );
        },

        getGraphClusterDiagram() {
            if (!this.data || !this.filteredData.colocPairs) return;

            const chartElement = document.getElementById("graph-cluster-diagram");
            chartElement.innerHTML = "";

            const chartContainer = d3.select("#graph-cluster-diagram");
            const width = chartContainer.node().getBoundingClientRect().width - 50;
            const height = 500;

            // Create SVG
            const svg = chartContainer.append("svg").attr("width", width).attr("height", height);

            // Prepare data for force-directed graph
            const colocPairs = this.filteredData.colocPairs;

            // Get unique study extraction IDs from coloc pairs
            const studyExtractionIds = new Set();
            colocPairs.forEach(pair => {
                studyExtractionIds.add(pair.study_extraction_a_id);
                studyExtractionIds.add(pair.study_extraction_b_id);
            });

            // Create nodes (study extractions)
            const nodes = Array.from(studyExtractionIds).map(id => {
                const coloc = this.data.coloc_groups.find(c => c.study_extraction_id === id);
                return {
                    id: id,
                    name: coloc ? coloc.trait_name : `Study ${id}`,
                    data_type: coloc ? coloc.data_type : "Unknown",
                    min_p: coloc ? coloc.min_p : 1,
                    association: coloc ? coloc.association : null,
                    coloc_group_id: coloc ? coloc.coloc_group_id : null,
                };
            });

            // Create links (coloc pairs)
            const links = colocPairs.map(pair => ({
                source: pair.study_extraction_a_id,
                target: pair.study_extraction_b_id,
                h4: pair.h4,
                h3: pair.h3,
            }));

            // Color scale for data types
            const fixedColorMap = constants.orderedDataTypes
                .map((dataType, index) => ({
                    [dataType]: constants.colors.palette[index],
                }))
                .reduce((acc, obj) => ({ ...acc, ...obj }), {});

            const color = d3.scaleOrdinal().domain(Object.keys(fixedColorMap)).range(Object.values(fixedColorMap));

            // Calculate appropriate parameters based on number of nodes
            const nodeCount = nodes.length;
            const isLargeGraph = nodeCount > 100;

            // Adjust node size and spacing based on graph size
            const baseNodeRadius = isLargeGraph ? 3 : 8;
            const maxNodeRadius = isLargeGraph ? 8 : 15;
            const linkDistance = isLargeGraph ? 30 : 50;
            const chargeStrength = isLargeGraph ? -100 : -300;

            // Update node sizes
            nodes.forEach(node => {
                const pValueRadius = Math.max(baseNodeRadius, Math.min(maxNodeRadius, -Math.log10(node.min_p) * 1.5));
                node.radius = pValueRadius;
            });

            // Create force simulation with adaptive parameters
            const simulation = d3
                .forceSimulation(nodes)
                .force(
                    "link",
                    d3
                        .forceLink(links)
                        .id(d => d.id)
                        .distance(linkDistance)
                )
                .force("charge", d3.forceManyBody().strength(chargeStrength))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force(
                    "collision",
                    d3.forceCollide().radius(d => d.radius + 2)
                );

            // Create links
            const link = svg
                .append("g")
                .attr("stroke", "#999")
                .attr("stroke-opacity", 0.3)
                .selectAll("line")
                .data(links)
                .join("line")
                .attr("stroke-width", 1) // Thickness based on H4 value
                .attr("stroke", "#999") // Default gray color
                .attr("data-h4", d => d.h4); // Store H4 value for hover effects

            // Create nodes
            const node = svg
                .append("g")
                .selectAll("circle")
                .data(nodes)
                .join("circle")
                .attr("r", d => d.radius) // Use calculated radius
                .attr("fill", d => color(d.data_type))
                .attr("stroke", "#fff")
                .attr("stroke-width", isLargeGraph ? 1 : 2)
                .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended))
                .on("mouseover", function (event, d) {
                    d3.select(this)
                        .attr("stroke", "#000")
                        .attr("stroke-width", isLargeGraph ? 2 : 3);

                    // Highlight connected links and bring them to front
                    link.attr("stroke-opacity", l => {
                        const isConnected = l.source.id === d.id || l.target.id === d.id;
                        return isConnected ? 0.8 : isLargeGraph ? 0.01 : 0.05;
                    }).attr("stroke", l => {
                        const isConnected = l.source.id === d.id || l.target.id === d.id;
                        if (!isConnected) return "#999";

                        const h4 = l.h4;
                        return h4 > 0.8 ? "#2E8B57" : "#FF6B6B";
                    });

                    const tooltipContent = `
                        <strong>${d.name}</strong><br/>
                        Data Type: ${d.data_type}<br/>
                        P-value: ${d.min_p.toExponential(2)}<br/>
                        ${d.association ? `Beta: ${d.association.beta.toExponential(2)}` : ""}
                    `;
                    graphTransformations.getTooltip(tooltipContent, event);
                    const snpGraphStore = Alpine.store("snpGraphStore");
                    snpGraphStore.highlightedStudy = {
                        colocGroupId: d.coloc_group_id,
                        studyExtractionId: d.id,
                    };
                })
                .on("mouseout", function () {
                    d3.select(this)
                        .attr("stroke", "#fff")
                        .attr("stroke-width", isLargeGraph ? 1 : 2);

                    // Reset all links to default gray
                    link.attr("stroke-opacity", 0.3)
                        .attr("stroke", "#999")
                        .style("stroke-width", d => Math.sqrt(d.h4 * 5)); // Reset to original thickness

                    d3.selectAll(".tooltip").remove();

                    // Clear the highlighted study from the store
                    const snpGraphStore = Alpine.store("snpGraphStore");
                    snpGraphStore.highlightedStudy = null;
                });

            let tickCount = 0;
            simulation.on("tick", () => {
                link.attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                node.attr("cx", d => d.x).attr("cy", d => d.y);

                // Stop simulation after 100 ticks, or immediately if large graph
                tickCount++;
                if (tickCount >= 1 && isLargeGraph) {
                    simulation.stop();
                }
            });

            // Drag functions
            function dragstarted(event, d) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }

            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }

            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }

            // Add legend
            const legend = svg.append("g").attr("class", "legend").attr("transform", `translate(20, 20)`);

            const dataTypes = Array.from(new Set(nodes.map(d => d.data_type)));
            dataTypes.forEach((type, i) => {
                const legendItem = legend.append("g").attr("transform", `translate(0, ${i * 20})`);

                legendItem
                    .append("circle")
                    .attr("r", isLargeGraph ? 4 : 6)
                    .attr("fill", color(type));

                legendItem.append("text").attr("x", 15).attr("y", 4).attr("font-size", "12px").text(type);
            });

            // Add link legend
            const linkLegend = legend.append("g").attr("transform", `translate(0, ${dataTypes.length * 20 + 10})`);

            linkLegend.append("text").attr("font-size", "12px").attr("font-weight", "bold").text("Link Strength (H4):");

            const linkTypes = [
                { h4: 0.8, color: "#2E8B57", label: "Strong (H4 > 0.8)" },
                { h4: 0.5, color: "#FF6B6B", label: "Weak (H4 > 0.5)" },
            ];

            linkTypes.forEach((linkType, i) => {
                const linkLegendItem = linkLegend.append("g").attr("transform", `translate(0, ${(i + 1) * 15})`);

                linkLegendItem
                    .append("line")
                    .attr("x1", 0)
                    .attr("x2", 20)
                    .attr("y1", 0)
                    .attr("y2", 0)
                    .attr("stroke", linkType.color)
                    .attr("stroke-width", 3);

                linkLegendItem.append("text").attr("x", 25).attr("y", 4).attr("font-size", "10px").text(linkType.label);
            });
        },

        getForestPlot() {
            if (!this.data || !this.filteredData.colocs) return;

            const plotContainer = d3.select("#forest-plot");
            plotContainer.selectAll("*").remove();

            const margin = { top: 45, right: 20, bottom: 40, left: 10 };
            let width = plotContainer.node().getBoundingClientRect().width;
            const height = this.filteredData.colocs.length * 27;

            const svg = plotContainer
                .append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);

            // Use all data points for y-axis scale, but filter for valid data when drawing
            const allData = this.filteredData.colocs;
            const validData = allData.filter(
                d =>
                    d.association &&
                    d.association.beta !== null &&
                    d.association.beta !== 0 &&
                    d.association.se !== null &&
                    d.association.se !== 0
            );

            // Calculate max beta from valid data only
            const maxAbsBeta = validData.length > 0 ? d3.max(validData, d => Math.abs(d.association.beta)) : 1;
            const xRange = [-maxAbsBeta * 1.5, maxAbsBeta * 1.5];

            const x = d3.scaleLinear().domain(xRange).range([0, width]);

            // Use all data points for y-axis scale to maintain spacing
            const y = d3
                .scaleBand()
                .domain(allData.map(d => d.study_extraction_id))
                .range([0, height])
                .padding(0);

            svg.append("g")
                .attr("transform", `translate(0,${height})`)
                .call(d3.axisBottom(x))
                .selectAll("text")
                .style("font-size", "10px")
                .attr("transform", "rotate(-65) translate(-15,-10)");

            svg.append("g").call(d3.axisLeft(y).tickSize(0).tickFormat("")).selectAll(".domain").attr("stroke", "#ddd");

            svg.append("line")
                .attr("x1", x(0))
                .attr("y1", 0)
                .attr("x2", x(0))
                .attr("y2", height)
                .attr("stroke", "#000")
                .attr("stroke-width", 1);

            allData.forEach(d => {
                const yPos = y(d.study_extraction_id) + y.bandwidth() / 2;

                const hasValidData =
                    d.association &&
                    d.association.beta !== null &&
                    d.association.beta !== 0 &&
                    d.association.se !== null &&
                    d.association.se !== 0;

                if (hasValidData) {
                    const beta = d.association.beta;
                    const se = d.association.se;

                    const group = svg.append("g");

                    group
                        .append("line")
                        .attr("x1", x(beta - 1.96 * se))
                        .attr("y1", yPos)
                        .attr("x2", x(beta + 1.96 * se))
                        .attr("y2", yPos)
                        .attr("stroke", beta > 0 ? "#afe1af" : "#ee4b2b")
                        .attr("stroke-width", 2);

                    group
                        .append("circle")
                        .attr("cx", x(beta))
                        .attr("cy", yPos)
                        .attr("r", 4)
                        .attr("fill", beta > 0 ? "#afe1af" : "#ee4b2b");

                    group
                        .append("title")
                        .text(`Trait: ${d.trait_name}\nBeta: ${beta.toExponential(2)}\nSE: ${se.toExponential(2)}`);
                }
            });

            svg.append("text")
                .attr("transform", `translate(${width / 2}, ${height + margin.bottom})`)
                .style("text-anchor", "middle")
                .style("font-size", "12px")
                .text("Effect Size (Beta)");
        },
    };
}
