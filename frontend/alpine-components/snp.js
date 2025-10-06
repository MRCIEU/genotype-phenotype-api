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
        selectedRowId: null,
        highlightLock: false,
        init() {
            this.$watch("$store.snpGraphStore.highlightedStudy", newValue => {
                if (newValue) {
                    this.updateGraphHighlightFromStore(newValue);
                } else {
                    this.clearGraphHighlightFromStore();
                }
            });

            // Clear highlight lock and selection when clicking anywhere outside nodes
            document.addEventListener("click", () => {
                const snpGraphStore = Alpine.store("snpGraphStore");
                this.highlightLock = false;
                snpGraphStore.highlightedStudy = null;
                d3.selectAll(".tooltip").remove();
            });
        },

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

        setHighlightedStudy(item) {
            const snpGraphStore = Alpine.store("snpGraphStore");
            const newHighlightedStudy = {
                colocGroupId: item.coloc_group_id,
                studyExtractionId: item.study_extraction_id,
            };
            if (
                !snpGraphStore.highlightedStudy ||
                snpGraphStore.highlightedStudy.studyExtractionId !== newHighlightedStudy.studyExtractionId
            ) {
                snpGraphStore.highlightedStudy = newHighlightedStudy;
            }
            this.selectedRowId = item.study_extraction_id;
        },

        updateGraphHighlightFromStore(highlightedStudy) {
            if (this.updateGraphHighlight) {
                this.updateGraphHighlight(highlightedStudy);
            }
        },

        clearGraphHighlightFromStore() {
            if (this.clearGraphHighlight) {
                this.clearGraphHighlight();
            }
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

            const self = this;
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
            const maxNodeRadius = isLargeGraph ? 6 : 15;
            const linkDistance = isLargeGraph ? 30 : 50;
            const chargeStrength = isLargeGraph ? -100 : -300;

            nodes.forEach(node => {
                const pValueRadius = Math.max(baseNodeRadius, Math.min(maxNodeRadius, -Math.log10(node.min_p) * 1.5));
                node.radius = pValueRadius;
            });

            const centerStrength = isLargeGraph ? 0.5 : 0.2;
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
                    d3.forceCollide().radius(d => d.radius + 5)
                )
                .force("x", d3.forceX(width / 2).strength(centerStrength)) // Stronger centering force
                .force("y", d3.forceY(height / 2).strength(centerStrength)); // Stronger centering force

            // Create links
            const link = svg
                .append("g")
                .attr("stroke", "#999")
                .selectAll("line")
                .data(links)
                .join("line")
                .attr("stroke-width", 2)
                .attr("stroke", "#999")
                .attr("stroke-opacity", d => (d.h4 >= 0.8 ? 0.3 : 0))
                .attr("data-h4", d => d.h4);

            // Create nodes
            const node = svg
                .append("g")
                .selectAll("circle")
                .data(nodes)
                .join("circle")
                .attr("r", d => d.radius)
                .attr("fill", d => color(d.data_type))
                .attr("stroke", "#fff")
                .attr("stroke-width", isLargeGraph ? 1 : 2)
                .attr("data-id", d => d.id)
                .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended))
                .on("mouseover", function (event, d) {
                    if (self.highlightLock) return;
                    d3.select(this)
                        .attr("cursor", "pointer")
                        .attr("stroke", "#000")
                        .attr("stroke-width", isLargeGraph ? 2 : 3);

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

                    self.setHighlightedStudy({
                        coloc_group_id: d.coloc_group_id,
                        study_extraction_id: d.id,
                    });
                })
                .on("mouseout", function () {
                    if (self.highlightLock) return;
                    d3.select(this)
                        .attr("cursor", "default")
                        .attr("stroke", "#fff")
                        .attr("stroke-width", isLargeGraph ? 1 : 2);

                    link.attr("stroke-opacity", l => (l.h4 >= 0.8 ? 0.3 : 0))
                        .attr("stroke", "#999")
                        .style("stroke-width", 2);

                    d3.selectAll(".tooltip").remove();

                    const snpGraphStore = Alpine.store("snpGraphStore");
                    snpGraphStore.highlightedStudy = null;
                })
                .on("click", function (event, d) {
                    event.stopPropagation();
                    const snpGraphStore = Alpine.store("snpGraphStore");
                    if (d.id !== self.selectedRowId && self.highlightLock) {
                        self.highlightLock = false;
                        snpGraphStore.highlightedStudy = null;
                        self.selectedRowId = null;
                        return;
                    }
                    self.highlightLock = true;
                    const newHighlightedStudy = {
                        colocGroupId: d.coloc_group_id,
                        studyExtractionId: d.id,
                    };
                    if (
                        !snpGraphStore.highlightedStudy ||
                        snpGraphStore.highlightedStudy.studyExtractionId !== newHighlightedStudy.studyExtractionId
                    ) {
                        snpGraphStore.highlightedStudy = newHighlightedStudy;
                    }
                });

            let tickCount = 0;
            simulation.on("tick", () => {
                link.attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                node.attr("cx", d => d.x).attr("cy", d => d.y);

                tickCount++;
                const currentAlpha = simulation.alpha();

                if (isLargeGraph && tickCount >= 10) {
                    simulation.stop();
                } else if (!isLargeGraph && (currentAlpha < 0.01 || tickCount >= 300)) {
                    simulation.stop();
                }
            });

            simulation.on("end", () => {
                const visited = new Set();
                const components = [];

                const findComponent = startNode => {
                    const component = [];
                    const queue = [startNode];
                    visited.add(startNode.id);

                    while (queue.length > 0) {
                        const node = queue.shift();
                        component.push(node);

                        links.forEach(link => {
                            if (link.source.id === node.id && !visited.has(link.target.id)) {
                                visited.add(link.target.id);
                                queue.push(nodes.find(n => n.id === link.target.id));
                            } else if (link.target.id === node.id && !visited.has(link.source.id)) {
                                visited.add(link.source.id);
                                queue.push(nodes.find(n => n.id === link.source.id));
                            }
                        });
                    }
                    return component;
                };

                nodes.forEach(node => {
                    if (!visited.has(node.id)) {
                        components.push(findComponent(node));
                    }
                });

                const margin = 80;
                const maxComponentsPerRow = Math.ceil(Math.sqrt(components.length));
                const componentWidth = (width - 2 * margin) / maxComponentsPerRow;
                const componentHeight = (height - 2 * margin) / Math.ceil(components.length / maxComponentsPerRow);

                components.forEach((component, componentIndex) => {
                    const row = Math.floor(componentIndex / maxComponentsPerRow);
                    const col = componentIndex % maxComponentsPerRow;

                    const targetCenterX = margin + col * componentWidth + componentWidth / 2;
                    const targetCenterY = margin + row * componentHeight + componentHeight / 2;

                    const xBounds = d3.extent(component, d => d.x);
                    const yBounds = d3.extent(component, d => d.y);
                    const currentCenterX = (xBounds[0] + xBounds[1]) / 2;
                    const currentCenterY = (yBounds[0] + yBounds[1]) / 2;

                    // Calculate scale to fit component in its allocated space
                    const xRange = xBounds[1] - xBounds[0];
                    const yRange = yBounds[1] - yBounds[0];
                    const maxRange = Math.max(xRange, yRange, 1);
                    const scale = Math.min((componentWidth * 0.8) / maxRange, (componentHeight * 0.8) / maxRange, 1);

                    component.forEach(node => {
                        const offsetX = (node.x - currentCenterX) * scale;
                        const offsetY = (node.y - currentCenterY) * scale;
                        node.x = targetCenterX + offsetX;
                        node.y = targetCenterY + offsetY;
                    });
                });

                link.attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                node.attr("cx", d => d.x).attr("cy", d => d.y);
            });

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

            const linkLegend = legend.append("g").attr("transform", `translate(0, ${dataTypes.length * 20 + 10})`);

            linkLegend.append("text").attr("font-size", "12px").attr("font-weight", "bold").text("Link Strength (H4):");

            const linkTypes = [
                { h4: 0.8, color: "#2E8B57", label: "Strong (H4 > 0.8)" },
                { h4: 0.5, color: "#FF6B6B", label: "Weak (0.5 < H4 < 0.8)" },
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
                    .attr("stroke-width", 2);

                linkLegendItem.append("text").attr("x", 25).attr("y", 4).attr("font-size", "10px").text(linkType.label);
            });

            this.updateGraphHighlight = highlightedStudy => {
                const nodeElement = d3.select(
                    `#graph-cluster-diagram circle[data-id="${highlightedStudy.studyExtractionId}"]`
                );
                if (nodeElement.empty()) return;

                nodeElement.attr("stroke", "#000").attr("stroke-width", 3);

                link.attr("stroke-opacity", l => {
                    const isConnected =
                        l.source.id === highlightedStudy.studyExtractionId ||
                        l.target.id === highlightedStudy.studyExtractionId;
                    return isConnected ? 0.8 : 0.01;
                }).attr("stroke", l => {
                    const isConnected =
                        l.source.id === highlightedStudy.studyExtractionId ||
                        l.target.id === highlightedStudy.studyExtractionId;
                    if (!isConnected) return "#999";

                    const h4 = l.h4;
                    return h4 > 0.8 ? "#2E8B57" : "#FF6B6B";
                });
            };

            this.clearGraphHighlight = () => {
                node.attr("stroke", "#fff").attr("stroke-width", 2);

                link.attr("stroke-opacity", l => (l.h4 >= 0.8 ? 0.3 : 0))
                    .attr("stroke", "#999")
                    .style("stroke-width", 2);
            };
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

            const allData = this.filteredData.colocs;
            const validData = allData.filter(
                d =>
                    d.association &&
                    d.association.beta !== null &&
                    d.association.beta !== 0 &&
                    d.association.se !== null &&
                    d.association.se !== 0
            );

            const maxAbsBeta = validData.length > 0 ? d3.max(validData, d => Math.abs(d.association.beta)) : 1;
            const xRange = [-maxAbsBeta * 1.5, maxAbsBeta * 1.5];

            const x = d3.scaleLinear().domain(xRange).range([0, width]);

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
                .attr("stroke-width", 2);

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
