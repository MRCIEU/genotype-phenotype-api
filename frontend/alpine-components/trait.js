import JSZip from "jszip";
import * as d3 from "d3";
import { stringify } from "flatted";

import graphTransformations from "./graphTransformations.js";
import constants from "./constants.js";
import downloads from "./downloads.js";

export default function trait() {
    return {
        constants: constants,
        userUpload: false,
        data: null,
        filteredData: {
            coloc_groups: null,
            groupedColocs: null,
            rare: null,
            groupedRare: null,
        },
        svgs: {
            metadata: null,
            full: null,
            chromosomes: {},
        },
        showTables: {
            coloc: true,
            rare: true,
        },
        displayFilters: {
            view: "full",
            chr: null,
            candidateSnp: null,
            traitName: null,
        },
        traitSearch: {
            text: "",
            showDropDown: false,
            orderedTraits: null,
        },
        errorMessage: null,
        downloadClicked: false,

        async loadData() {
            let traitId = new URLSearchParams(location.search).get("id");
            let traitUrl = constants.apiUrl + "/traits/" + traitId;

            if (traitId && traitId.includes("-")) {
                this.userUpload = true;
                traitUrl = constants.apiUrl + "/gwas/" + traitId;
            }

            try {
                const response = await fetch(traitUrl);
                if (!response.ok) {
                    this.errorMessage = `Failed to load data: ${response.status} ${response.statusText}`;
                    return;
                }

                this.data = await response.json();
                await this.getSvgData(traitId);

                document.title = "GP Map: " + (this.userUpload ? this.data.trait.name : this.data.trait.trait_name);

                this.transformDataForGraphs();
            } catch (error) {
                console.error(error);
                this.errorMessage = `Failed to load data: ${error.status} ${error.statusText}`;
            }
        },

        transformDataForGraphs() {
            // Count frequency of each id in colocs and scale between 2 and 10
            const [scaledMinNumStudies, scaledMaxNumStudies] = [2, 10];
            const colocGroups = this.data.coloc_groups || [];
            const idFrequencies = colocGroups.reduce((acc, obj) => {
                if (obj.coloc_group_id) {
                    acc[obj.coloc_group_id] = (acc[obj.coloc_group_id] || 0) + 1;
                }
                return acc;
            }, {});

            // Get min and max frequencies
            const frequencies = Object.values(idFrequencies);
            const minNumStudies = frequencies.length > 0 ? Math.min(...frequencies) : 0;
            const maxNumStudies = frequencies.length > 0 ? Math.max(...frequencies) : 0;

            this.data.study_extractions = (this.data.study_extractions || []).map(se => {
                se.MbP = se.bp / 1000000;
                se.chrText = "CHR ".concat(se.chr);
                se.ignore = false;
                return se;
            });
            this.data.rare_results = (this.data.rare_results || []).map(r => {
                r.MbP = r.bp / 1000000;
                r.chrText = "CHR ".concat(r.chr);
                r.ignore = false;
                return r;
            });
            this.data.coloc_groups = (this.data.coloc_groups || []).map(c => {
                c.MbP = c.bp / 1000000;
                c.chrText = "CHR ".concat(c.chr);
                c.annotationColor =
                    constants.colors.palette[Math.floor(Math.random() * constants.colors.palette.length)];
                c.ignore = false;
                if (minNumStudies === maxNumStudies) {
                    c.scaledNumStudies = 4;
                } else {
                    c.scaledNumStudies =
                        ((idFrequencies[c.coloc_group_id] - minNumStudies) / (maxNumStudies - minNumStudies)) *
                            (scaledMaxNumStudies - scaledMinNumStudies) +
                        scaledMinNumStudies;
                }
                return c;
            });
            this.data.coloc_groups.sort((a, b) => a.chr > b.chr);
        },

        filterDataForGraphs() {
            if (!this.data) return;
            const graphOptions = Alpine.store("graphOptionStore");
            const selectedCategories = graphTransformations.selectedTraitCategories(graphOptions);

            this.filteredData.coloc_groups = (this.data.coloc_groups || []).filter(coloc => {
                if (this.userUpload) return true;
                let graphOptionFilters =
                    coloc.min_p <= graphOptions.pValue &&
                    (graphOptions.includeTrans ? true : coloc.cis_trans !== "trans") &&
                    (coloc.trait_id === this.data.trait.id ||
                        (graphOptions.traitType === "all"
                            ? true
                            : graphOptions.traitType === "molecular"
                              ? coloc.data_type !== "Phenotype"
                              : graphOptions.traitType === "phenotype"
                                ? coloc.data_type === "Phenotype"
                                : true));
                let displayFilters = this.displayFilters.chr !== null ? coloc.chr == this.displayFilters.chr : true;

                let categoryFilters = true;
                if (selectedCategories.size > 0) {
                    categoryFilters =
                        selectedCategories.has(coloc.trait_category) || coloc.trait_id === this.data.trait.id;
                }

                return graphOptionFilters && displayFilters && categoryFilters;
            });

            this.filteredData.rare = (this.data.rare_results || []).filter(rare => {
                const graphOptionFilters =
                    rare.min_p <= graphOptions.pValue &&
                    (graphOptions.includeTrans ? true : rare.cis_trans !== "trans") &&
                    (graphOptions.traitType === "all" || graphOptions.traitType === "phenotype");
                return graphOptionFilters;
            });

            this.filteredData.groupedColocs = graphTransformations.groupBySnp(
                this.filteredData.coloc_groups,
                "trait",
                this.data.trait.id,
                this.displayFilters,
                this.userUpload
            );
            this.filteredData.groupedRare = graphTransformations.groupBySnp(
                this.filteredData.rare,
                "trait",
                this.data.trait.id,
                this.displayFilters,
                this.userUpload
            );

            const allFilteredData = { ...this.filteredData.groupedColocs, ...this.filteredData.groupedRare };
            this.traitSearch.orderedTraits = graphTransformations.getOrderedTraits(allFilteredData);
        },

        async getSvgData(traitId) {
            if (this.userUpload) {
                this.svgs = {
                    metadata: null,
                    full: null,
                    chromosomes: {},
                };
                return;
            }
            if (constants.isLocal) {
                const colocGroups = this.data.coloc_groups || [];
                const minP = colocGroups.reduce((min, se) => Math.min(min, se.min_p), Infinity);
                traitId = minP < 1e-10 ? "gwas" : "short_gwas";
            }

            const metadataUrl = `${constants.assetBaseUrl}/traits/${traitId}_metadata.json`;
            const svgsUrl = `${constants.assetBaseUrl}/traits/${traitId}_svgs.zip`;

            const response = await fetch(metadataUrl);
            if (!response.ok) {
                this.errorMessage = `Failed to load data: ${response.status} ${response.statusText}`;
                return;
            }
            this.svgs.metadata = await response.json();

            const zipResponse = await fetch(svgsUrl);
            const zipBlob = await zipResponse.blob();
            const zip = await JSZip.loadAsync(zipBlob);

            for (const [filename, file] of Object.entries(zip.files)) {
                if (filename.endsWith(".svg")) {
                    const svgContent = await file.async("text");
                    if (filename.includes("chr")) {
                        // Extract chromosome number from filename
                        const chrNum = filename.match(/chr(\d+)\.svg/)[1];
                        this.svgs.chromosomes[`chr${chrNum}`] = svgContent;
                    } else {
                        // This is the full genome SVG
                        this.svgs.full = svgContent;
                    }
                }
            }
        },

        async downloadDataOnly() {
            await downloads.downloadDataToZip(this.data, this.data.trait.trait_name || this.data.trait.name);
            this.downloadClicked = true;
        },

        async downloadDataAndGWAS() {
            if (this.userUpload) {
                let traitId = new URLSearchParams(location.search).get("id");
                try {
                    await this.downloadDataOnly();
                    const response = await fetch(constants.apiUrl + "/gwas/" + traitId + "/summary-stats");
                    if (!response.ok) {
                        this.errorMessage = `Failed to get summary stats: ${response.status} ${response.statusText}`;
                        return;
                    }
                    const downloadUrl = await response.json();
                    if (downloadUrl) {
                        downloads.downloadFile(downloadUrl);
                    }
                } catch (error) {
                    console.error("Error downloading GWAS data:", error);
                    this.errorMessage = "Error initiating download. Please try again.";
                }
            }
        },

        get showResults() {
            if (this.userUpload) return this.data && this.data.trait.status === "completed";
            return true;
        },

        get getStudyToDisplay() {
            let text = "Trait: ";
            if (this.data === null) return text + "...";
            if (this.userUpload) {
                return "GWAS Upload: " + this.data.trait.name;
            }

            return text + this.data.trait.trait_name;
        },

        get getUploadStatus() {
            let text = "Status: ";
            if (this.data === null) return text + "...";
            return text + this.data.trait.status;
        },

        get getSampleSizes() {
            if (this.data === null) return "...";
            if (this.userUpload) {
                return {
                    common: this.data.trait.sample_size.toLocaleString(),
                    rare: null,
                };
            }
            return {
                common: this.data.trait.common_study.sample_size.toLocaleString(),
                rare: this.data.trait.rare_study ? this.data.trait.rare_study.sample_size.toLocaleString() : null,
            };
        },

        get getStudySourceLink() {
            if (this.data === null || this.userUpload || !this.data.trait.trait) return null;
            const traitForUrl = this.data.trait.trait.replace(/-/g, (match, offset) => {
                // Count dashes before current position
                const dashesBefore = (this.data.trait.trait.substring(0, offset).match(/-/g) || []).length;
                return dashesBefore >= 2 ? "_" : match;
            });
            return "https://opengwas.io/datasets/" + traitForUrl;
        },

        getTraitsToFilterBy() {
            if (this.traitSearch.orderedTraits === null) return [];
            return this.traitSearch.orderedTraits.filter(
                t => !this.traitSearch.text || t.toLowerCase().includes(this.traitSearch.text.toLowerCase())
            );
        },

        filterByTrait(trait) {
            if (trait !== null) {
                this.displayFilters.traitName = trait;
            }
        },

        removeDisplayFilters() {
            this.downloadClicked = false;
            this.displayFilters = {
                view: "full",
                chr: null,
                candidateSnp: null,
                traitName: null,
            };
            this.traitSearch.text = "";
        },

        get getDataForColocTable() {
            if (!this.filteredData.coloc_groups || this.filteredData.coloc_groups.length === 0) return [];

            // Keep chromosome filtering, but do not drop other SNPs when one is selected
            let tableData = this.filteredData.coloc_groups.filter(coloc => {
                if (this.displayFilters.chr !== null) return coloc.chr == this.displayFilters.chr;
                else return true;
            });

            tableData = graphTransformations.addColorForSNPs(tableData);
            let groupedData = graphTransformations.groupBySnp(
                tableData,
                "trait",
                this.data.trait.id,
                this.displayFilters,
                this.userUpload
            );

            // If a SNP is selected, reorder so that its group appears first
            if (this.displayFilters.candidateSnp) {
                const candidateSnpKey = this.displayFilters.candidateSnp;
                const selectedEntryValue = groupedData[candidateSnpKey];
                delete groupedData[candidateSnpKey];
                groupedData = { [candidateSnpKey]: selectedEntryValue, ...groupedData };
            }

            const truncatedData = Object.fromEntries(
                Object.entries(groupedData).slice(0, constants.maxSNPGroupsToDisplay)
            );
            return stringify(truncatedData);
        },

        get doRareResultsExist() {
            return this.data && this.data.trait.rare_study;
        },

        get getDataForRareTable() {
            if (!this.filteredData.rare || this.filteredData.rare.length === 0) return [];

            // Only filter by chromosome if specified, not by SNP (we'll reorder instead)
            let tableData = this.filteredData.rare.filter(rare => {
                if (this.displayFilters.chr !== null) return rare.chr == this.displayFilters.chr;
                else return true;
            });

            tableData = graphTransformations.addColorForSNPs(tableData);
            let groupedData = graphTransformations.groupBySnp(
                tableData,
                "trait",
                this.data.trait.id,
                this.displayFilters,
                this.userUpload
            );

            // If a SNP is selected, reorder so that its group appears first
            if (this.displayFilters.candidateSnp) {
                const candidateSnpKey = this.displayFilters.candidateSnp;
                const selectedEntryValue = groupedData[candidateSnpKey];
                delete groupedData[candidateSnpKey];
                groupedData = { [candidateSnpKey]: selectedEntryValue, ...groupedData };
            }

            const truncatedData = Object.fromEntries(
                Object.entries(groupedData).slice(0, constants.maxSNPGroupsToDisplay)
            );
            return stringify(truncatedData);
        },

        initTraitGraph() {
            this.filterDataForGraphs();
            if (this.userUpload) return;
            const chartContainer = document.getElementById("trait-chart");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () => this.getTraitGraph());
        },

        getTraitGraph() {
            if (!this.svgs.metadata) return;

            const chartContainer = document.getElementById("trait-chart");
            chartContainer.innerHTML = "";

            let self = this;
            const graphConstants = {
                margin: { top: 20, right: 20, bottom: 60, left: 80 },
                legend: { width: 450, height: 20 },
            };
            const textColor = graphTransformations.graphColor();

            // Get container dimensions
            const containerWidth = chartContainer.clientWidth;
            const aspectRatio = self.svgs.metadata.svg_height / self.svgs.metadata.svg_width;
            const width = containerWidth - graphConstants.margin.left - graphConstants.margin.right;
            const height = width * aspectRatio;

            // Shared variables for circle size calculations
            let circleData = [];
            let radiusInfo = {
                minGroupSize: 0,
                maxGroupSize: 0,
                minRadius: 0,
                maxRadius: 0,
            };

            if (self.filteredData.groupedColocs || self.filteredData.groupedRare) {
                const colocGroups = self.filteredData.groupedColocs
                    ? Object.values(self.filteredData.groupedColocs)
                    : [];
                const rareGroups = self.filteredData.groupedRare ? Object.values(self.filteredData.groupedRare) : [];
                const allGroups = colocGroups.concat(rareGroups);
                circleData = allGroups
                    .map(group => {
                        const traitId = self.data.trait.id;
                        // Check if this is a rare variant group (no coloc_group_id)
                        const isRareVariantGroup = group.some(entry => !entry.coloc_group_id);

                        // First try to find a study with matching trait_id
                        let study = group.find(s => s.trait_id === traitId);
                        // For rare variants, if no matching trait_id found, use the first study
                        // (groups are already filtered to be related to the current trait)
                        if (!study && isRareVariantGroup && group.length > 0) {
                            study = group[0];
                        }
                        if (!study) return null;
                        study._group = group;
                        return study;
                    })
                    .filter(Boolean);

                if (circleData.length > 0) {
                    const groupSizes = circleData.map(d => d._group.length);
                    radiusInfo.minGroupSize = Math.min(...groupSizes);
                    radiusInfo.maxGroupSize = Math.max(...groupSizes);
                    radiusInfo.minRadius = 3;
                    radiusInfo.maxRadius = Math.min(radiusInfo.maxGroupSize + 2, 20);
                }
            }

            // Create a container div to hold both Canvas and SVG
            const containerDiv = d3
                .select(chartContainer)
                .append("div")
                .style("position", "relative")
                .style("width", width + graphConstants.margin.left + graphConstants.margin.right + "px")
                .style("height", height + graphConstants.margin.top + graphConstants.margin.bottom + "px");

            // Create Canvas container
            const canvas = containerDiv
                .append("canvas")
                .attr("width", width + graphConstants.margin.left + graphConstants.margin.right)
                .attr("height", height + graphConstants.margin.top + graphConstants.margin.bottom)
                .style("display", "block")
                .style("position", "relative")
                .style("z-index", "2")
                .node();

            const ctx = canvas.getContext("2d");

            // Create SVG container for embedded SVG content (positioned behind Canvas)
            const svg = containerDiv
                .append("svg")
                .attr("width", width + graphConstants.margin.left + graphConstants.margin.right)
                .attr("height", height + graphConstants.margin.top + graphConstants.margin.bottom)
                .attr(
                    "viewBox",
                    `0 0 ${width + graphConstants.margin.left + graphConstants.margin.right} ${height + graphConstants.margin.top + graphConstants.margin.bottom}`
                )
                .style("position", "absolute")
                .style("top", "0")
                .style("left", "0")
                .style("z-index", "1")
                .style("pointer-events", "none"); // Make SVG non-interactive

            // Create separate interactive SVG layer for buttons (above canvas)
            const interactiveSvg = containerDiv
                .append("svg")
                .attr("width", width + graphConstants.margin.left + graphConstants.margin.right)
                .attr("height", height + graphConstants.margin.top + graphConstants.margin.bottom)
                .attr(
                    "viewBox",
                    `0 0 ${width + graphConstants.margin.left + graphConstants.margin.right} ${height + graphConstants.margin.top + graphConstants.margin.bottom}`
                )
                .style("position", "absolute")
                .style("top", "0")
                .style("left", "0")
                .style("z-index", "3")
                .style("pointer-events", "none"); // Only button will have pointer events

            // Create main plot group for SVG (for embedded content only)
            const plotGroup = svg
                .append("g")
                .attr("transform", `translate(${graphConstants.margin.left},${graphConstants.margin.top})`);

            // Create interactive plot group for buttons
            const interactivePlotGroup = interactiveSvg
                .append("g")
                .attr("transform", `translate(${graphConstants.margin.left},${graphConstants.margin.top})`)
                .style("pointer-events", "none"); // Group level is none, but button will have all

            // Create a foreignObject to properly embed the SVG
            const foreignObject = plotGroup
                .append("foreignObject")
                .attr("width", width)
                .attr("height", height)
                .attr("overflow", "hidden");

            // Add chromosome backgrounds for ALL chromosomes (behind canvas in main SVG)
            const chrBackgrounds = plotGroup
                .append("g")
                .attr("class", "chr-backgrounds")
                .style("pointer-events", "all");

            // Add chromosome labels (will be drawn on canvas)
            const chrLabels = plotGroup.append("g").attr("class", "chr-labels");

            const yScale = d3
                .scaleLinear()
                .domain([self.svgs.metadata.y_axis.min_lp, self.svgs.metadata.y_axis.max_lp])
                .range([height, 0]);

            // Add Y-axis to SVG (behind Canvas)
            const yAxis = d3
                .axisLeft(yScale)
                .ticks(10)
                .tickFormat(d => d);
            const yAxisGroup = plotGroup.append("g").call(yAxis);
            yAxisGroup
                .selectAll("text")
                .style("text-anchor", "end")
                .style("font-size", "12px")
                .style("fill", textColor);
            yAxisGroup.selectAll("line, path").style("stroke", textColor);
            plotGroup
                .append("text")
                .attr("transform", "rotate(-90)")
                .attr("x", -height / 2)
                .attr("y", -50)
                .style("text-anchor", "middle")
                .style("font-size", "14px")
                .style("fill", textColor)
                .text("-log10(p-value)");

            // Add reference lines to SVG (behind Canvas)
            const referenceLines = plotGroup.append("g").attr("class", "reference-lines");
            referenceLines
                .append("line")
                .attr("x1", 0)
                .attr("x2", width)
                .attr("y1", yScale(4))
                .attr("y2", yScale(4))
                .attr("stroke", textColor)
                .attr("opacity", 0.8)
                .attr("stroke-width", 0.6)
                .attr("stroke-dasharray", "5,5");

            referenceLines
                .append("line")
                .attr("x1", 0)
                .attr("x2", width)
                .attr("y1", yScale(7.3))
                .attr("y2", yScale(7.3))
                .attr("stroke", textColor)
                .attr("opacity", 0.8)
                .attr("stroke-width", 0.6);

            // Canvas rendering functions
            const renderCanvas = () => {
                // Clear canvas with transparent background
                ctx.clearRect(0, 0, canvas.width, canvas.height);
            };

            // Store circle data for Canvas rendering
            let canvasCircles = [];
            let highlightedCircle = null;
            let hoveredChromosome = null;
            let chromosomeRects = null;

            const renderLegend = () => {
                const legendY = graphConstants.margin.top - 10;
                const legendX = graphConstants.margin.left + width - graphConstants.legend.width;

                ctx.save();
                ctx.translate(legendX, legendY);

                // Draw legend border
                ctx.strokeStyle = "#bbb";
                ctx.lineWidth = 1;
                ctx.strokeRect(-10, -10, graphConstants.legend.width, graphConstants.legend.height);

                // Get text color from graphTransformations
                const textColor = graphTransformations.graphColor();

                // Common circle
                ctx.beginPath();
                ctx.arc(0, 2, 5, 0, 2 * Math.PI);
                ctx.fillStyle = constants.colors.dataTypes.common;
                ctx.fill();
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 1;
                ctx.stroke();

                ctx.fillStyle = textColor;
                ctx.font = "12px Arial";
                ctx.textAlign = "left";
                ctx.fillText("Common", 10, 6);

                // Rare circle
                ctx.beginPath();
                ctx.arc(70, 2, 5, 0, 2 * Math.PI);
                ctx.fillStyle = constants.colors.dataTypes.rare;
                ctx.fill();
                ctx.strokeStyle = "#fff";
                ctx.stroke();

                ctx.fillStyle = textColor;
                ctx.fillText("Rare", 80, 6);

                // Suggestive significance line
                ctx.beginPath();
                ctx.moveTo(115, 3);
                ctx.lineTo(135, 3);
                ctx.strokeStyle = "darkred";
                ctx.lineWidth = 0.8;
                ctx.setLineDash([5, 5]);
                ctx.stroke();
                ctx.setLineDash([]);

                ctx.fillStyle = textColor;
                ctx.fillText("Suggestive significance", 135, 6);

                // Genome-wide significance line
                ctx.beginPath();
                ctx.moveTo(270, 3);
                ctx.lineTo(290, 3);
                ctx.strokeStyle = "darkred";
                ctx.lineWidth = 0.8;
                ctx.stroke();

                ctx.fillStyle = textColor;
                ctx.fillText("Genome-wide significance", 295, 6);

                ctx.restore();
            };

            // Reference lines are now handled by SVG

            const renderCircles = () => {
                ctx.save();
                ctx.translate(graphConstants.margin.left, graphConstants.margin.top);

                canvasCircles.forEach(circle => {
                    const isHighlighted = highlightedCircle && circle.display_snp === highlightedCircle.display_snp;
                    const radius = isHighlighted ? circle.radius + 8 : circle.radius;

                    ctx.beginPath();
                    ctx.arc(circle.x, circle.y, radius, 0, 2 * Math.PI);
                    ctx.fillStyle = circle.fillColor;
                    ctx.fill();
                    ctx.strokeStyle = "#fff";
                    ctx.lineWidth = 1.5;
                    ctx.stroke();
                });

                ctx.restore();
            };

            // Chromosome backgrounds and labels are now handled by SVG

            // Mouse interaction handling
            const getMousePos = e => {
                const rect = canvas.getBoundingClientRect();
                return {
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top,
                };
            };

            const getCircleAt = (x, y) => {
                const plotX = x - graphConstants.margin.left;
                const plotY = y - graphConstants.margin.top;

                for (let i = canvasCircles.length - 1; i >= 0; i--) {
                    const circle = canvasCircles[i];
                    const distance = Math.sqrt((plotX - circle.x) ** 2 + (plotY - circle.y) ** 2);
                    if (distance <= circle.radius + 5) {
                        // Add padding for easier clicking
                        return circle;
                    }
                }
                return null;
            };

            const getChromosomeAt = (x, y) => {
                const plotX = x - graphConstants.margin.left;
                const plotY = y - graphConstants.margin.top;

                if (plotY < 0 || plotY > height) return null;

                for (const chr of self.svgs.metadata.x_axis) {
                    const xStart = (chr.pixel_start / self.svgs.metadata.svg_width) * width;
                    const xEnd = (chr.pixel_end / self.svgs.metadata.svg_width) * width;

                    if (plotX >= xStart && plotX <= xEnd) {
                        return chr;
                    }
                }
                return null;
            };

            // Mouse event handlers
            canvas.addEventListener("mousemove", e => {
                const mousePos = getMousePos(e);
                const circle = getCircleAt(mousePos.x, mousePos.y);

                if (circle) {
                    canvas.style.cursor = "pointer";
                    // Reset chromosome hover if hovering over a circle
                    if (hoveredChromosome !== null) {
                        if (chromosomeRects) {
                            chromosomeRects.each(function (d) {
                                if (d.CHR === hoveredChromosome.CHR) {
                                    const i = self.svgs.metadata.x_axis.indexOf(d);
                                    const chrBgColor1 = constants.darkMode ? "#3a3a3a" : "#e5e5e5";
                                    const chrBgColor2 = constants.darkMode ? "#2d2d2d" : "#ffffff";
                                    d3.select(this)
                                        .transition()
                                        .duration(200)
                                        .attr("fill", i % 2 === 0 ? chrBgColor1 : chrBgColor2);
                                }
                            });
                        }
                        hoveredChromosome = null;
                    }
                    if (highlightedCircle !== circle) {
                        highlightedCircle = circle;
                        renderCanvas();
                        renderCircles();
                        renderLegend();

                        const tooltipContent = graphTransformations.getTraitListHTML(circle._group);
                        graphTransformations.getTooltip(tooltipContent, e);
                    }
                } else {
                    // Check for chromosome hover (only in full view)
                    if (self.displayFilters.view === "full" || self.displayFilters.chr === null) {
                        const chr = getChromosomeAt(mousePos.x, mousePos.y);
                        if (chr) {
                            canvas.style.cursor = "grab";
                            if (hoveredChromosome?.CHR !== chr.CHR) {
                                // Reset previous hover
                                if (hoveredChromosome !== null && chromosomeRects) {
                                    chromosomeRects.each(function (d) {
                                        if (d.CHR === hoveredChromosome.CHR) {
                                            const i = self.svgs.metadata.x_axis.indexOf(d);
                                            const chrBgColor1 = constants.darkMode ? "#3a3a3a" : "#e5e5e5";
                                            const chrBgColor2 = constants.darkMode ? "#2d2d2d" : "#ffffff";
                                            d3.select(this)
                                                .transition()
                                                .duration(200)
                                                .attr("fill", i % 2 === 0 ? chrBgColor1 : chrBgColor2);
                                        }
                                    });
                                }
                                // Set new hover
                                hoveredChromosome = chr;
                                if (chromosomeRects) {
                                    const chrHoverColor = constants.darkMode ? "#4a5a6a" : "#e6f3ff";
                                    chromosomeRects.each(function (d) {
                                        if (d.CHR === chr.CHR) {
                                            d3.select(this).transition().duration(200).attr("fill", chrHoverColor);
                                        }
                                    });
                                }
                            }
                        } else {
                            canvas.style.cursor = "default";
                            // Reset chromosome hover
                            if (hoveredChromosome !== null) {
                                if (chromosomeRects) {
                                    chromosomeRects.each(function (d) {
                                        if (d.CHR === hoveredChromosome.CHR) {
                                            const i = self.svgs.metadata.x_axis.indexOf(d);
                                            const chrBgColor1 = constants.darkMode ? "#3a3a3a" : "#e5e5e5";
                                            const chrBgColor2 = constants.darkMode ? "#2d2d2d" : "#ffffff";
                                            d3.select(this)
                                                .transition()
                                                .duration(200)
                                                .attr("fill", i % 2 === 0 ? chrBgColor1 : chrBgColor2);
                                        }
                                    });
                                }
                                hoveredChromosome = null;
                            }
                        }
                    } else {
                        canvas.style.cursor = "default";
                    }
                    if (highlightedCircle) {
                        highlightedCircle = null;
                        renderCanvas();
                        renderCircles();
                        renderLegend();
                        d3.selectAll(".tooltip").remove();
                    }
                }
            });

            canvas.addEventListener("mousedown", () => {
                if (hoveredChromosome) {
                    canvas.style.cursor = "grabbing";
                }
            });

            canvas.addEventListener("mouseup", () => {
                if (hoveredChromosome) {
                    canvas.style.cursor = "grab";
                }
            });

            canvas.addEventListener("click", e => {
                const mousePos = getMousePos(e);
                const circle = getCircleAt(mousePos.x, mousePos.y);

                if (circle) {
                    const variantType = circle.coloc_group_id
                        ? constants.colors.dataTypes.common
                        : constants.colors.dataTypes.rare;
                    graphTransformations.handleColocGroupClick.bind(self)(circle.display_snp, variantType);
                    d3.selectAll(".tooltip").remove();
                } else {
                    // Only check for chromosome click when in full view (not when zoomed in on a chromosome)
                    if (self.displayFilters.view === "full" || self.displayFilters.chr === null) {
                        const chr = getChromosomeAt(mousePos.x, mousePos.y);
                        if (chr) {
                            self.displayFilters.view = "chromosome";
                            self.displayFilters.chr = chr.CHR;
                            self.displayFilters.candidateSnp = null;
                        }
                    }
                }
            });

            function renderResetDisplayButton() {
                // Clear any existing reset button
                interactivePlotGroup.selectAll(".reset-button-group").remove();

                if (
                    self.displayFilters.chr !== null ||
                    self.displayFilters.candidateSnp !== null ||
                    self.displayFilters.traitName !== null
                ) {
                    const btnX = width / 2 + 60;
                    const btnY = height + 25;
                    const btnWidth = 90;
                    const btnHeight = 22;
                    // Use adaptive colors for button background
                    const buttonBgColor = constants.darkMode ? "#2d2d2d" : "#ffffff";
                    const buttonBorderColor = constants.darkMode ? "#666666" : "#b5b5b5";

                    // Create a separate interactive group for the button (above canvas)
                    const resetButtonGroup = interactivePlotGroup
                        .append("g")
                        .attr("class", "reset-button-group")
                        .style("pointer-events", "all");

                    resetButtonGroup
                        .append("rect")
                        .attr("x", btnX)
                        .attr("y", btnY)
                        .attr("width", btnWidth)
                        .attr("height", btnHeight)
                        .attr("rx", 6)
                        .attr("fill", buttonBgColor)
                        .attr("stroke", buttonBorderColor)
                        .style("cursor", "pointer")
                        .on("click", () => self.removeDisplayFilters());
                    resetButtonGroup
                        .append("text")
                        .attr("x", btnX + btnWidth / 2)
                        .attr("y", btnY + btnHeight / 2 + 3)
                        .attr("text-anchor", "middle")
                        .attr("alignment-baseline", "middle")
                        .attr("font-size", 13)
                        .attr("fill", textColor)
                        .attr("class", "button is-small")
                        .style("cursor", "pointer")
                        .text("Reset Display")
                        .on("click", () => self.removeDisplayFilters());
                }
            }

            function loadSvg(specificSvg) {
                if (!specificSvg) return;

                foreignObject.selectAll("*").remove();
                const parser = new DOMParser();
                const svgDoc = parser.parseFromString(specificSvg, "image/svg+xml");
                const importedSvg = svgDoc.documentElement;

                // Remove width/height attributes to allow scaling
                importedSvg.removeAttribute("width");
                importedSvg.removeAttribute("height");
                importedSvg.setAttribute("preserveAspectRatio", "xMidYMid meet");
                importedSvg.setAttribute(
                    "viewBox",
                    `0 0 ${self.svgs.metadata.svg_width} ${self.svgs.metadata.svg_height}`
                );
                importedSvg.style.pointerEvents = "none"; // Make the SVG non-interactive

                // Append the SVG to foreignObject
                foreignObject.node().appendChild(importedSvg);
            }

            function calculateDynamicCircleRadius(groupSize) {
                // Safety check: if radiusInfo not initialized, return default
                if (radiusInfo.maxGroupSize === 0 || radiusInfo.minRadius === 0) {
                    return 5;
                }
                if (radiusInfo.maxGroupSize === radiusInfo.minGroupSize) {
                    // All groups are the same size, use average radius
                    return (radiusInfo.minRadius + radiusInfo.maxRadius) / 2;
                }
                // Normalize groupSize between minGroupSize and maxGroupSize
                const normalizedSize =
                    (groupSize - radiusInfo.minGroupSize) / (radiusInfo.maxGroupSize - radiusInfo.minGroupSize);
                // Map to radius range and ensure it's capped at maxRadius
                const radius = radiusInfo.minRadius + normalizedSize * (radiusInfo.maxRadius - radiusInfo.minRadius);
                return Math.min(Math.max(radius, radiusInfo.minRadius), radiusInfo.maxRadius);
            }

            function renderChromosomeView() {
                const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == self.displayFilters.chr);
                const chrSvg = self.svgs.chromosomes[`chr${self.displayFilters.chr}`];
                loadSvg(chrSvg);

                const xScale = d3.scaleLinear().domain([chrMeta.bp_start, chrMeta.bp_end]).range([0, width]);

                const xAxis = d3.axisBottom(xScale).ticks(0).tickSize(0);
                const xAxisGroup = plotGroup.append("g").attr("transform", `translate(0,${height})`).call(xAxis);
                xAxisGroup.selectAll("line, path").style("stroke", textColor);
                plotGroup
                    .append("text")
                    .attr("x", width / 2)
                    .attr("y", height + 40)
                    .style("text-anchor", "middle")
                    .style("font-size", "14px")
                    .style("fill", textColor)
                    .text(`Chromosome ${self.displayFilters.chr}`);

                chrLabels
                    .selectAll("text")
                    .data(self.svgs.metadata.x_axis)
                    .join("text")
                    .transition()
                    .duration(500)
                    .attr("opacity", 0);

                // Clear chromosome backgrounds when zoomed in (they should only be interactive in full view)
                chrBackgrounds.selectAll("rect").remove();
                hoveredChromosome = null;

                renderResetDisplayButton();

                // Prepare circle data for Canvas rendering
                const chrCircleData = circleData.filter(study => study.chr == self.displayFilters.chr);
                canvasCircles = chrCircleData.map(d => {
                    const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == d.chr);
                    const bpPosition = d.bp / (chrMeta.bp_end - chrMeta.bp_start);
                    const x = bpPosition * width;
                    const yValue = -Math.log10(d.min_p);
                    // Clip yValue to y-axis domain to prevent circles from being drawn outside canvas
                    const clippedYValue = Math.max(
                        self.svgs.metadata.y_axis.min_lp,
                        Math.min(self.svgs.metadata.y_axis.max_lp, yValue)
                    );
                    let y = yScale(clippedYValue);
                    // If circle was clipped at the top, offset it slightly downward for visibility
                    if (yValue > self.svgs.metadata.y_axis.max_lp) {
                        y = y + 8; // Add 8 pixels downward offset
                    }
                    const radius = calculateDynamicCircleRadius(d._group.length);

                    let fillColor;
                    if (d.display_snp === self.displayFilters.candidateSnp) {
                        fillColor = constants.colors.dataTypes.highlighted;
                    } else if (d.coloc_group_id) {
                        fillColor = constants.colors.dataTypes.common;
                    } else {
                        fillColor = constants.colors.dataTypes.rare;
                    }

                    return {
                        ...d,
                        x,
                        y,
                        yValue, // Store original yValue for debugging
                        radius,
                        fillColor,
                    };
                });

                // Render everything on Canvas
                renderCanvas();
                renderCircles();
                renderLegend();
            }

            function renderFullView() {
                loadSvg(self.svgs.full);

                const xScale = d3
                    .scaleLinear()
                    .domain([0, self.svgs.metadata.x_axis[self.svgs.metadata.x_axis.length - 1].bp_end])
                    .range([0, width]);
                const xAxis = d3.axisBottom(xScale).ticks(0).tickSize(0);
                const xAxisGroup = plotGroup.append("g").attr("transform", `translate(0,${height})`).call(xAxis);
                xAxisGroup.selectAll("line, path").style("stroke", textColor);
                // X-axis label
                plotGroup
                    .append("text")
                    .attr("x", width / 2)
                    .attr("y", height + 40)
                    .style("text-anchor", "middle")
                    .style("font-size", "14px")
                    .style("fill", textColor)
                    .text("Chromosome");

                renderResetDisplayButton();

                // Clear existing chromosome backgrounds before adding new ones
                chrBackgrounds.selectAll("rect").remove();

                // Add chromosome backgrounds to main SVG (behind canvas)
                // Use adaptive colors for dark/light mode with original opacity
                const chrBgColor1 = constants.darkMode ? "#3a3a3a" : "#e5e5e5";
                const chrBgColor2 = constants.darkMode ? "#2d2d2d" : "#ffffff";

                chromosomeRects = chrBackgrounds
                    .selectAll("rect")
                    .data(self.svgs.metadata.x_axis)
                    .enter()
                    .append("rect")
                    .attr("x", chr => {
                        const xStart = (chr.pixel_start / self.svgs.metadata.svg_width) * width;
                        return xStart;
                    })
                    .attr("y", 0)
                    .attr("width", chr => {
                        const xStart = (chr.pixel_start / self.svgs.metadata.svg_width) * width;
                        const xEnd = (chr.pixel_end / self.svgs.metadata.svg_width) * width;
                        return xEnd - xStart;
                    })
                    .attr("height", height)
                    .attr("fill", (_, i) => (i % 2 === 0 ? chrBgColor1 : chrBgColor2))
                    .attr("opacity", 0.5);

                // Add chromosome labels to SVG
                self.svgs.metadata.x_axis.forEach(chr => {
                    const xPos = ((chr.pixel_start + chr.pixel_end) / 2 / self.svgs.metadata.svg_width) * width;
                    const label = chrLabels
                        .append("text")
                        .attr("x", xPos)
                        .attr("y", height + 20)
                        .style("text-anchor", "middle")
                        .style("font-size", "10px")
                        .style("fill", textColor)
                        .text(chr.CHR);
                    label.transition().duration(500).attr("opacity", 1);
                });
                if (self.filteredData.groupedColocs || self.filteredData.groupedRare) {
                    // Prepare circle data for Canvas rendering
                    canvasCircles = circleData.map(d => {
                        const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == d.chr);
                        const chrLength = chrMeta.bp_end - chrMeta.bp_start;
                        const bpRatio = d.bp / chrLength;
                        const x =
                            ((chrMeta.pixel_start + bpRatio * (chrMeta.pixel_end - chrMeta.pixel_start)) /
                                self.svgs.metadata.svg_width) *
                            width;
                        const yValue = -Math.log10(d.min_p);
                        // Clip yValue to y-axis domain to prevent circles from being drawn outside canvas
                        const clippedYValue = Math.max(
                            self.svgs.metadata.y_axis.min_lp,
                            Math.min(self.svgs.metadata.y_axis.max_lp, yValue)
                        );
                        let y = yScale(clippedYValue);
                        // If circle was clipped at the top, offset it slightly downward for visibility
                        if (yValue > self.svgs.metadata.y_axis.max_lp) {
                            y = y + 8;
                        }
                        const radius = calculateDynamicCircleRadius(d._group.length);

                        let fillColor;
                        if (d.display_snp === self.displayFilters.candidateSnp) {
                            fillColor = constants.colors.dataTypes.highlighted;
                        } else if (d.coloc_group_id) {
                            fillColor = constants.colors.dataTypes.common;
                        } else {
                            fillColor = constants.colors.dataTypes.rare;
                        }

                        return {
                            ...d,
                            x,
                            y,
                            yValue, // Store original yValue for debugging
                            radius,
                            fillColor,
                        };
                    });

                    // Render everything on Canvas
                    renderCanvas();
                    renderCircles();
                    renderLegend();
                }
            }

            // Initial render
            renderCanvas();
            renderLegend();

            if (self.displayFilters.view === "chromosome" && self.displayFilters.chr) {
                renderChromosomeView();
            } else {
                renderFullView();
            }
        },
    };
}
