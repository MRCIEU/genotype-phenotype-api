import * as d3 from "d3";
import JSZip from "jszip";

import constants from "./constants.js";
import graphTransformations from "./graphTransformations.js";

export default function snp() {
    return {
        data: {
            colocs: [],
            variant: null,
            highlightedStudy: null,
        },
        svgZips: {},
        svgs: [],
        loadingSvgs: new Set(),

        async init() {
            this.$watch("$store.snpGraphStore", newValue => {
                this.data.highlightedStudy = newValue.highlightedStudy;
                this.data = newValue;
                this.updateHighlightedStudy();

                if (newValue.colocs && newValue.colocs.length > 0 && Object.keys(this.svgZips).length === 0) {
                    this.loadData();
                }
            });
            this.loadData();
        },

        async loadData() {
            if (!this.data.colocs || this.data.colocs.length === 0 || !this.data.variant) return;

            let colocGroupIds = [...new Set(this.data.colocs.map(cg => cg.coloc_group_id))];

            const initialSvgLoadNumber = 20;
            if (constants.isLocal) {
                colocGroupIds = ["test"];
            }
            for (const colocGroupId of colocGroupIds) {
                // Skip if we already have this zip file loaded
                if (this.svgZips[colocGroupId]) {
                    console.log(`SVG zip for coloc group ${colocGroupId} already loaded`);
                    continue;
                }

                const svgsUrl = `${constants.assetBaseUrl}/groups/coloc_group_${colocGroupId}_svgs.zip`;
                const zipResponse = await fetch(svgsUrl);
                const zipBlob = await zipResponse.blob();
                this.svgZips[colocGroupId] = await JSZip.loadAsync(zipBlob);

                const entries = Object.entries(this.svgZips[colocGroupId].files);
                for (let i = 0; i < Math.min(entries.length, initialSvgLoadNumber); i++) {
                    const [filename, _] = entries[i];
                    let studyExtractionId = parseInt(filename.split(".svg")[0]);
                    await this.loadSpecificSvg(colocGroupId, studyExtractionId);
                }
            }
            this.initManhattanPlotOverlay();
        },

        async loadSpecificSvg(colocGroupId, studyExtractionId) {
            if (constants.isLocal) {
                colocGroupId = "test";
            }
            if (
                this.loadingSvgs.has(studyExtractionId) ||
                this.svgs.some(s => s.studyExtractionId === studyExtractionId)
            ) {
                return;
            }

            if (!this.svgZips[colocGroupId]) return;

            this.loadingSvgs.add(studyExtractionId);

            try {
                const entries = Object.entries(this.svgZips[colocGroupId].files);

                let file = null;
                if (constants.isLocal) {
                    const fileIndex = studyExtractionId % entries.length;
                    const foundEntry = entries.find(entry => entry[0].includes(fileIndex.toString()));
                    if (foundEntry) {
                        file = foundEntry[1];
                    }
                } else {
                    const foundEntry = entries.find(entry => entry[0].includes(studyExtractionId.toString()));
                    if (foundEntry) {
                        file = foundEntry[1];
                    }
                }

                if (!file) {
                    console.warn(`No SVG file found for study extraction ID: ${studyExtractionId}`);
                    return;
                }

                const originalStudyExtractionId = studyExtractionId;
                const svgContent = await file.async("text");
                this.svgs.push({ studyExtractionId: originalStudyExtractionId, svgContent });
            } finally {
                this.loadingSvgs.delete(studyExtractionId);
            }
        },

        updateHighlightedStudy() {
            if (this.data.highlightedStudy) {
                if (this.data && this.data.colocs && this.data.colocs.length > 0) {
                    this.loadSpecificSvg(
                        this.data.highlightedStudy.colocGroupId,
                        this.data.highlightedStudy.studyExtractionId
                    );
                }
                this.getManhattanPlotOverlay();
            }
        },

        initManhattanPlotOverlay() {
            if (!this.data || !this.data.variant || !this.data.colocs) return;

            const chartContainer = document.getElementById("manhattan-plot");
            graphTransformations.initGraph(chartContainer, this.data, null, () => this.getManhattanPlotOverlay());
        },

        getManhattanPlotOverlay() {
            d3.select("#manhattan-plot").selectAll("*").remove();

            const width = document.getElementById("manhattan-plot").clientWidth;
            const originalSvgWidth = 1000;
            const height = 200;
            const margin = { top: 30, right: 30, bottom: 50, left: 20 };

            const minBP = this.data.variant.min_bp / 1e6;
            const maxBP = this.data.variant.max_bp / 1e6;

            const x = d3
                .scaleLinear()
                .domain([minBP, maxBP])
                .range([margin.left, width - margin.right]);

            const svg = d3.select("#manhattan-plot").append("svg").attr("width", width).attr("height", height);

            svg.append("g")
                .attr("transform", `translate(0,${height - margin.bottom})`)
                .call(
                    d3
                        .axisBottom(x)
                        .ticks((maxBP - minBP) / 0.1)
                        .tickFormat(d3.format(".1f"))
                );
            svg.append("text")
                .attr("x", width / 2)
                .attr("y", height - 10)
                .attr("text-anchor", "middle")
                .text(`CHR ${this.data.variant.chr}`);

            const renderSvg = (_, svgContent, isHighlighted) => {
                let parser = new DOMParser();
                let doc = parser.parseFromString(svgContent, "image/svg+xml");
                let importedSvg = doc.documentElement;

                // Remove width/height to allow scaling
                importedSvg.removeAttribute("width");
                importedSvg.removeAttribute("height");
                importedSvg.setAttribute("preserveAspectRatio", "xMidYMid meet");
                importedSvg.setAttribute("viewBox", `0 0 ${originalSvgWidth} ${height}`);

                if (isHighlighted) {
                    importedSvg.querySelectorAll("g, path").forEach(element => {
                        element.removeAttribute("class");
                        element.removeAttribute("style");
                        element.setAttribute("fill", "#1976d2");
                        element.setAttribute("stroke", "#1976d2");
                        element.setAttribute("opacity", "0.9");
                    });
                } else {
                    importedSvg.querySelectorAll("g, path").forEach(element => {
                        element.removeAttribute("class");
                        element.removeAttribute("style");
                        element.setAttribute("opacity", "0.4");
                    });
                }

                let g = document.createElementNS("http://www.w3.org/2000/svg", "g");

                while (importedSvg.childNodes.length > 0) {
                    g.appendChild(importedSvg.childNodes[0]);
                }

                const plotWidth = width - margin.left - margin.right;
                const plotHeight = height - margin.top - margin.bottom;
                const scaleX = plotWidth / originalSvgWidth;
                const scaleY = plotHeight / height;
                g.setAttribute("transform", `translate(${margin.left},${margin.top}) scale(${scaleX},${scaleY})`);

                svg.node().appendChild(g);
            };

            // First, render all non-highlighted SVGs
            this.svgs.forEach(({ studyExtractionId, svgContent }) => {
                const isHighlighted =
                    this.data.highlightedStudy && this.data.highlightedStudy.studyExtractionId === studyExtractionId;
                if (!isHighlighted) {
                    renderSvg(studyExtractionId, svgContent, false);
                }
            });

            // Then, render the highlighted SVG (if any) so it appears on top
            this.svgs.forEach(({ studyExtractionId, svgContent }) => {
                const isHighlighted =
                    this.data.highlightedStudy && this.data.highlightedStudy.studyExtractionId === studyExtractionId;
                if (isHighlighted) {
                    renderSvg(studyExtractionId, svgContent, true);
                }
            });

            // Draw a thin red vertical line at the variant position (after SVGs so it appears on top)
            const variantMb = this.data.variant.bp / 1e6;
            const variantX = x(variantMb);
            svg.append("line")
                .attr("x1", variantX)
                .attr("x2", variantX)
                .attr("y1", margin.top)
                .attr("y2", height - margin.bottom)
                .attr("stroke", "red")
                .attr("stroke-width", 0.8)
                .attr("opacity", 0.8);
        },
    };
}
