import constants from "./constants.js";
import * as d3 from "d3";
import graphTransformations from "./graphTransformations.js";

export default {
    groupBySnp(data, type, id, displayFilters, userUpload = false) {
        id = parseInt(id);
        let attribute = null;
        if (type === "trait") {
            attribute = userUpload ? "gwas_upload_id" : "trait_id";
        } else if (type === "gene") {
            attribute = "gene_id";
        }
        let groupedData = Object.groupBy(data, ({ display_snp }) => display_snp);

        groupedData = Object.entries(groupedData).filter(([_, group]) => {
            let hasId = attribute ? group.some(entry => parseInt(entry[attribute]) === id) : true;
            if (type === "gene") {
                hasId = group.some(entry => parseInt(entry.gene_id) === id || parseInt(entry.situated_gene_id) === id);
            }
            const hasTrait = displayFilters.traitName
                ? group.some(entry => entry.trait_name === displayFilters.traitName)
                : true;
            const hasGene = displayFilters.gene
                ? group.some(entry => entry.gene === displayFilters.gene || entry.situated_gene === displayFilters.gene)
                : true;

            const moreThanOneTrait = group.length > 1;
            return hasId && hasTrait && hasGene && moreThanOneTrait;
        });

        groupedData.sort((a, b) => {
            const aMinP = Math.min(
                ...a[1]
                    .filter(entry =>
                        attribute ? entry[attribute] === id && entry.min_p !== null : entry.min_p !== null
                    )
                    .map(entry => entry.min_p)
            );
            const bMinP = Math.min(
                ...b[1]
                    .filter(entry =>
                        attribute ? entry[attribute] === id && entry.min_p !== null : entry.min_p !== null
                    )
                    .map(entry => entry.min_p)
            );
            return (isNaN(aMinP) ? Infinity : aMinP) - (isNaN(bMinP) ? Infinity : bMinP);
        });

        return Object.fromEntries(groupedData);
    },

    handleColocGroupClick(displaySnp, variantType) {
        this.displayFilters.candidateSnp = displaySnp;
        const isColoc = variantType === constants.colors.dataTypes.common;
        const headerId = isColoc ? "coloc-table" : "rare-table";
        this.showTables.coloc = isColoc;
        this.showTables.rare = !isColoc;

        const scrollToHeader = () => {
            const headerElement = document.getElementById(headerId);
            if (headerElement && headerElement.offsetParent !== null) {
                const y = headerElement.getBoundingClientRect().top + window.pageYOffset - 80;
                window.scrollTo(0, y);
                return true;
            }
            return false;
        };

        this.$nextTick(() => scrollToHeader());
    },

    addColorForSNPs(entries) {
        return entries.map(entry => {
            const hash = [...entry.display_snp].reduce(
                (hash, char) => (hash * 31 + char.charCodeAt(0)) % constants.tableColors.length,
                0
            );
            return {
                ...entry,
                color: constants.tableColors[hash],
            };
        });
    },

    graphColor() {
        if (constants.darkMode) return constants.colors.textColors.dark;
        else return constants.colors.textColors.light;
    },

    getVariantTypeColor(variantType) {
        return this.variantTypes[variantType] || "#000000";
    },

    getResultColorType(type) {
        if (type === "coloc") return constants.colors.dataTypes.common;
        else if (type === "rare") return constants.colors.dataTypes.rare;
        else return constants.colors.dataTypes.common;
    },

    selectedTraitCategories(graphOptions) {
        const selectedCategories = new Set(
            Object.entries(graphOptions.categories).flatMap(([key, value]) => {
                if (typeof value === "object" && value !== null) {
                    return Object.entries(value)
                        .filter(([, v]) => v === true)
                        .map(([k]) => k);
                }
                if (value === true) return [key];
                return [];
            })
        );
        return selectedCategories;
    },

    getOrderedTraits(groupedData, excludeTrait) {
        let allTraits = Object.values(groupedData).flatMap(c => c.map(c => c.trait_name));

        let frequency = {};
        allTraits.forEach(item => {
            frequency[item] = (frequency[item] || 0) + 1;
        });

        let uniqueTraits = [...new Set(allTraits)];
        uniqueTraits.sort((a, b) => frequency[b] - frequency[a]);

        if (excludeTrait) uniqueTraits = uniqueTraits.filter(t => t !== excludeTrait);

        return uniqueTraits;
    },

    getTraitListHTML(content) {
        const uniqueTraits = [
            ...new Set(content.map(s => (s.trait_name.length > 70 ? `${s.trait_name.slice(0, 70)}...` : s.trait_name))),
        ];
        const traitNames = uniqueTraits.slice(0, 9).join("<br>");
        let tooltipContent = `<b>SNP: ${content[0].display_snp}</b><br>${traitNames}`;
        if (uniqueTraits.length > 10) {
            tooltipContent += `<br>${uniqueTraits.length - 10} more...`;
        }
        return tooltipContent;
    },

    initGraph(chartContainer, graphData, errorMessage, graphFunction) {
        if (errorMessage) {
            chartContainer.innerHTML = '<div class="notification is-danger is-light mt-4">' + errorMessage + "</div>";
            return;
        } else if (!graphData) {
            chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
            return;
        }

        // listen to resize events to redraw the graph
        window.addEventListener("resize", () => {
            clearTimeout(this.resizeTimer);
            this.resizeTimer = setTimeout(() => {
                graphFunction();
            }, 250);
        });

        graphFunction();
    },

    getTooltip(content, event) {
        d3.selectAll(".tooltip").remove();
        // If the tooltip would overflow the right edge, expand left
        // We need to allow the DOM to update so we can measure the tooltip, hence the setTimeout
        const tooltip = d3
            .select("body")
            .append("div")
            .attr("class", "tooltip")
            .style("display", "block")
            .style("position", "absolute")
            .style("background-color", "white")
            .style("opacity", "0.90")
            .style("padding", "5px")
            .style("border", "1px solid black")
            .style("border-radius", "5px")
            .style("visibility", "hidden")
            .style("z-index", "10")
            .html(content);

        setTimeout(() => {
            const tooltipNode = tooltip.node();
            const tooltipWidth = tooltipNode.offsetWidth;
            const windowWidth = window.innerWidth;
            let left = event.pageX + 10;

            if (left + tooltipWidth > windowWidth) {
                left = event.pageX - tooltipWidth - 10;
            }

            tooltip
                .style("left", `${left}px`)
                .style("top", `${event.pageY - 10}px`)
                .style("visibility", "visible");
        }, 0);
    },

    colocByPositionGraph() {
        const self = this;
        const genesInRegion = this.data.genes_in_region ? this.data.genes_in_region : this.data.gene.genes_in_region;
        const textColor = graphTransformations.graphColor();

        const container = document.getElementById("coloc-by-position-chart");
        container.innerHTML = "";

        const graphConstants = {
            width: container.clientWidth,
            outerMargin: { top: 90, right: 60, bottom: 150, left: 60 },
            geneTrackMargin: { top: 40, height: 20 },
        };
        const innerWidth = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;

        const snpGroups = Object.entries(this.filteredData.groupedResults).map(([snp, studies]) => {
            const variant = this.data.variants.find(variant => variant.display_snp === snp);
            return {
                snp,
                studies,
                variant: variant,
                bp: variant ? variant.bp / 1000000 : 0,
            };
        });

        const xScale = d3.scaleLinear().domain([this.minMbp, this.maxMbp]).nice().range([0, innerWidth]);

        // Prepare SNP groups with position data first
        const { positionedGroups, numLevels } = assignCircleLevels(snpGroups, xScale);
        const dynamicHeight = Math.max(numLevels * 16, 350);

        const innerHeight = dynamicHeight - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;
        const totalWidth = graphConstants.width;
        const totalHeight = dynamicHeight;

        // Create a container div to hold both Canvas and SVG
        const containerDiv = d3
            .select("#coloc-by-position-chart")
            .append("div")
            .style("position", "relative")
            .style("width", totalWidth + "px")
            .style("height", totalHeight + "px");

        // Create Canvas container for interactive circles
        const canvas = containerDiv
            .append("canvas")
            .attr("width", totalWidth)
            .attr("height", totalHeight)
            .style("display", "block")
            .style("position", "relative")
            .style("z-index", "2")
            .node();

        const ctx = canvas.getContext("2d");

        // Create SVG container for static elements (axes, labels, legend)
        const svg = containerDiv
            .append("svg")
            .attr("width", totalWidth)
            .attr("height", totalHeight)
            .attr("viewBox", `0 0 ${totalWidth} ${totalHeight}`)
            .style("position", "absolute")
            .style("top", "0")
            .style("left", "0")
            .style("z-index", "1")
            .style("pointer-events", "none"); // Make SVG non-interactive

        // Create separate interactive SVG layer for gene rectangles (above canvas)
        const interactiveSvg = containerDiv
            .append("svg")
            .attr("width", totalWidth)
            .attr("height", totalHeight)
            .attr("viewBox", `0 0 ${totalWidth} ${totalHeight}`)
            .style("position", "absolute")
            .style("top", "0")
            .style("left", "0")
            .style("z-index", "3")
            .style("pointer-events", "none"); // Only gene rectangles will have pointer events

        // Create main plot group for SVG
        const plotGroup = svg
            .append("g")
            .attr("transform", `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

        // Draw the x-axis to SVG
        const xAxisGroup = plotGroup
            .append("g")
            .attr("class", "x-axis")
            .attr("transform", `translate(0,${innerHeight})`)
            .call(d3.axisBottom(xScale));
        xAxisGroup
            .selectAll("text")
            .style("text-anchor", "end")
            .style("fill", textColor)
            .attr("dx", "-.8em")
            .attr("dy", ".15em")
            .attr("transform", "rotate(-65)");
        xAxisGroup.selectAll("line, path").style("stroke", textColor);

        // Function to detect overlaps and assign vertical levels to SNP circles
        function assignCircleLevels(snpGroups, xScale) {
            let levels = [];
            snpGroups.forEach(group => {
                let level = 0;
                const baseRadius = 2;
                const radius =
                    group.studies.length > 0
                        ? Math.min(baseRadius + Math.sqrt(group.studies.length) * 1.7, 10)
                        : baseRadius;
                const positionPx = xScale(group.bp);

                while (true) {
                    const hasOverlap = levels[level]?.some(existing => {
                        const existingRadius =
                            existing.studies.length > 0
                                ? Math.min(baseRadius + Math.sqrt(existing.studies.length) * 1.7, 10)
                                : baseRadius;
                        const existingPx = xScale(existing.bp);
                        const distancePx = Math.abs(existingPx - positionPx);
                        return distancePx < radius + existingRadius;
                    });

                    if (!hasOverlap) {
                        if (!levels[level]) levels[level] = [];
                        levels[level].push({ ...group, level });
                        break;
                    }
                    level++;
                }
            });
            return { positionedGroups: levels.flat(), numLevels: levels.length };
        }

        // Function to detect overlaps and assign vertical levels to gene rectangles
        function assignGeneLevels(genes) {
            let levels = [];
            genes.forEach(gene => {
                let level = 0;
                while (true) {
                    const hasOverlap = levels[level]?.some(
                        existingGene => !(gene.stop < existingGene.start || gene.start > existingGene.stop)
                    );

                    if (!hasOverlap) {
                        if (!levels[level]) levels[level] = [];
                        levels[level].push(gene);
                        gene.level = level;
                        break;
                    }
                    level++;
                }
            });
            return levels;
        }

        function renderLegend() {
            const legendWidth = 120;
            const legendHeight = 20;
            const legendX = graphConstants.outerMargin.left + innerWidth - legendWidth;
            const legendY = graphConstants.outerMargin.top - 10;

            ctx.save();
            ctx.translate(legendX, legendY);

            // Draw legend border
            ctx.strokeStyle = "#bbb";
            ctx.lineWidth = 1;
            ctx.strokeRect(-8, -10, legendWidth, legendHeight);

            // Common variant legend item
            ctx.beginPath();
            ctx.arc(0, 0, 5, 0, 2 * Math.PI);
            ctx.fillStyle = constants.colors.dataTypes.common;
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.fillStyle = textColor;
            ctx.font = "12px Arial";
            ctx.textAlign = "left";
            ctx.fillText("Common", 10, 4);

            // Rare variant legend item
            ctx.beginPath();
            ctx.arc(70, 0, 5, 0, 2 * Math.PI);
            ctx.fillStyle = constants.colors.dataTypes.rare;
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.stroke();

            ctx.fillStyle = textColor;
            ctx.fillText("Rare", 80, 4);

            ctx.restore();

            // X-axis label
            plotGroup
                .append("text")
                .attr("x", innerWidth / 2)
                .attr("y", innerHeight + graphConstants.outerMargin.bottom - 10)
                .style("text-anchor", "middle")
                .style("fill", textColor)
                .text("Genomic Position (MB)");

            // Reset button (needs to be interactive, so put in interactive SVG layer above canvas)
            // Clear any existing reset button first
            interactivePlotGroup.selectAll(".reset-button-group").remove();

            if (
                self.displayFilters.gene !== null ||
                self.displayFilters.traitName !== null ||
                self.displayFilters.candidateSnp !== null
            ) {
                const btnX = innerWidth / 2 + 90;
                const btnY = innerHeight + graphConstants.outerMargin.bottom - 25;
                const btnWidth = 90;
                const btnHeight = 22;
                // Use adaptive colors for button background
                const buttonBgColor = constants.darkMode ? "#2d2d2d" : "#ffffff";
                const buttonBorderColor = constants.darkMode ? "#666666" : "#b5b5b5";

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

        // Prepare circle data for Canvas rendering
        const canvasCircles = positionedGroups.map(d => {
            const baseRadius = 2;
            const radius =
                d.studies.length > 0 ? Math.min(baseRadius + Math.sqrt(d.studies.length) * 1.5, 10) : baseRadius;
            const x = xScale(d.bp);
            const y = innerHeight - d.level * (radius * 1.8) - 10;

            return {
                ...d,
                x,
                y,
                radius,
                fillColor: graphTransformations.getResultColorType(d.studies[0].type),
            };
        });

        let highlightedCircle = null;

        // Canvas rendering functions
        const renderCanvas = () => {
            // Clear canvas
            ctx.clearRect(0, 0, totalWidth, totalHeight);
        };

        const renderCircles = () => {
            ctx.save();
            ctx.translate(graphConstants.outerMargin.left, graphConstants.outerMargin.top);

            canvasCircles.forEach(circle => {
                const isHighlighted = highlightedCircle && circle.snp === highlightedCircle.snp;
                const radius = isHighlighted ? circle.radius + 8 : circle.radius;

                ctx.beginPath();
                ctx.arc(circle.x, circle.y, radius, 0, 2 * Math.PI);
                ctx.fillStyle = isHighlighted ? constants.colors.dataTypes.highlighted : circle.fillColor;
                ctx.fill();
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 1.5;
                ctx.stroke();
            });

            ctx.restore();
        };

        // Mouse interaction handling
        const getMousePos = e => {
            const rect = canvas.getBoundingClientRect();
            return {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top,
            };
        };

        const getCircleAt = (x, y) => {
            const plotX = x - graphConstants.outerMargin.left;
            const plotY = y - graphConstants.outerMargin.top;

            for (let i = canvasCircles.length - 1; i >= 0; i--) {
                const circle = canvasCircles[i];
                const distance = Math.sqrt((plotX - circle.x) ** 2 + (plotY - circle.y) ** 2);
                if (distance <= circle.radius + 5) {
                    return circle;
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
                if (highlightedCircle !== circle) {
                    highlightedCircle = circle;
                    renderCanvas();
                    renderCircles();
                    renderLegend();

                    const tooltipContent = graphTransformations.getTraitListHTML(circle.studies);
                    graphTransformations.getTooltip(tooltipContent, e);
                }
            } else {
                canvas.style.cursor = "default";
                if (highlightedCircle) {
                    highlightedCircle = null;
                    renderCanvas();
                    renderCircles();
                    renderLegend();
                    d3.selectAll(".tooltip").remove();
                }
            }
        });

        canvas.addEventListener("click", e => {
            const mousePos = getMousePos(e);
            const circle = getCircleAt(mousePos.x, mousePos.y);

            if (circle) {
                const firstStudy = circle.studies && circle.studies.length > 0 ? circle.studies[0] : null;
                const variantType =
                    firstStudy && firstStudy.coloc_group_id
                        ? constants.colors.dataTypes.common
                        : constants.colors.dataTypes.rare;
                graphTransformations.handleColocGroupClick.bind(this)(circle.snp, variantType);
                d3.selectAll(".tooltip").remove();
            }
        });

        const geneTrackY = innerHeight + graphConstants.geneTrackMargin.top;
        const genes = genesInRegion.filter(gene => gene.minMbp <= this.maxMbp && gene.maxMbp >= this.minMbp);

        assignGeneLevels(genes);
        // Gene rectangles need to be interactive, so put them in a separate interactive SVG layer above canvas
        const interactivePlotGroup = interactiveSvg
            .append("g")
            .attr("transform", `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`)
            .style("pointer-events", "none"); // Group level is none, but rectangles will have all
        const geneGroup = interactivePlotGroup.append("g").attr("class", "gene-track").style("pointer-events", "all");

        geneGroup
            .selectAll(".gene-rect")
            .data(genes)
            .enter()
            .append("rect")
            .attr("class", "gene-rect")
            .attr("x", d => xScale(d.start / 1000000))
            .attr("y", d => geneTrackY + d.level * (graphConstants.geneTrackMargin.height + 5))
            .attr("width", d => xScale(d.stop / 1000000) - xScale(d.start / 1000000))
            .attr("height", graphConstants.geneTrackMargin.height)
            .attr("fill", (d, i) => constants.colors.palette[i % constants.colors.palette.length])
            .attr("stroke", d => (d.focus ? textColor : null))
            .attr("stroke-width", 3)
            .attr("opacity", 0.7)
            .on("mouseover", (event, d) => {
                graphTransformations.getTooltip(`Gene: ${d.gene}`, event);
                d3.select(event.target).style("cursor", "pointer").style("stroke", "#808080").style("stroke-width", 3);
            })
            .on("click", (event, d) => {
                self.displayFilters.gene = d.gene;
            })
            .on("mouseout", event => {
                d3.selectAll(".tooltip").remove();
                d3.select(event.target)
                    .style("stroke", d => (d.focus ? textColor : null))
                    .style("stroke-width", d => (d.focus ? 3 : null));
            });

        // Initial render
        renderCanvas();
        renderCircles();
        renderLegend();
    },
};
