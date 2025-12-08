import Alpine from "alpinejs";
import * as d3 from "d3";

import constants from "./constants.js";
import downloads from "./downloads.js";
import graphTransformations from "./graphTransformations.js";

export default function snp() {
    return {
        data: null,
        filteredData: {
            colocs: [],
            colocPairs: [],
            rare: [],
            studies: [],
        },
        errorMessage: null,
        selectedRowId: null,
        highlightLock: false,

        init() {
            this.$watch("$store.snpGraphStore.highlightedStudy", newValue => {
                // Update footer text based on store highlight
                const footerText = d3.select("#graph-footer-text");
                if (newValue) {
                    this.updateGraphHighlightFromStore(newValue);
                    const nodeData =
                        this.filteredData.coloc_groups?.find(
                            d => d.study_extraction_id === newValue.studyExtractionId
                        ) || this.data.coloc_groups?.find(d => d.study_extraction_id === newValue.studyExtractionId);
                    if (nodeData) {
                        footerText.text(`${nodeData.trait_name} | p=${nodeData.min_p.toExponential(2)}`);
                    }
                } else {
                    this.clearGraphHighlightFromStore();
                    footerText.text("");
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
            return this.data ? this.filteredData.colocs || [] : [];
        },

        setHighlightedStudy(item) {
            this.clearGraphHighlightFromStore();
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

            // Additional filtering: Remove colocs that don't have strong coloc pairs (h4 > 0.8) with other studies
            const strongColocPairs = this.filteredData.colocPairs.filter(pair => pair.h4 > 0.8);
            const studyIdsWithStrongColoc = new Set();

            // Collect all study extraction IDs that have strong coloc pairs
            strongColocPairs.forEach(pair => {
                studyIdsWithStrongColoc.add(pair.study_extraction_a_id);
                studyIdsWithStrongColoc.add(pair.study_extraction_b_id);
            });

            // Filter out colocs that don't have strong coloc pairs with other studies
            this.filteredData.colocs = this.filteredData.colocs.filter(coloc =>
                studyIdsWithStrongColoc.has(coloc.study_extraction_id)
            );

            // Re-filter coloc pairs to only include those between remaining colocs
            const remainingStudyIds = new Set(this.filteredData.colocs.map(coloc => coloc.study_extraction_id));
            this.filteredData.colocPairs = this.filteredData.colocPairs.filter(colocPair => {
                return (
                    remainingStudyIds.has(colocPair.study_extraction_a_id) &&
                    remainingStudyIds.has(colocPair.study_extraction_b_id)
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
            if (!this.data) return;

            const chartElement = document.getElementById("graph-cluster-diagram");
            chartElement.innerHTML = "";

            const chartContainer = d3.select("#graph-cluster-diagram");
            const width = chartContainer.node().getBoundingClientRect().width - 50;
            const height = 500;
            const footerHeight = 40; // Fixed height for footer to prevent layout shift

            const self = this;
            const textColor = graphTransformations.graphColor();

            // Set container to have fixed height to prevent layout shifts
            chartContainer.style("height", height + footerHeight + "px").style("position", "relative");

            // Create canvas element with high-DPI support
            const canvas = chartContainer.append("canvas").style("display", "block").node();

            // Get device pixel ratio for crisp rendering on high-DPI displays
            const dpr = window.devicePixelRatio || 1;

            // Set the actual canvas size in memory (scaled up for high-DPI)
            canvas.width = width * dpr;
            canvas.height = height * dpr;

            // Scale the canvas back down using CSS
            canvas.style.width = width + "px";
            canvas.style.height = height + "px";

            const ctx = canvas.getContext("2d");

            // Scale the drawing context so everything draws at the correct size
            ctx.scale(dpr, dpr);

            // Create footer text element separately with fixed min-height to prevent layout shifts
            const footerText = chartContainer
                .append("div")
                .attr("id", "graph-footer-text")
                .style("text-align", "center")
                .style("font-weight", "bold")
                .style("font-size", "18px")
                .style("min-height", footerHeight + "px")
                .style("padding-top", "10px")
                .style("box-sizing", "border-box")
                .style("color", textColor)
                .text("");

            // If too many studies, show message and exit early
            const numStudies = (this.filteredData.colocs || []).length;
            if (numStudies > 1000) {
                // Increased limit since Canvas is more performant
                ctx.fillStyle = textColor;
                ctx.font = "16px Arial";
                ctx.textAlign = "center";
                ctx.fillText(
                    "The cluster is too big to render in a web browser. Please refine filters to reduce the number of results.",
                    width / 2,
                    height / 2
                );
                return;
            }

            if (!this.filteredData.colocPairs || this.filteredData.colocPairs.length === 0) return;

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
            const numColocGroups = [...new Set(this.filteredData.colocs.map(coloc => coloc.coloc_group_id))].length;

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

            // Store references for Canvas rendering
            let highlightedNode = null;
            let isDragging = false;
            let dragNode = null;
            let mousePos = { x: 0, y: 0 };

            // Function to render the graph on canvas
            const renderGraph = () => {
                // Clear canvas
                ctx.clearRect(0, 0, width, height);

                // Draw links
                links.forEach(link => {
                    const sourceNode = nodes.find(n => n.id === link.source.id);
                    const targetNode = nodes.find(n => n.id === link.target.id);

                    if (!sourceNode || !targetNode) return;

                    const isConnected =
                        highlightedNode &&
                        (link.source.id === highlightedNode.id || link.target.id === highlightedNode.id);

                    let strokeOpacity = 0;
                    let strokeColor = "#999";

                    if (isConnected) {
                        strokeOpacity = 0.8;
                        strokeColor = link.h4 > 0.8 ? "#2563EB" : "#EA580C";
                    } else if (link.h4 >= 0.8) {
                        strokeOpacity = 0.3;
                    }

                    if (strokeOpacity > 0) {
                        ctx.beginPath();
                        ctx.moveTo(sourceNode.x, sourceNode.y);
                        ctx.lineTo(targetNode.x, targetNode.y);
                        ctx.strokeStyle = strokeColor;
                        ctx.lineWidth = isLargeGraph ? 1 : 2;
                        ctx.globalAlpha = strokeOpacity;
                        ctx.stroke();
                        ctx.globalAlpha = 1;
                    }
                });
                nodes.forEach(node => {
                    const isHighlighted = highlightedNode && node.id === highlightedNode.id;

                    // Draw node circle
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
                    ctx.fillStyle = color(node.data_type);
                    ctx.fill();

                    // Draw node border
                    ctx.strokeStyle = isHighlighted ? textColor : "#fff";
                    ctx.lineWidth = isHighlighted ? 3 : isLargeGraph ? 1 : 2;
                    ctx.stroke();
                });

                // Draw legend after main graph elements
                drawLegend();
            };

            // Mouse interaction handling
            const getMousePos = e => {
                const rect = canvas.getBoundingClientRect();
                return {
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top,
                };
            };

            const getNodeAt = (x, y) => {
                for (let i = nodes.length - 1; i >= 0; i--) {
                    const node = nodes[i];
                    const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2);
                    if (distance <= node.radius + 5) {
                        // Add some padding for easier clicking
                        return node;
                    }
                }
                return null;
            };

            // Mouse event handlers
            canvas.addEventListener("mousemove", e => {
                mousePos = getMousePos(e);
                const node = getNodeAt(mousePos.x, mousePos.y);

                if (isDragging && dragNode) {
                    dragNode.fx = mousePos.x;
                    dragNode.fy = mousePos.y;
                    simulation.alphaTarget(0.3).restart();
                } else if (node && !self.highlightLock) {
                    canvas.style.cursor = "pointer";
                    if (highlightedNode !== node) {
                        highlightedNode = node;
                        renderGraph();

                        // Update footer text
                        const footer = `${node.name} | p=${node.min_p.toExponential(2)}`;
                        footerText.text(footer);

                        self.setHighlightedStudy({
                            coloc_group_id: node.coloc_group_id,
                            study_extraction_id: node.id,
                        });
                    }
                } else if (!node && !self.highlightLock) {
                    canvas.style.cursor = "default";
                    if (highlightedNode) {
                        highlightedNode = null;
                        renderGraph();
                        footerText.text("");

                        const snpGraphStore = Alpine.store("snpGraphStore");
                        snpGraphStore.highlightedStudy = null;
                    }
                }
            });

            canvas.addEventListener("mousedown", _ => {
                const node = getNodeAt(mousePos.x, mousePos.y);
                if (node) {
                    isDragging = true;
                    dragNode = node;
                    node.fx = node.x;
                    node.fy = node.y;
                    simulation.alphaTarget(0.3).restart();
                }
            });

            canvas.addEventListener("mouseup", _ => {
                if (isDragging && dragNode) {
                    isDragging = false;
                    dragNode.fx = null;
                    dragNode.fy = null;
                    dragNode = null;
                    simulation.alphaTarget(0);
                }
            });

            canvas.addEventListener("click", e => {
                e.stopPropagation();
                const node = getNodeAt(mousePos.x, mousePos.y);
                if (node) {
                    const snpGraphStore = Alpine.store("snpGraphStore");
                    if (node.id !== self.selectedRowId && self.highlightLock) {
                        self.highlightLock = false;
                        snpGraphStore.highlightedStudy = null;
                        self.selectedRowId = null;
                        highlightedNode = null;
                        renderGraph();
                        return;
                    }
                    self.highlightLock = true;
                    const newHighlightedStudy = {
                        colocGroupId: node.coloc_group_id,
                        studyExtractionId: node.id,
                    };
                    if (
                        !snpGraphStore.highlightedStudy ||
                        snpGraphStore.highlightedStudy.studyExtractionId !== newHighlightedStudy.studyExtractionId
                    ) {
                        snpGraphStore.highlightedStudy = newHighlightedStudy;
                    }
                    // Ensure footer reflects clicked node
                    const footer = `${node.name} | ${node.data_type} | p=${node.min_p.toExponential(2)}`;
                    footerText.text(footer);
                } else {
                    // Clicked on empty space - de-highlight
                    const snpGraphStore = Alpine.store("snpGraphStore");
                    self.highlightLock = false;
                    snpGraphStore.highlightedStudy = null;
                    self.selectedRowId = null;
                    highlightedNode = null;
                    renderGraph();
                    footerText.text("");
                }
            });

            let tickCount = 0;
            simulation.on("tick", () => {
                // Re-render the entire graph on each tick
                renderGraph();

                tickCount++;
                const currentAlpha = simulation.alpha();

                if (isLargeGraph && numColocGroups > 1 && tickCount >= 30) {
                    simulation.stop();
                } else if (isLargeGraph && numColocGroups === 1 && tickCount >= 1) {
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

                // Final render after component layout
                renderGraph();
            });

            // Draw legend on canvas
            const drawLegend = () => {
                const legendX = 20;
                const legendY = 20;
                const dataTypes = Array.from(new Set(nodes.map(d => d.data_type)));

                // Draw "Trait Type" header
                ctx.fillStyle = textColor;
                ctx.font = "bold 12px Arial";
                ctx.fillText("Trait Type:", legendX, legendY);

                // Draw node type legend
                dataTypes.forEach((type, i) => {
                    const y = legendY + (i + 1) * 20;

                    // Draw circle
                    ctx.beginPath();
                    ctx.arc(legendX + (isLargeGraph ? 4 : 6), y, isLargeGraph ? 4 : 6, 0, 2 * Math.PI);
                    ctx.fillStyle = color(type);
                    ctx.fill();
                    ctx.strokeStyle = "#fff";
                    ctx.lineWidth = 1;
                    ctx.stroke();

                    // Draw text
                    ctx.fillStyle = textColor;
                    ctx.font = "12px Arial";
                    ctx.textAlign = "left";
                    ctx.fillText(type, legendX + 15, y + 4);
                });

                // Draw link legend
                const linkLegendY = legendY + (dataTypes.length + 1) * 20 + 10;
                ctx.fillStyle = textColor;
                ctx.font = "bold 12px Arial";
                ctx.fillText("Link Strength (H4):", legendX, linkLegendY);

                const linkTypes = [
                    { h4: 0.8, color: "#2563EB", label: "Strong (H4 > 0.8)" },
                    { h4: 0.5, color: "#EA580C", label: "Weak (0.5 < H4 < 0.8)" },
                ];

                linkTypes.forEach((linkType, i) => {
                    const y = linkLegendY + (i + 1) * 15;

                    // Draw line
                    ctx.beginPath();
                    ctx.moveTo(legendX, y);
                    ctx.lineTo(legendX + 20, y);
                    ctx.strokeStyle = linkType.color;
                    ctx.lineWidth = 2;
                    ctx.stroke();

                    // Draw text
                    ctx.fillStyle = textColor;
                    ctx.font = "10px Arial";
                    ctx.fillText(linkType.label, legendX + 25, y + 4);
                });

                // Display connectedness for each coloc group using existing data
                const colocGroups = [...new Set(nodes.map(n => n.coloc_group_id).filter(id => id !== null))];
                if (colocGroups.length > 0) {
                    const connectednessY = linkLegendY + linkTypes.length * 15 + 30; // Added extra spacing for line break

                    ctx.fillStyle = textColor;
                    ctx.font = "bold 12px Arial";
                    ctx.fillText("Group Connectedness:", legendX, connectednessY);
                    const onlyOneColocGroup = colocGroups.length === 1;

                    colocGroups.forEach((groupId, i) => {
                        // Find the first node in this group to get the connectedness value
                        const groupNode = nodes.find(n => n.coloc_group_id === groupId);
                        const connectednessValue = groupNode
                            ? self.data.coloc_groups.find(cg => cg.coloc_group_id === groupId)?.h4_connectedness || 0
                            : 0;
                        const connectednessPercentage = Math.round(connectednessValue * 100);

                        let strengthText = "Weak";
                        for (const threshold in constants.clusterConnectednessThresholds) {
                            if (connectednessPercentage >= threshold)
                                strengthText = constants.clusterConnectednessThresholds[threshold];
                        }

                        const y = connectednessY + (i + 1) * 15;

                        // Draw group indicator
                        ctx.fillStyle = textColor;
                        ctx.font = "11px Arial";
                        const connectednessText = onlyOneColocGroup
                            ? `Connectedness: ${connectednessPercentage}% (${strengthText})`
                            : `Group ${groupId}: ${connectednessPercentage}% connected (${strengthText})`;
                        ctx.fillText(connectednessText, legendX, y);
                    });
                }
            };

            this.updateGraphHighlight = highlightedStudy => {
                const node = nodes.find(n => n.id === highlightedStudy.studyExtractionId);
                if (node) {
                    highlightedNode = node;
                    renderGraph();
                }
            };

            this.clearGraphHighlight = () => {
                highlightedNode = null;
                renderGraph();
            };
        },

        getForestPlot() {
            if (!this.data || !this.filteredData.colocs) return;

            const plotContainer = d3.select("#forest-plot");
            plotContainer.selectAll("*").remove();

            const margin = { top: 45, right: 20, bottom: 40, left: 10 };
            let width = plotContainer.node().getBoundingClientRect().width;
            const height = this.filteredData.colocs.length * 27;
            const textColor = graphTransformations.graphColor();

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

            const xAxisGroup = svg.append("g").attr("transform", `translate(0,${height})`).call(d3.axisBottom(x));
            xAxisGroup
                .selectAll("text")
                .style("font-size", "10px")
                .style("fill", textColor)
                .attr("transform", "rotate(-65) translate(-15,-10)");
            xAxisGroup.selectAll("line, path").style("stroke", textColor);

            svg.append("g")
                .call(d3.axisLeft(y).tickSize(0).tickFormat(""))
                .selectAll(".domain")
                .attr("stroke", textColor);

            svg.append("line")
                .attr("x1", x(0))
                .attr("y1", 0)
                .attr("x2", x(0))
                .attr("y2", height)
                .attr("stroke", textColor)
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
                .style("fill", textColor)
                .text("Effect Size (Beta)");
        },
    };
}
