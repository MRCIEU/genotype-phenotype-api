import constants from './constants.js'
import * as d3 from "d3";
import graphTransformations from './graphTransformations.js';

export default {
    groupByCandidateSnp(data, type, id, traitFilter) {
        id = parseInt(id)
        let attribute = null
        if (type === 'trait') {
            attribute = 'trait_id'
        }
        else if (type === 'gene') {
            attribute = 'gene_id'
        }

        let groupedData = Object.groupBy(data, ({ candidate_snp }) => candidate_snp);

        groupedData = Object.entries(groupedData).filter(([_, group]) => {
            const hasId = attribute ? group.some(entry => parseInt(entry[attribute]) === id) : true
            const hasTrait = traitFilter ? group.some(entry => entry.trait_name === traitFilter) : true
            const moreThanOneTrait = group.length > 1
            return hasId && hasTrait && moreThanOneTrait
        });

        groupedData.sort((a, b) => {
            const aMinP = Math.min(...a[1]
                .filter(entry => attribute ? entry[attribute] === id && entry.min_p !== null : entry.min_p !== null)
                .map(entry => entry.min_p)
            );
            const bMinP = Math.min(...b[1]
                .filter(entry => attribute ? entry[attribute] === id && entry.min_p !== null : entry.min_p !== null)
                .map(entry => entry.min_p)
            );
            return (isNaN(aMinP) ? Infinity : aMinP) - (isNaN(bMinP) ? Infinity : bMinP);
        });

        return Object.fromEntries(groupedData)
    },

    addColorForSNPs(entries) {
        return entries.map(entry => {
            const hash = [...entry.candidate_snp].reduce((hash, char) =>
                (hash * 31 + char.charCodeAt(0)) % constants.tableColors.length, 0
            )
            return {
                ...entry,
                color: constants.tableColors[hash]
            }
        })
    },

    getVariantTypeColor(variantType) {
        return this.variantTypes[variantType] || '#000000';
    },


    getResultColorType(type) {
        if (type === 'coloc') return constants.colors.dataTypes.common
        else if (type === 'rare') return constants.colors.dataTypes.rare
        else return constants.colors.dataTypes.common
    },

    getOrderedTraits(groupedData, excludeTrait) {
        let allTraits = Object.values(groupedData).flatMap(c => c.map(c => c.trait_name))

        let frequency = {};
        allTraits.forEach(item => { frequency[item] = (frequency[item] || 0) + 1});

        let uniqueTraits = [...new Set(allTraits)];
        uniqueTraits.sort((a, b) => frequency[b] - frequency[a]);

        if (excludeTrait) uniqueTraits = uniqueTraits.filter(t => t !== excludeTrait)

        return uniqueTraits
    },

    getTraitListHTML(content) {
        const uniqueTraits = [...new Set(content.map(s => 
            s.trait_name.length > 70 ? `${s.trait_name.slice(0, 70)}...` : s.trait_name)
        )];
        const traitNames = uniqueTraits.slice(0, 9).join("<br>");
        let tooltipContent = `<b>SNP: ${content[0].candidate_snp}</b><br>${traitNames}`;
        if (uniqueTraits.length > 10) {
            tooltipContent += `<br>${uniqueTraits.length - 10} more...`;
        }
        return tooltipContent;
    },

    initGraph(chartContainer, graphData, errorMessage, graphFunction) {
        if (errorMessage) {
            chartContainer.innerHTML = '<div class="notification is-danger is-light mt-4">' + errorMessage + '</div>'
            return
        }
        else if (!graphData) {
            chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
            return
        }

        // listen to resize events to redraw the graph
        window.addEventListener('resize', () => {
            clearTimeout(this.resizeTimer);
            this.resizeTimer = setTimeout(() => {
                graphFunction();
            }, 250);
        });

        graphFunction()
    },

    getTooltip(content, event) {
        // If the tooltip would overflow the right edge, expand left
        // We need to allow the DOM to update so we can measure the tooltip
        const tooltip = d3.select("body")
            .append('div')
            .attr('class', 'tooltip')
            .style('display', 'block')
            .style('position', 'absolute')
            .style('background-color', 'white')
            .style('opacity', '0.90')
            .style('padding', '5px')
            .style('border', '1px solid black')
            .style('border-radius', '5px')
            .style('visibility', 'hidden')
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
                .style('left', `${left}px`)
                .style('top', `${event.pageY - 10}px`)
                .style('visibility', 'visible');
        }, 0);
    },
    traitByPositionGraph(minMbp, maxMbp, filteredData, genesInRegion) {

        const self = this;
        const container = document.getElementById('trait-by-position-chart');
        container.innerHTML = '';

        // Prepare SNP groups with position data first
        const snpGroups = Object.entries(filteredData.groupedResults).map(([snp, studies]) => ({
            snp,
            studies,
            bp: snp.match(/\d+:(\d+)_/)[1] / 1000000
        }));

        // Get positioned groups first to determine height
        const positionedGroups = assignCircleLevels(snpGroups);
        const maxLevel = Math.max(...positionedGroups.map(g => g.level));
        
        // Calculate the height needed for the highest circle
        const baseRadius = 2;
        const maxCircleRadius = Math.max(baseRadius + Math.sqrt(Math.max(
            ...positionedGroups.map(g => g.studies.length)
        )), 10);
        
        const circleSpace = (maxLevel * maxCircleRadius/1.5) + 50; // 50 for padding from x-axis
        
        // Dynamically calculate height based on actual circle space needed
        const minHeight = 300;
        const calculatedHeight = Math.max(minHeight, circleSpace + 200); // +200 for margins and gene track

        const graphConstants = {
            width: container.clientWidth,
            height: calculatedHeight,
            outerMargin: {
                top: 90,
                right: 60,
                bottom: 150,
                left: 60,
            },
            geneTrackMargin: {
                top: 40,
                height: 20
            }
        }

        const innerWidth = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
        const innerHeight = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

        const svg = d3.select('#trait-by-position-chart')
            .append('svg')
            .attr('viewBox', `0 0 ${graphConstants.width} ${graphConstants.height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet')
            .style('width', '100%')
            .style('height', '100%')
            .append('g')
            .attr('transform', `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

        const xScale = d3.scaleLinear()
            .domain([minMbp, maxMbp])
            .nice()
            .range([0, innerWidth]);

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

        // Function to detect overlaps and assign vertical levels
        function assignCircleLevels(snpGroups) {
            let levels = [];
            snpGroups.forEach(group => {
                let level = 0;
                const radius = Math.min(5 + Math.sqrt(group.studies.length) * 2, 20);
                const position = group.bp;
                
                while (true) {
                    const hasOverlap = levels[level]?.some(existing => {
                        const existingRadius = Math.min(5 + Math.sqrt(existing.studies.length) * 2, 20);
                        const distance = Math.abs(existing.bp - position);
                        return distance < (radius + existingRadius);
                    });
                    
                    if (!hasOverlap) {
                        if (!levels[level]) levels[level] = [];
                        levels[level].push({...group, level});
                        break;
                    }
                    level++;
                }
            });
            return levels.flat();
        }

        // Add circles for each SNP group with adjusted vertical positions
        positionedGroups.forEach(({snp, studies, bp, level}) => {
            const baseRadius = 2;
            const radius = studies.length > 0 ? 
                Math.min(baseRadius + Math.sqrt(studies.length) * 1.5, 10) : 
                baseRadius;

            // Adjust y-position calculation to start from the bottom
            // and work upwards, leaving less empty space
            const yPos = innerHeight - (level * (radius * 1.8)) - 10;

            svg.append('circle')
                .attr('cx', xScale(bp))
                .attr('cy', yPos)
                .attr('r', radius)
                .attr("fill", this.getResultColorType(studies[0].type))
                .attr("stroke", "#fff")
                .attr("stroke-width", 1.5)
                .style('opacity', 0.9)
                .on('mouseover', function(event, d) {
                    d3.select(this).style("cursor", "pointer");
                    d3.select(this).transition()
                        .duration('100')
                        .attr("fill", constants.colors.dataTypes.highlighted)
                        .attr("r", radius + 8)

                    const tooltipContent = graphTransformations.getTraitListHTML(studies)
                    graphTransformations.getTooltip(tooltipContent, event)
                })
                .on('mouseout', function() {
                    d3.select(this).transition()
                        .duration('200')
                        .attr("fill", self.getResultColorType(studies[0].type))
                        .attr("r", radius);
                    d3.selectAll('.tooltip').remove();
                });
        });

        // Add gene track
        const geneTrackY = innerHeight + graphConstants.geneTrackMargin.top;
        const genes = genesInRegion.filter(gene =>
            gene.minMbp <= maxMbp && gene.maxMbp >= minMbp
        )

        function assignLevels(genes) {
            let levels = [];
            genes.forEach(gene => {
                let level = 0;
                while (true) {
                    const hasOverlap = levels[level]?.some(existingGene => 
                        !(gene.stop < existingGene.start || gene.start > existingGene.stop)
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

        assignLevels(genes);
        const geneGroup = svg.append("g")
            .attr("class", "gene-track");

        geneGroup.selectAll(".gene-rect")
            .data(genes)
            .enter()
            .append("rect")
            .attr("class", "gene-rect")
            .attr("x", d => xScale(d.start / 1000000))
            .attr("y", d => geneTrackY + (d.level * (graphConstants.geneTrackMargin.height + 5)))
            .attr("width", d => xScale(d.stop / 1000000) - xScale(d.start / 1000000))
            .attr("height", graphConstants.geneTrackMargin.height)
            .attr("fill", (d, i) => constants.colors.palette[i % constants.colors.palette.length])
            .attr("stroke", (d) => d.focus ? "black": null)
            .attr("stroke-width", 3) 
            .attr("opacity", 0.7)
            .on('mouseover', (event, d) => {
                this.getTooltip(`Gene: ${d.gene}`, event)
            })
            .on('mouseout', () => {
                d3.selectAll('.tooltip').remove();
            });

        // Add compact legend (like phenotype.js)
        const legendWidth = 120;
        const legendHeight = 20;
        const legend = svg.append('g')
            .attr('class', 'legend')
            .attr('transform', `translate(${innerWidth - legendWidth}, -${graphConstants.outerMargin.top-10})`);

        legend.append('rect')
            .attr('x', -8)
            .attr('y', -10)
            .attr('width', legendWidth)
            .attr('height', legendHeight)
            .attr('fill', 'none')
            .attr('stroke', '#bbb')
            .attr('stroke-width', 1);

        // Common variant legend item
        legend.append('circle')
            .attr('cx', 0)
            .attr('cy', 0)
            .attr('r', 5)
            .attr('fill', constants.colors.dataTypes.common)
            .attr('stroke', '#fff')
            .attr('stroke-width', 1);

        legend.append('text')
            .attr('x', 10)
            .attr('y', 4)
            .style('font-size', '12px')
            .text('Common');

        // Rare variant legend item
        legend.append('circle')
            .attr('cx', 70)
            .attr('cy', 0)
            .attr('r', 5)
            .attr('fill', constants.colors.dataTypes.rare)
            .attr('stroke', '#fff')
            .attr('stroke-width', 1);

        legend.append('text')
            .attr('x', 80)
            .attr('y', 4)
            .style('font-size', '12px')
            .text('Rare');

        // Add x-axis label
        svg.append("text")
            .attr("x", innerWidth/2)
            .attr("y", innerHeight + graphConstants.outerMargin.bottom - 10)
            .style("text-anchor", "middle")
            .text("Genomic Position (MB)");
    },
}