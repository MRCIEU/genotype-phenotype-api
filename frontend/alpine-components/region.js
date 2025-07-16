import * as d3 from 'd3';
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
            traitName: null
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

            this.data.colocs = this.data.colocs.map(coloc => {
                const variantType = this.data.variants.find(variant => variant.SNP === coloc.candidate_snp)
                return {
                    ...coloc,
                    type: 'coloc',
                    mbp : coloc.bp / 1000000,
                    variantType: variantType ? variantType.Consequence.split(",")[0] : null,
                }
            })
            this.data.colocs = graphTransformations.addColorForSNPs(this.data.colocs)

            this.data.rare_results = this.data.rare_results.map(rareResult => {
                const variantType = this.data.variants.find(variant => variant.SNP === rareResult.candidate_snp)
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

            this.filteredData.colocs = this.data.colocs.filter(coloc => {
                let graphOptionFilters = (coloc.min_p <= graphOptions.pValue &&
                   coloc.posterior_prob >= graphOptions.coloc &&
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

            this.filteredData.groupedRare = graphTransformations.groupByCandidateSnp(this.filteredData.rare, null, null, this.displayFilters.traitName)
            this.filteredData.groupedColocs = graphTransformations.groupByCandidateSnp(this.filteredData.colocs, null, null, this.displayFilters.traitName)
            this.filteredData.groupedResults = {...this.filteredData.groupedColocs, ...this.filteredData.groupedRare}

            this.traitSearch.orderedTraits = graphTransformations.getOrderedTraits(this.filteredData.groupedResults)
        },

        get regionName() {
            if (this.data === null) return
            return this.data.region.ancestry + ' ' + this.data.region.chr + ':' + this.data.region.start + '-' + this.data.region.stop
        },

        getTraitsToFilterBy() {
            if (this.traitSearch.orderedTraits === null) return []
            return this.traitSearch.orderedTraits.filter(text =>
                !this.traitSearch.text || text.toLowerCase().includes(this.traitSearch.text.toLowerCase())
            )
        },

        removeDisplayFilters() {
            this.displayFilters = {
                traitName: null
            }
            this.traitSearch.text = ''
        },

        filterByTrait(trait) {
            if (trait !== null) {
                this.displayFilters.traitName = trait
            } 
        },

        async downloadData() {
            this.downloadClicked = true;
            await downloads.downloadDataToZip(this.data, this.data.gene.gene);
        },

        get getDataForColocTable() {
            if (!this.filteredData.colocs || this.filteredData.colocs.length === 0) return []
            return stringify(Object.fromEntries(Object.entries(this.filteredData.groupedColocs).slice(0, constants.maxSNPGroupsToDisplay)))
        },

        get getDataForRareTable() {
            if (!this.filteredData.rare || this.filteredData.rare.length === 0) return []
            return stringify(Object.fromEntries(Object.entries(this.filteredData.groupedRare).slice(0, constants.maxSNPGroupsToDisplay)))
        },

        initTraitByPositionGraph() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("trait-by-position-chart");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () => this.getTraitByPositionGraph())
        },

        getTraitByPositionGraph() {
            graphTransformations.traitByPositionGraph(this.minMbp, this.maxMbp, this.filteredData, this.data.genes_in_region)
        },

        getRegionGraph() {
            const chartElement = document.getElementById("region-chart");
            chartElement.innerHTML = ''

            const chartContainer = d3.select("#region-chart");
            chartContainer.select("svg").remove()
            let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

            const graphConstants = {
                width: graphWidth, 
                height: Math.floor(graphWidth / 2),
                outerMargin: {
                    top: 50,
                    right: 30,
                    bottom: 80,
                    left: 60,
                },
                geneTrackMargin: {
                    top: 40,
                    height: 20
                }
            }

            let self = this
            const innerWidth = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
            const innerHeight = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

            const svg = chartContainer
                .append("svg")
                .attr('width', graphConstants.width)
                .attr('height', graphConstants.height + graphConstants.geneTrackMargin.top)
                .append('g')
                .attr('transform', `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

            const xScale = d3.scaleLinear()
                .domain([this.minMbp, this.maxMbp])
                .nice()
                .range([0, innerWidth]);

            // Calculate the maximum number of studies for any SNP
            const maxStudiesPerSnp = Math.max(...Object.values(this.data.groupedColocs)
                .map(group => group.length));

            const yScale = d3.scaleLinear()
                    .domain([0, maxStudiesPerSnp - 1])    // -1 because we're using 0-based indexing
                    .range([innerHeight, 0])
                    .nice();

            // Draw the axes
            svg.append("g")
                .attr("class", "x-axis")
                .call(d3.axisBottom(xScale))
                .attr("transform", `translate(0,${innerHeight})`)
                .selectAll("text")    
                .style("text-anchor", "end")
                .attr("dx", "-0.8em")
                .attr("dy", "0.15em")
                .attr("transform", "rotate(-65)")

            svg.append("g")
                .attr("class", "y-axis")
                .call(d3.axisLeft(yScale)
                    .ticks(maxStudiesPerSnp)
                    .tickFormat(d => d + 1))    // Changed from empty string to show numbers, add 1 to make it 1-based
                
            //Labels for x and y axis
            svg.append("text")
                .attr("font-size", "14px")
                .attr("transform", "rotate (-90)")
                .attr("x", -graphConstants.height / 2)
                .attr("y", graphConstants.outerMargin.left * -1 + 20)
                .text("Number of Colocalizing Studies");

            svg.append("text")
                .attr("font-size", "14px")
                .attr("x", graphConstants.width/2 - graphConstants.outerMargin.left)
                .attr("y", graphConstants.height + graphConstants.geneTrackMargin.height - graphConstants.outerMargin.bottom + 30)
                .text("Genomic Position (MB)");

            // Draw horizontal grid lines for each study position
            const studyPositions = d3.range(maxStudiesPerSnp);
            studyPositions.forEach(index => {
                const yPos = yScale(index);
                svg.append("line")
                    .attr("x1", 0)
                    .attr("x2", innerWidth)
                    .attr("y1", yPos)
                    .attr("y2", yPos)
                    .attr("stroke", "lightgray")
                    .attr("stroke-width", 1)
                    .attr("stroke-dasharray", "4 2");
            });

            // Add clip path and plot group
            svg.append("defs").append("clipPath")
                    .attr("id", "clip")
                    .append("rect")
                    .attr("width", innerWidth)
                    .attr("height", innerHeight);

            const plotGroup = svg.append("g")
                    .attr("clip-path", "url(#clip)");

            // Create brush
            const brush = d3.brushX()
                    .extent([[0, 0], [innerWidth, innerHeight]])
                    .on("end", function (event) {
                            if (!event.selection) return;
                            
                            const extent = event.selection.map(xScale.invert);
                            
                            self.graphicalMbRange = {
                                    start: extent[0],
                                    end: extent[1]
                            };
                            
                            // Update x scale domain to zoom
                            xScale.domain(extent);
                            
                            // Update x-axis
                            svg.select(".x-axis")
                                    .transition()
                                    .duration(750)
                                    .call(d3.axisBottom(xScale))
                                    .selectAll("text")    
                                    .style("text-anchor", "end")
                                    .attr("dx", "-.8em")
                                    .attr("dy", ".15em")
                                    .attr("transform", "rotate(-65)");
                            
                            // Update lines
                            plotGroup.selectAll(".graph-line")
                                    .transition()
                                    .duration(750)
                                    .attr("x1", d => xScale(d.bp))
                                    .attr("x2", d => xScale(d.bp));
                            
                            // Update gene rectangles
                            svg.selectAll(".gene-rect")
                                    .transition()
                                    .duration(750)
                                    .attr("x", d => xScale(d.min_bp / 1000000))
                                    .attr("width", d => xScale(d.max_bp / 1000000) - xScale(d.min_bp / 1000000));
                            
                            // Update gene labels
                            svg.selectAll(".gene-label")
                                    .transition()
                                    .duration(750)
                                    .attr("x", d => xScale((d.min_bp + (d.max_bp - d.min_bp)/2) / 1000000))
                                    .attr("transform", function(d) {
                                            const x = xScale((d.min_bp + (d.max_bp - d.min_bp)/2) / 1000000);
                                            return `rotate(45, ${x}, ${geneTrackHeight + 12})`;
                                    });

                            // Clear the brush selection
                            svg.select(".brush").call(brush.move, null);
                    });

            // Add brush to svg
            svg.append("g")
                    .attr("class", "brush")
                    .call(brush);

            // Create a container for tooltips outside of the SVG
            const tooltipContainer = d3.select('#region-chart')
                    .append('div')
                    .attr('class', 'tooltip')
                    .style('position', 'absolute')
                    .style('visibility', 'hidden')
                    .style('background-color', 'white')
                    .style('padding', '5px')
                    .style('border', '1px solid black')
                    .style('border-radius', '5px');

            const lines = Object.keys(this.data.groupedColocs).map(snp => {
                const groups = this.data.groupedColocs[snp];
                    const bp = snp.match(/\d+:(\d+)_/)[1] / 1000000;
                    return {
                        bp: bp,
                        x1: xScale(bp),
                        y1: yScale(0),
                        x2: xScale(bp),
                        y2: yScale(groups.length),
                    }
            })

            plotGroup.selectAll(".graph-line")
                    .data(lines)
                    .enter()
                    .append("line")
                    .attr("class", "graph-line")
                    .attr("x1", d => d.x1)
                    .attr("y1", d => d.y1)
                    .attr("x2", d => d.x2)
                    .attr("y2", d => d.y2)
                    .style("stroke", "black")
                    .style("stroke-width", 4)
                    .style("stroke-linecap", "round");

            // Calculate gene track height and position
            const geneTrackY = innerHeight + graphConstants.geneTrackMargin.top; // Position below x-axis
            const geneHeight = 20; // Height of each gene rectangle

            // Create gene rectangles
            const genes = this.data.genes.filter(gene =>
                gene.minMbp <= this.maxMbp && gene.maxMbp >= this.minMbp
            );
            
            // Function to detect overlaps and assign levels
            function assignLevels(genes) {
                let levels = [];
                genes.forEach(gene => {
                    let level = 0;
                    while (true) {
                        // Check if current level has overlap
                        const hasOverlap = levels[level]?.some(existingGene => 
                            !(gene.max_bp < existingGene.min_bp || gene.min_bp > existingGene.max_bp)
                        );
                        
                        if (!hasOverlap) {
                            // No overlap found, assign this level
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

            const geneLevels = assignLevels(genes);
            const totalLevels = geneLevels.length;

            // Add gene rectangles with vertical stacking
            const geneGroup = svg.append("g")
                    .attr("class", "gene-track")
                    .attr("transform", `translate(0, ${geneTrackY})`);

            geneGroup.selectAll(".gene-rect")
                    .data(genes)
                    .enter()
                    .append("rect")
                    .attr("class", "gene-rect")
                    .attr("x", d => xScale(d.min_bp / 1000000))
                    .attr("y", d => d.level * (graphConstants.geneTrackMargin.height + 5)) // Add 5px spacing between levels
                    .attr("width", d => xScale(d.max_bp / 1000000) - xScale(d.min_bp / 1000000))
                    .attr("height", graphConstants.geneTrackMargin.height)
                    .attr("fill", (d, i) => constants.colors.palette[i % constants.colors.palette.length])
                    .attr("opacity", 0.7)
                    .on('mouseover', function(event, d) {
                            d3.select(this)
                                    .style('opacity', 1)
                                    .attr('r', 5);
                                    
                            tooltipContainer.html(`Gene: ${d.symbol}`)
                                .style('visibility', 'visible')
                                .style('display', 'flex')
                                .style('left', `${event.pageX + 10}px`)
                                .style('top', `${event.pageY - 10}px`)
                    })
                    .on('mouseout', function() {
                            d3.select(this)
                                    .style('opacity', 0.7)
                                    .attr('r', 3);
                                    
                            tooltipContainer.style('visibility', 'hidden')
                    });

            // Update SVG height to accommodate stacked genes
            const newHeight = graphConstants.height + (totalLevels * (geneHeight + 5)) + 50;
            svg.attr("height", newHeight);

            // Add reset zoom text after creating the SVG
            svg.append("text")
                .attr("class", "reset-zoom")
                .attr("x", innerWidth - 80)    // Position near top-right
                .attr("y", -20)                            // Position above the plot
                .text("Reset Zoom")
                .style("cursor", "pointer")     // Show pointer cursor on hover
                .style("fill", "black")                // Make it look clickable
                .on("click", function() {
                    // Reset x scale to original domain
                    xScale.domain([self.minMbp, self.maxMbp]);
                    
                    // // Reset currentMbRange
                    self.graphicalMbRange = {
                            start: self.minMbp,
                            end: self.maxMbp
                    };
                    
                    // Update x-axis with transition
                    svg.select(".x-axis")
                        .transition()
                        .duration(750)
                        .call(d3.axisBottom(xScale))
                        .selectAll("text")    
                        .style("text-anchor", "end")
                        .attr("dx", "-0.8em")
                        .attr("dy", "0.15em")
                        .attr("transform", "rotate(-65)");
                    
                    // Update lines
                    plotGroup.selectAll(".graph-line")
                        .transition()
                        .duration(750)
                        .attr("x1", d => xScale(d.bp))
                        .attr("x2", d => xScale(d.bp));
                    
                    // Update gene rectangles
                    svg.selectAll(".gene-rect")
                        .transition()
                        .duration(750)
                        .attr("x", d => xScale(d.min_bp / 1000000))
                        .attr("width", d => xScale(d.max_bp / 1000000) - xScale(d.min_bp / 1000000));
                    
                    // Update gene labels
                    svg.selectAll(".gene-label")
                        .transition()
                        .duration(750)
                        .attr("x", d => xScale((d.min_bp + (d.max_bp - d.min_bp)/2) / 1000000))
                        .attr("transform", function(d) {
                            const x = xScale((d.min_bp + (d.max_bp - d.min_bp)/2) / 1000000);
                            return `rotate(45, ${x}, ${geneTrackHeight + 12})`;
                        });
                });
        },
    }
}