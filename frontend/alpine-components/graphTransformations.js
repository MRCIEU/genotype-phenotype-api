import constants from "./constants.js";
import * as d3 from "d3";
import graphTransformations from "./graphTransformations.js";

export default {
    groupBySnp(data, type, id, displayFilters) {
        id = parseInt(id);
        let attribute = null;
        if (type === "trait") {
            attribute = "trait_id";
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

    traitByPositionGraph() {
        const genesInRegion = this.data.genes_in_region ? this.data.genes_in_region : this.data.gene.genes_in_region;

        const container = document.getElementById("trait-by-position-chart");
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

        const svg = d3
            .select("#trait-by-position-chart")
            .append("svg")
            .attr("viewBox", `0 0 ${graphConstants.width} ${dynamicHeight}`)
            .attr("preserveAspectRatio", "xMidYMid meet")
            .style("width", "100%")
            .style("height", "100%")
            .append("g")
            .attr("transform", `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

        // Draw the x-axis
        svg.append("g")
            .attr("class", "x-axis")
            .attr("transform", `translate(0,${innerHeight})`)
            .call(d3.axisBottom(xScale))
            .selectAll("text")
            .style("text-anchor", "end")
            .attr("dx", "-.8em")
            .attr("dy", ".15em")
            .attr("transform", "rotate(-65)");

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
            const legend = svg
                .append("g")
                .attr("class", "legend")
                .attr("transform", `translate(${innerWidth - legendWidth}, -${graphConstants.outerMargin.top - 10})`);

            legend
                .append("rect")
                .attr("x", -8)
                .attr("y", -10)
                .attr("width", legendWidth)
                .attr("height", legendHeight)
                .attr("fill", "none")
                .attr("stroke", "#bbb")
                .attr("stroke-width", 1);

            // Common variant legend item
            legend
                .append("circle")
                .attr("cx", 0)
                .attr("cy", 0)
                .attr("r", 5)
                .attr("fill", constants.colors.dataTypes.common)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);

            legend.append("text").attr("x", 10).attr("y", 4).style("font-size", "12px").text("Common");

            // Rare variant legend item
            legend
                .append("circle")
                .attr("cx", 70)
                .attr("cy", 0)
                .attr("r", 5)
                .attr("fill", constants.colors.dataTypes.rare)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);

            legend.append("text").attr("x", 80).attr("y", 4).style("font-size", "12px").text("Rare");

            svg.append("text")
                .attr("x", innerWidth / 2)
                .attr("y", innerHeight + graphConstants.outerMargin.bottom - 10)
                .style("text-anchor", "middle")
                .text("Genomic Position (MB)");

            if (
                this.displayFilters.gene !== null ||
                this.displayFilters.traitName !== null ||
                this.displayFilters.candidateSnp !== null
            ) {
                const btnX = innerWidth / 2 + 90;
                const btnY = innerHeight + graphConstants.outerMargin.bottom - 25;
                const btnWidth = 90;
                const btnHeight = 22;
                svg.append("rect")
                    .attr("x", btnX)
                    .attr("y", btnY)
                    .attr("width", btnWidth)
                    .attr("height", btnHeight)
                    .attr("rx", 6)
                    .attr("fill", "white")
                    .attr("stroke", "#b5b5b5")
                    .style("cursor", "pointer")
                    .on("click", () => this.removeDisplayFilters());
                svg.append("text")
                    .attr("x", btnX + btnWidth / 2)
                    .attr("y", btnY + btnHeight / 2 + 3)
                    .attr("text-anchor", "middle")
                    .attr("alignment-baseline", "middle")
                    .attr("font-size", 13)
                    .attr("fill", "#363636")
                    .attr("class", "button is-small")
                    .style("cursor", "pointer")
                    .text("Reset Display")
                    .on("click", () => this.removeDisplayFilters());
            }
        }

        // Add circles for each SNP group with adjusted vertical positions
        svg.selectAll(".snp-circle")
            .data(positionedGroups)
            .enter()
            .append("circle")
            .attr("class", "snp-circle")
            .attr("cx", d => xScale(d.bp))
            .attr("cy", d => {
                const baseRadius = 2;
                const radius =
                    d.studies.length > 0 ? Math.min(baseRadius + Math.sqrt(d.studies.length) * 1.5, 10) : baseRadius;
                return innerHeight - d.level * (radius * 1.8) - 10;
            })
            .attr("r", d => {
                const baseRadius = 2;
                return d.studies.length > 0 ? Math.min(baseRadius + Math.sqrt(d.studies.length) * 1.5, 10) : baseRadius;
            })
            .attr("fill", d => graphTransformations.getResultColorType(d.studies[0].type))
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5)
            .style("opacity", 0.9)
            .on("mouseover", function (event, d) {
                d3.select(this).style("cursor", "pointer");
                d3.select(this)
                    .transition()
                    .duration("100")
                    .attr("fill", constants.colors.dataTypes.highlighted)
                    .attr("r", function () {
                        const baseRadius = 2;
                        return (
                            (d.studies.length > 0
                                ? Math.min(baseRadius + Math.sqrt(d.studies.length) * 1.5, 10)
                                : baseRadius) + 8
                        );
                    });
                const tooltipContent = graphTransformations.getTraitListHTML(d.studies);
                graphTransformations.getTooltip(tooltipContent, event);
            })
            .on("click", (_, d) => {
                const firstStudy = d.studies && d.studies.length > 0 ? d.studies[0] : null;
                const variantType =
                    firstStudy && firstStudy.coloc_group_id
                        ? constants.colors.dataTypes.common
                        : constants.colors.dataTypes.rare;
                graphTransformations.handleColocGroupClick.bind(this)(d.snp, variantType);
                d3.selectAll(".tooltip").remove();
            })
            .on("mouseout", function (_, d) {
                d3.select(this)
                    .transition()
                    .duration("200")
                    .attr("fill", graphTransformations.getResultColorType(d.studies[0].type))
                    .attr("r", function () {
                        const baseRadius = 2;
                        return d.studies.length > 0
                            ? Math.min(baseRadius + Math.sqrt(d.studies.length) * 1.5, 10)
                            : baseRadius;
                    });
                d3.selectAll(".tooltip").remove();
            });

        const geneTrackY = innerHeight + graphConstants.geneTrackMargin.top;
        const genes = genesInRegion.filter(gene => gene.minMbp <= this.maxMbp && gene.maxMbp >= this.minMbp);

        assignGeneLevels(genes);
        const geneGroup = svg.append("g").attr("class", "gene-track");

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
            .attr("stroke", d => (d.focus ? "black" : null))
            .attr("stroke-width", 3)
            .attr("opacity", 0.7)
            .on("mouseover", (event, d) => {
                graphTransformations.getTooltip(`Gene: ${d.gene}`, event);
                d3.select(event.target).style("cursor", "pointer").style("stroke", "#808080").style("stroke-width", 3);
            })
            .on("click", (event, d) => {
                this.displayFilters.gene = d.gene;
            })
            .on("mouseout", event => {
                d3.selectAll(".tooltip").remove();
                d3.select(event.target)
                    .style("stroke", d => (d.focus ? "black" : null))
                    .style("stroke-width", d => (d.focus ? 3 : null));
            });

        renderLegend.bind(this)();
    },
};
