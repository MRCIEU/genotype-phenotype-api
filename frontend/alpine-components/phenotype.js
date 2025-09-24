import JSZip from "jszip";
import * as d3 from "d3";
import { stringify } from "flatted";

import graphTransformations from "./graphTransformations.js";
import constants from "./constants.js";
import downloads from "./downloads.js";

export default function pheontype() {
    return {
        userUpload: false,
        data: null,
        filteredData: {
            colocs: null,
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
            snp: null,
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

                document.title = "GP Map: " + this.data.trait.trait_name;

                this.transformDataForGraphs();
            } catch (error) {
                console.error(error);
                this.errorMessage = `Failed to load data: ${error.status} ${error.statusText}`;
            }
        },

        transformDataForGraphs() {
            // Count frequency of each id in colocs and scale between 2 and 10
            const [scaledMinNumStudies, scaledMaxNumStudies] = [2, 10];
            const idFrequencies = this.data.coloc_groups.reduce((acc, obj) => {
                if (obj.coloc_group_id) {
                    acc[obj.coloc_group_id] = (acc[obj.coloc_group_id] || 0) + 1;
                }
                return acc;
            }, {});

            // Get min and max frequencies
            const frequencies = Object.values(idFrequencies);
            const minNumStudies = Math.min(...frequencies);
            const maxNumStudies = Math.max(...frequencies);

            this.data.study_extractions = this.data.study_extractions.map(se => {
                se.MbP = se.bp / 1000000;
                se.chrText = "CHR ".concat(se.chr);
                se.ignore = false;
                return se;
            });
            this.data.rare_results = this.data.rare_results.map(r => {
                r.MbP = r.bp / 1000000;
                r.chrText = "CHR ".concat(r.chr);
                r.ignore = false;
                return r;
            });
            this.data.coloc_groups = this.data.coloc_groups.map(c => {
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

            this.filteredData.coloc_groups = this.data.coloc_groups.filter(coloc => {
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

            this.filteredData.rare = this.data.rare_results.filter(rare => {
                const graphOptionFilters =
                    rare.min_p <= graphOptions.pValue &&
                    !graphOptions.includeTrans &&
                    (graphOptions.traitType === "all" || graphOptions.traitType === "phenotype");
                return graphOptionFilters;
            });

            this.filteredData.groupedColocs = graphTransformations.groupBySnp(
                this.filteredData.coloc_groups,
                "trait",
                this.data.trait.id,
                this.displayFilters
            );
            this.filteredData.groupedRare = graphTransformations.groupBySnp(
                this.filteredData.rare,
                "trait",
                this.data.trait.id,
                this.displayFilters
            );

            const allFilteredData = { ...this.filteredData.groupedColocs, ...this.filteredData.groupedRare };
            this.traitSearch.orderedTraits = graphTransformations.getOrderedTraits(allFilteredData);
        },

        async getSvgData(traitId) {
            if (constants.isLocal) {
                const minP = this.data.coloc_groups.reduce((min, se) => Math.min(min, se.min_p), Infinity);
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

        async downloadData() {
            await downloads.downloadDataToZip(this.data, this.data.trait.trait_name);
            this.downloadClicked = true;
        },

        get showResults() {
            if (this.userUpload) return this.data.trait.status === "completed";
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
                snp: null,
                traitName: null,
            };
            this.traitSearch.text = "";
        },

        get getDataForColocTable() {
            if (!this.filteredData.coloc_groups || this.filteredData.coloc_groups.length === 0) return [];

            let tableData = this.filteredData.coloc_groups.filter(coloc => {
                if (this.displayFilters.snp !== null) return coloc.display_snp === this.displayFilters.snp;
                else if (this.displayFilters.chr !== null) return coloc.chr == this.displayFilters.chr;
                else return true;
            });

            tableData = graphTransformations.addColorForSNPs(tableData);
            tableData = graphTransformations.groupBySnp(tableData, "trait", this.data.trait.id, this.displayFilters);

            return stringify(Object.fromEntries(Object.entries(tableData).slice(0, constants.maxSNPGroupsToDisplay)));
        },

        get doRareResultsExist() {
            return this.data && this.data.trait.rare_study !== null;
        },

        get getDataForRareTable() {
            if (!this.filteredData.rare || this.filteredData.rare.length === 0) return [];

            let tableData = this.filteredData.rare.filter(rare => {
                if (this.displayFilters.snp !== null) return rare.display_snp === this.displayFilters.snp;
                else if (this.displayFilters.chr !== null) return rare.chr == this.displayFilters.chr;
                else return true;
            });

            tableData = graphTransformations.addColorForSNPs(tableData);
            tableData = graphTransformations.groupBySnp(tableData, "trait", this.data.trait.id, this.displayFilters);

            return stringify(Object.fromEntries(Object.entries(tableData).slice(0, constants.maxSNPGroupsToDisplay)));
        },

        initPhenotypeGraph() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("phenotype-chart");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () =>
                this.getPhenotypeGraph()
            );
        },

        getPhenotypeGraph() {
            if (!this.svgs.metadata) return;

            const chartContainer = document.getElementById("phenotype-chart");
            chartContainer.innerHTML = "";

            let self = this;
            const graphConstants = {
                margin: { top: 20, right: 20, bottom: 60, left: 80 },
                legend: { width: 450, height: 20 },
            };

            // Get container dimensions
            const containerWidth = chartContainer.clientWidth;
            const aspectRatio = self.svgs.metadata.svg_height / self.svgs.metadata.svg_width;
            const width = containerWidth - graphConstants.margin.left - graphConstants.margin.right;
            const height = width * aspectRatio;

            // Shared variables for circle size calculations
            let circleData = [];
            let radiusInfo = {
                maxGroupSize: 0,
                minRadius: 0,
                maxRadius: 0,
            };

            if (self.filteredData.groupedColocs || self.filteredData.groupedRare) {
                const allGroups = Object.values(self.filteredData.groupedColocs).concat(
                    Object.values(self.filteredData.groupedRare)
                );
                circleData = allGroups
                    .map(group => {
                        const traitId = self.data.trait.id;
                        const study = group.find(s => s.trait_id === traitId);
                        if (!study) return null;
                        study._group = group;
                        return study;
                    })
                    .filter(Boolean);

                if (circleData.length > 0) {
                    radiusInfo.maxGroupSize = Math.max(...circleData.map(d => d._group.length));
                    radiusInfo.minRadius = Math.min(...circleData.map(d => d._group.length)) + 2;
                    radiusInfo.maxRadius = Math.max(
                        radiusInfo.minRadius + 5,
                        Math.min(radiusInfo.maxGroupSize + 2, 20)
                    );
                }
            }

            // Create SVG container
            const svg = d3
                .select(chartContainer)
                .append("svg")
                .attr("width", width + graphConstants.margin.left + graphConstants.margin.right)
                .attr("height", height + graphConstants.margin.top + graphConstants.margin.bottom)
                .attr(
                    "viewBox",
                    `0 0 ${width + graphConstants.margin.left + graphConstants.margin.right} ${height + graphConstants.margin.top + graphConstants.margin.bottom}`
                );

            // Create main plot group
            const plotGroup = svg
                .append("g")
                .attr("transform", `translate(${graphConstants.margin.left},${graphConstants.margin.top})`);

            // Create a foreignObject to properly embed the SVG
            const foreignObject = plotGroup
                .append("foreignObject")
                .attr("width", width)
                .attr("height", height)
                .attr("overflow", "hidden");

            // Add chromosome backgrounds for ALL chromosomes
            const chrBackgrounds = plotGroup
                .append("g")
                .attr("class", "chr-backgrounds")
                .style("pointer-events", "all");

            // Add chromosome labels
            const chrLabels = plotGroup.append("g").attr("class", "chr-labels");

            const yScale = d3
                .scaleLinear()
                .domain([self.svgs.metadata.y_axis.min_lp, self.svgs.metadata.y_axis.max_lp])
                .range([height, 0]);

            const yAxis = d3
                .axisLeft(yScale)
                .ticks(10)
                .tickFormat(d => d);
            plotGroup.append("g").call(yAxis).selectAll("text").style("text-anchor", "end").style("font-size", "12px");
            plotGroup
                .append("text")
                .attr("transform", "rotate(-90)")
                .attr("x", -height / 2)
                .attr("y", -50)
                .style("text-anchor", "middle")
                .style("font-size", "14px")
                .text("-log10(p-value)");

            // Store coloc circles in a group for easy manipulation
            const colocCirclesGroup = plotGroup.append("g").attr("class", "coloc-circles");

            colocCirclesGroup.selectAll("circle").transition().duration(500).attr("opacity", 0).remove();

            function renderLegend() {
                const legendY = -10;
                const legendX = width - graphConstants.legend.width;
                const legendGroup = plotGroup
                    .append("g")
                    .attr("class", "legend")
                    .attr("transform", `translate(${legendX}, ${legendY})`);
                legendGroup
                    .append("rect")
                    .attr("x", -10)
                    .attr("y", -10)
                    .attr("width", graphConstants.legend.width)
                    .attr("height", graphConstants.legend.height)
                    .attr("fill", "none")
                    .attr("stroke", "#bbb")
                    .attr("stroke-width", 1);

                // Common
                legendGroup
                    .append("circle")
                    .attr("cx", 0)
                    .attr("cy", 2)
                    .attr("r", 5)
                    .attr("fill", constants.colors.dataTypes.common)
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 1);

                legendGroup.append("text").attr("x", 10).attr("y", 6).style("font-size", "12px").text("Common");

                // Rare
                legendGroup
                    .append("circle")
                    .attr("cx", 70)
                    .attr("cy", 2)
                    .attr("r", 5)
                    .attr("fill", constants.colors.dataTypes.rare)
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 1);

                legendGroup.append("text").attr("x", 80).attr("y", 6).style("font-size", "12px").text("Rare");

                // Suggestive significance (dashed line)
                legendGroup
                    .append("line")
                    .attr("x1", 115)
                    .attr("x2", 135)
                    .attr("y1", 3)
                    .attr("y2", 3)
                    .attr("stroke", "darkred")
                    .attr("stroke-width", 0.8)
                    .attr("stroke-dasharray", "5,5");

                legendGroup
                    .append("text")
                    .attr("x", 135)
                    .attr("y", 6)
                    .style("font-size", "12px")
                    .text("Suggestive significance");

                // Genome-wide significance (solid line)
                legendGroup
                    .append("line")
                    .attr("x1", 270)
                    .attr("x2", 290)
                    .attr("y1", 3)
                    .attr("y2", 3)
                    .attr("stroke", "darkred")
                    .attr("stroke-width", 0.8);

                legendGroup
                    .append("text")
                    .attr("x", 295)
                    .attr("y", 6)
                    .style("font-size", "12px")
                    .text("Genome-wide significance");
            }

            // Add reference lines
            const referenceLines = plotGroup.append("g").attr("class", "reference-lines");
            referenceLines
                .append("line")
                .attr("x1", 0)
                .attr("x2", width)
                .attr("y1", yScale(4))
                .attr("y2", yScale(4))
                .attr("stroke", "darkred")
                .attr("opacity", 0.8)
                .attr("stroke-width", 0.6)
                .attr("stroke-dasharray", "5,5");

            referenceLines
                .append("line")
                .attr("x1", 0)
                .attr("x2", width)
                .attr("y1", yScale(7.3))
                .attr("y2", yScale(7.3))
                .attr("stroke", "darkred")
                .attr("opacity", 0.8)
                .attr("stroke-width", 0.6);

            function renderResetDisplayButton() {
                if (
                    self.displayFilters.chr !== null ||
                    self.displayFilters.snp !== null ||
                    self.displayFilters.traitName !== null
                ) {
                    const btnX = width / 2 + 60;
                    const btnY = height + 25;
                    const btnWidth = 90;
                    const btnHeight = 22;
                    plotGroup
                        .append("rect")
                        .attr("x", btnX)
                        .attr("y", btnY)
                        .attr("width", btnWidth)
                        .attr("height", btnHeight)
                        .attr("rx", 6)
                        .attr("fill", "white")
                        .attr("stroke", "#b5b5b5")
                        .style("cursor", "pointer")
                        .on("click", () => self.removeDisplayFilters());
                    plotGroup
                        .append("text")
                        .attr("x", btnX + btnWidth / 2)
                        .attr("y", btnY + btnHeight / 2 + 3)
                        .attr("text-anchor", "middle")
                        .attr("alignment-baseline", "middle")
                        .attr("font-size", 13)
                        .attr("fill", "#363636")
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
                const normalizedSize =
                    (groupSize - radiusInfo.minRadius + 2) / (radiusInfo.maxGroupSize - radiusInfo.minRadius + 2);
                return radiusInfo.minRadius + normalizedSize * (radiusInfo.maxRadius - radiusInfo.minRadius);
            }

            function renderChromosomeView() {
                const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == self.displayFilters.chr);
                const chrSvg = self.svgs.chromosomes[`chr${self.displayFilters.chr}`];
                loadSvg(chrSvg);

                const xScale = d3.scaleLinear().domain([chrMeta.bp_start, chrMeta.bp_end]).range([0, width]);

                const xAxis = d3.axisBottom(xScale).ticks(0).tickSize(0);
                plotGroup.append("g").attr("transform", `translate(0,${height})`).call(xAxis);
                plotGroup
                    .append("text")
                    .attr("x", width / 2)
                    .attr("y", height + 40)
                    .style("text-anchor", "middle")
                    .style("font-size", "14px")
                    .text(`Chromosome ${self.displayFilters.chr}`);

                chrLabels
                    .selectAll("text")
                    .data(self.svgs.metadata.x_axis)
                    .join("text")
                    .transition()
                    .duration(500)
                    .attr("opacity", 0);

                renderResetDisplayButton();

                // Only show circles for the selected chromosome
                const chrCircleData = circleData.filter(study => study.chr == self.displayFilters.chr);
                const circles = colocCirclesGroup.selectAll("circle").data(chrCircleData, d => d.display_snp);

                circles
                    .enter()
                    .append("circle")
                    .attr("cx", d => {
                        const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == d.chr);
                        const bpPosition = d.bp / (chrMeta.bp_end - chrMeta.bp_start);
                        return bpPosition * width;
                    })
                    .attr("cy", d => {
                        const yValue = -Math.log10(d.min_p);
                        return yScale(yValue);
                    })
                    .attr("r", d => {
                        return calculateDynamicCircleRadius(d._group.length);
                    })
                    .attr("fill", d => {
                        if (d.display_snp === self.displayFilters.snp) return constants.colors.dataTypes.highlighted;
                        else if (d.coloc_group_id) return constants.colors.dataTypes.common;
                        else return constants.colors.dataTypes.rare;
                    })
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 1.5)
                    .attr("opacity", 0.8)
                    .on("mouseover", function (event, d) {
                        d3.select(this).style("cursor", "pointer");
                        const currentRadius = calculateDynamicCircleRadius(d._group.length);
                        d3.select(this)
                            .transition()
                            .duration("100")
                            .attr("fill", constants.colors.dataTypes.highlighted)
                            .attr("r", currentRadius + 8);
                        const tooltipContent = graphTransformations.getTraitListHTML(d._group);
                        graphTransformations.getTooltip(tooltipContent, event);
                    })
                    .on("mouseout", function () {
                        d3.select(this)
                            .transition()
                            .duration("200")
                            .attr("fill", d => {
                                if (d.display_snp === self.displayFilters.snp)
                                    return constants.colors.dataTypes.highlighted;
                                else if (d.coloc_group_id) return constants.colors.dataTypes.common;
                                else return constants.colors.dataTypes.rare;
                            })
                            .attr("r", d => {
                                return calculateDynamicCircleRadius(d._group.length);
                            });
                        d3.selectAll(".tooltip").remove();
                    })
                    .on("click", function (_, d) {
                        self.displayFilters.snp = d.display_snp;
                    });
            }

            function renderFullView() {
                loadSvg(self.svgs.full);

                const xScale = d3
                    .scaleLinear()
                    .domain([0, self.svgs.metadata.x_axis[self.svgs.metadata.x_axis.length - 1].bp_end])
                    .range([0, width]);
                const xAxis = d3.axisBottom(xScale).ticks(0).tickSize(0);
                plotGroup.append("g").attr("transform", `translate(0,${height})`).call(xAxis);
                // X-axis label
                plotGroup
                    .append("text")
                    .attr("x", width / 2)
                    .attr("y", height + 40)
                    .style("text-anchor", "middle")
                    .style("font-size", "14px")
                    .text("Chromosome");

                renderResetDisplayButton();

                self.svgs.metadata.x_axis.forEach((chr, i) => {
                    const xStart = (chr.pixel_start / self.svgs.metadata.svg_width) * width;
                    const xEnd = (chr.pixel_end / self.svgs.metadata.svg_width) * width;
                    chrBackgrounds
                        .append("rect")
                        .datum(chr)
                        .attr("x", xStart)
                        .attr("y", 0)
                        .attr("width", xEnd - xStart)
                        .attr("height", height)
                        .attr("fill", i % 2 === 0 ? "#e5e5e5" : "#ffffff")
                        .attr("opacity", 0.5)
                        .style("cursor", "pointer")
                        .on("mouseover", function () {
                            d3.select(this).transition().duration(200).attr("fill", "#e6f3ff");
                        })
                        .on("mouseout", function () {
                            d3.select(this)
                                .transition()
                                .duration(200)
                                .attr("fill", i % 2 === 0 ? "#e5e5e5" : "#ffffff");
                        })
                        .on("click", function () {
                            self.displayFilters.view = "chromosome";
                            self.displayFilters.chr = chr.CHR;
                            self.displayFilters.snp = null;
                        });
                });

                self.svgs.metadata.x_axis.forEach(chr => {
                    const xPos = ((chr.pixel_start + chr.pixel_end) / 2 / self.svgs.metadata.svg_width) * width;
                    const label = chrLabels
                        .append("text")
                        .attr("x", xPos)
                        .attr("y", height + 20)
                        .style("text-anchor", "middle")
                        .style("font-size", "10px")
                        .text(chr.CHR);
                    label.transition().duration(500).attr("opacity", 1);
                });
                if (self.filteredData.groupedColocs || self.filteredData.groupedRare) {
                    const circles = colocCirclesGroup.selectAll("circle").data(circleData, d => d.display_snp);

                    circles
                        .enter()
                        .append("circle")
                        .attr("cx", d => {
                            const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == d.chr);
                            const chrLength = chrMeta.bp_end - chrMeta.bp_start;
                            const bpRatio = d.bp / chrLength;
                            const xPixel =
                                ((chrMeta.pixel_start + bpRatio * (chrMeta.pixel_end - chrMeta.pixel_start)) /
                                    self.svgs.metadata.svg_width) *
                                width;
                            return xPixel;
                        })
                        .attr("cy", d => {
                            const yValue = -Math.log10(d.min_p);
                            return yScale(yValue);
                        })
                        .attr("r", d => {
                            return calculateDynamicCircleRadius(d._group.length);
                        })
                        .attr("fill", d => {
                            if (d.display_snp === self.displayFilters.snp)
                                return constants.colors.dataTypes.highlighted;
                            else if (d.coloc_group_id) return constants.colors.dataTypes.common;
                            else return constants.colors.dataTypes.rare;
                        })
                        .attr("stroke", "#fff")
                        .attr("stroke-width", 1.5)
                        .attr("opacity", 0.8)
                        .on("mouseover", function (event, d) {
                            d3.select(this).style("cursor", "pointer");
                            const currentRadius = calculateDynamicCircleRadius(d._group.length);

                            d3.select(this)
                                .transition()
                                .duration("100")
                                .attr("fill", constants.colors.dataTypes.highlighted)
                                .attr("r", currentRadius + 8);
                            const tooltipContent = graphTransformations.getTraitListHTML(d._group);
                            graphTransformations.getTooltip(tooltipContent, event);
                        })
                        .on("mouseout", function () {
                            d3.select(this)
                                .transition()
                                .duration("200")
                                .attr("fill", d => {
                                    if (d.display_snp === self.displayFilters.snp)
                                        return constants.colors.dataTypes.highlighted;
                                    else if (d.coloc_group_id) return constants.colors.dataTypes.common;
                                    else return constants.colors.dataTypes.rare;
                                })
                                .attr("r", d => {
                                    return calculateDynamicCircleRadius(d._group.length);
                                });
                            d3.selectAll(".tooltip").remove();
                        })
                        .on("click", function (_, d) {
                            self.displayFilters.snp = d.display_snp;
                        });
                }
            }

            renderLegend();
            if (self.displayFilters.view === "chromosome" && self.displayFilters.chr) {
                renderChromosomeView();
            } else {
                renderFullView();
            }
        },
    };
}
