import Alpine from 'alpinejs'
import * as d3 from "d3";
import constants from './constants.js'

export default function gene() {
    return {
        data: null,
        svg: null,
        tissueByDataType: {},
        variantTypes: null, 
        minMbp: null,
        maxMbp: null,
        errorMessage: null,

        async loadData() {
            let geneId = (new URLSearchParams(location.search).get('id'))
            try {
                const response = await fetch(constants.apiUrl + '/genes/' + geneId);
                if (!response.ok) {
                    this.errorMessage = `Failed to load gene: ${geneId}. Please try again later.`
                    console.log(this.errorMessage)
                    return
                }
                this.data = await response.json();
                this.data.gene.minMbp = this.data.gene.start/ 1000000
                this.data.gene.maxMbp = this.data.gene.stop / 1000000

                this.data.colocs = this.data.colocs.map(coloc => {
                    const variantType = this.data.variants.find(variant => variant.SNP === coloc.candidate_snp)
                    return {
                        ...coloc,
                        type: 'coloc',
                        mbp : coloc.bp / 1000000,
                        variantType: variantType ? variantType.Consequence.split(",")[0] : null,
                    }
                })
                this.data.rare_results = this.data.rare_results.map(rareResult => {
                    const variantType = this.data.variants.find(variant => variant.SNP === rareResult.candidate_snp)
                    return {
                        ...rareResult,
                        type: 'rare',
                        mbp : rareResult.bp / 1000000,
                        variantType: variantType ? variantType.Consequence.split(",")[0] : null,
                    }
                })
                this.data.study_extractions = this.data.study_extractions.map(study => ({
                    ...study,
                    mbp : study.bp / 1000000,
                }))

                this.minMbp = Math.min(
                    ...this.data.colocs.map(d => d.mbp), 
                    // ...this.data.study_extractions.map(d => d.mbp),
                    // ...this.data.filteredRareResults.map(d => d.mbp),
                    this.data.gene.minMbp
                )
                this.maxMbp = Math.max(
                    ...this.data.colocs.map(d => d.mbp), 
                    // ...this.data.study_extractions.map(d => d.mbp),
                    // ...this.data.filteredRareResults.map(d => d.mbp),
                    this.data.gene.maxMbp
                )

                this.data.gene.genes_in_region = this.data.gene.genes_in_region.map(gene => ({
                    ...gene,
                    minMbp : gene.start / 1000000,
                    maxMbp : gene.stop / 1000000,
                }))
                this.data.gene.genes_in_region = this.data.gene.genes_in_region.filter(gene => {
                    return gene.minMbp < this.maxMbp && gene.maxMbp > this.minMbp
                })

                this.data.study_extractions = this.data.study_extractions.map(study => ({
                    ...study,
                    mbp : study.bp / 1000000,
                }))

                constants.orderedDataTypes.forEach(dataType => {
                    if (dataType !== 'Phenotype') this.tissueByDataType[dataType] = {}
                })

                let variantTypesInData = Object.values(this.data.variants).map(variant => variant.Consequence)
                let filteredVariantTypes = constants.variantTypes.filter(variantType => variantTypesInData.includes(variantType))
                this.variantTypes = Object.fromEntries(filteredVariantTypes.map((key, index) => [key, constants.colors.palette[index]]));
                this.filterByOptions(Alpine.store('graphOptionStore'));
            } catch (error) {
                console.error('Error loading data:', error);
            }
        },

        get geneName() {
            return this.data ? `${this.data.gene.gene}` : '...';
        },
        
        get filteredColocsExist() {
            return this.data && this.data.filteredColocs && this.data.filteredColocs.length > 0
        },

        get genomicRange() {
            return this.data ? `${this.data.gene.chr}:${this.data.gene.start}-${this.data.gene.stop}` : '...';
        },

        get ldBlockId() {
            return this.data && this.data.colocs ? this.data.colocs[0].ld_block_id : null
        },

        get colocsForTable() {
            if (!this.data) return [];
            return this.data.groupedColocs
        },

        get studyExtractionsForTable() {
            if (!this.data) return [];
            return this.data.filteredStudies
        },

        filterByOptions(graphOptions) {
            this.data.filteredColocs = this.data.colocs.filter(coloc => {
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

            this.data.filteredRareResults = this.data.rare_results
            this.data.filteredStudies = this.data.study_extractions.filter(study => {
                let graphOptionFilters = (study.min_p <= graphOptions.pValue && 
                   (graphOptions.includeTrans ? true : study.cis_trans !== 'trans') &&
                   (graphOptions.onlyMolecularTraits ? study.data_type !== 'Phenotype' : true))

                if (Object.values(graphOptions.categories).some(c => c)) {
                    graphOptionFilters = graphOptionFilters && graphOptions.categories[study.trait_category] === true
                }

                return graphOptionFilters
            })
            this.data.filteredStudies.sort((a, b) => a.mbp - b.mbp)
            this.minMbp = Math.min(
                ...this.data.filteredColocs.map(d => d.mbp), 
                // ...this.data.study_extractions.map(d => d.mbp),
                // ...this.data.filteredRareResults.map(d => d.mbp),
                this.data.gene.minMbp
            )
            this.maxMbp = Math.max(
                ...this.data.filteredColocs.map(d => d.mbp), 
                // ...this.data.study_extractions.map(d => d.mbp),
                // ...this.data.filteredRareResults.map(d => d.mbp),
                this.data.gene.maxMbp
            )

            this.data.tissues.forEach(tissue => {
                constants.orderedDataTypes.forEach(dataType => {
                    if (dataType === 'Phenotype') return;
                    const tissueColocs = this.data.filteredColocs.filter(coloc => coloc.tissue === tissue && coloc.data_type === dataType)
                    const colocIds = tissueColocs.map(coloc => coloc.id)
                    const allColocsWithTissue = this.data.filteredColocs.filter(coloc => colocIds.includes(coloc.id))
                    const tissueStudies = this.data.filteredStudies.filter(study => study.tissue == tissue && study.data_type === dataType)
                    const tissueDataTypeResults = allColocsWithTissue.concat(tissueStudies)
                    this.tissueByDataType[dataType][tissue] = tissueDataTypeResults
                })
            })

            this.data.filteredColocs.forEach(coloc => {
                const hash = [...coloc.candidate_snp].reduce((hash, char) => (hash * 31 + char.charCodeAt(0)) % 7, 0)
                coloc.color = constants.tableColors[hash]
            })
            this.data.allResults = this.data.filteredColocs.concat(this.data.filteredRareResults)
            this.data.groupedColocs = Object.groupBy(this.data.filteredColocs, ({ candidate_snp }) => candidate_snp);
            this.data.groupedResults = Object.groupBy(this.data.allResults, ({ candidate_snp }) => candidate_snp);


            const allData = this.data.filteredColocs.concat(this.data.filteredRareResults)
            this.data.associatedGenes = Object.groupBy(allData, ({ gene }) => gene)
            // Remove null and "NA" keys from associatedGenes, fix later
            delete this.data.associatedGenes[null];
            delete this.data.associatedGenes["NA"];
            delete this.data.associatedGenes[this.data.gene.gene];

            // TODO remove this once we are happier with the non colocing study list
            this.data.filteredStudies = []
        },

        getResultColorType(type) {
            if (type === 'coloc') return constants.colors.dataTypes.common
            else if (type === 'rare') return constants.colors.dataTypes.rare
            else return constants.colors.dataTypes.common
        },

        getVariantTypeColor(variantType) {
            return this.variantTypes[variantType] || '#000000';
        },

        initTraitByPositionGraph() {
            if (this.errorMessage) {
                const chartContainer = document.getElementById("gene-network-plot");
                chartContainer.innerHTML = '<div class="notification is-danger is-light mt-4">' + this.errorMessage + '</div>'
                return
            }
            else if (!this.data || !this.data.groupedResults) {
                const chartContainer = document.getElementById("gene-network-plot");
                chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
                return
            }
            const graphOptions = Alpine.store('graphOptionStore');
            this.filterByOptions(graphOptions);
            // listen to resize events to redraw the graph
            window.addEventListener('resize', () => {
                clearTimeout(this.resizeTimer);
                this.resizeTimer = setTimeout(() => {
                    this.getTraitByPositionGraph();
                }, 250);
            });

            this.getTraitByPositionGraph();
        },

        getTraitByPositionGraph() {
            const self = this;
            const container = document.getElementById('gene-network-plot');
            container.innerHTML = '';

            // Prepare SNP groups with position data first
            const snpGroups = Object.entries(this.data.groupedResults).map(([snp, studies]) => ({
                snp,
                studies,
                bp: snp.match(/\d+:(\d+)_/)[1] / 1000000
            }));

            this.data.filteredStudies.forEach(study => {
                snpGroups.push({
                    snp: null,
                    studies: [study],
                    bp: study.bp / 1000000
                })
            })

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
                    top: 50,
                    right: 150,
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

            const svg = d3.select('#gene-network-plot')
                .append('svg')
                .attr('viewBox', `0 0 ${graphConstants.width} ${graphConstants.height}`)
                .attr('preserveAspectRatio', 'xMidYMid meet')
                .style('width', '100%')
                .style('height', '100%')
                .append('g')
                .attr('transform', `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

            const xScale = d3.scaleLinear()
                .domain([this.minMbp, this.maxMbp])
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
                            return distance < (radius + existingRadius + 5); // Reduced spacing from default
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

                const variant = this.data.variants.find(v => v.SNP === snp);
                const variantType = variant ? variant.Consequence.split(",")[0] : null;

                // Adjust y-position calculation to start from the bottom
                // and work upwards, leaving less empty space
                const yPos = innerHeight - (level * (radius * 1.8)) - 50; // Reduced spacing from 2.2 to 1.8

                svg.append('circle')
                    .attr('cx', xScale(bp))
                    .attr('cy', yPos)
                    .attr('r', radius)
                    // .style('fill', this.getVariantTypeColor(variantType))
                    .attr("fill", this.getResultColorType(studies[0].type))
                    .attr("stroke", "#fff")
                    .attr("stroke-width", 1.5)
                    .style('opacity', 0.9)
                    .on('mouseover', function(event, d) {
                        d3.select(this).style("cursor", "pointer");
                        d3.select(this).transition()
                            .duration('100')
                            .attr("fill", constants.colors.dataTypes.highlighted)
                            .attr("r", radius + 8) // Make circle grow on hover like in phenotype.js
                        const uniqueTraits = [...new Set(studies.map(s => s.trait_name))];
                        const traitNames = uniqueTraits.slice(0, 9);
                        let tooltipContent = traitNames.join("<br />");
                        if (uniqueTraits.length > 10) {
                            tooltipContent += "<br /> " + (uniqueTraits.length - 10) + " more...";
                        }

                        d3.select('#gene-network-plot')
                            .append('div')
                            .attr('class', 'tooltip')
                            .style('position', 'absolute')
                            .style('background-color', 'white')
                            .style('padding', '5px')
                            .style('border', '1px solid black')
                            .style('border-radius', '5px')
                            .style('left', `${event.pageX + 10}px`)
                            .style('top', `${event.pageY - 10}px`)
                            .html(tooltipContent);
                    })
                    .on('mouseout', function() {
                        d3.select(this).transition()
                            .duration('200')
                            .attr("fill", self.getResultColorType(studies[0].type))
                            .attr("r", radius); // Return to original size
                        d3.selectAll('.tooltip').remove();
                    });
            });

            // Add gene track
            const geneTrackY = innerHeight + graphConstants.geneTrackMargin.top;
            const genes = this.data.gene.genes_in_region.filter(gene =>
                gene.minMbp <= this.maxMbp && gene.maxMbp >= this.minMbp
            )

            // Function to detect overlaps and assign levels
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
                    d3.select('#gene-network-plot')
                        .append('div')
                        .attr('class', 'tooltip')
                        .style('position', 'absolute')
                        .style('background-color', 'white')
                        .style('padding', '5px')
                        .style('border', '1px solid black')
                        .style('border-radius', '5px')
                        .style('left', `${event.pageX + 10}px`)
                        .style('top', `${event.pageY - 10}px`)
                        .html(`Gene: ${d.gene}`);
                })
                .on('mouseout', () => {
                    d3.selectAll('.tooltip').remove();
                });

            // Add legend
            const legendSpacing = 25;
            const legendX = innerWidth + 10;
            
            const legend = svg.append('g')
                .attr('class', 'legend')
                .attr('transform', `translate(${legendX}, 20)`);

            const studyTypes = ['Common', 'Rare'];
            const studyColors = [constants.colors.dataTypes.common, constants.colors.dataTypes.rare];

            legend.selectAll('circle')
                .data(studyTypes)
                .enter()
                .append('circle')
                .attr('cx', 10)
                .attr('cy', (d, i) => i * legendSpacing + 8)
                .attr('r', 5)
                .style('fill', (d, i) => studyColors[i])
                .style('opacity', 0.7);

            legend.selectAll('text')
                .data(studyTypes)
                .enter()
                .append('text')
                .attr('x', 25)
                .attr('y', (d, i) => (i * legendSpacing) + 12)
                .style('font-size', '12px')
                .text(d => d);

            legend.append('text')
                .attr('x', 0)
                .attr('y', -10)
                .style('font-size', '14px')
                .style('font-weight', 'bold')
                .text('Study Type');

            // Add x-axis label
            svg.append("text")
                .attr("x", innerWidth/2)
                .attr("y", innerHeight + graphConstants.outerMargin.bottom - 10)
                .style("text-anchor", "middle")
                .text("Genomic Position (MB)");
        },

        initAssociatedGenesGraph() {
            if (this.errorMessage) {
                const chartContainer = document.getElementById("associated-genes-plot");
                chartContainer.innerHTML = '<div class="notification is-danger is-light mt-4">' + this.errorMessage + '</div>'
                return
            }
            else if (!this.data || !this.data.groupedResults) {
                const chartContainer = document.getElementById("associated-genes-plot");
                chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
                return
            }
            const graphOptions = Alpine.store('graphOptionStore');
            this.filterByOptions(graphOptions);
            // listen to resize events to redraw the graph
            window.addEventListener('resize', () => {
                clearTimeout(this.resizeTimer);
                this.resizeTimer = setTimeout(() => {
                    this.getAssociatedGenesGraph();
                }, 250);
            });
            this.getAssociatedGenesGraph();
        },

        getAssociatedGenesGraph() {
            const container = document.getElementById('associated-genes-plot');
            if (!container || !this.data.associatedGenes) return;
            container.innerHTML = '';

            const graphConstants = {
                width: container.clientWidth,
                height: 300,
                outerMargin: {
                    top: 20,
                    right: 20,
                    bottom: 80,
                    left: 60
                }
            };

            const innerWidth = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
            const innerHeight = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

            const svg = d3.select('#associated-genes-plot')
                .append('svg')
                .attr('viewBox', `0 0 ${graphConstants.width} ${graphConstants.height}`)
                .attr('preserveAspectRatio', 'xMidYMid meet')
                .style('width', '100%')
                .style('height', '100%')
                .append('g')
                .attr('transform', `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

            // Convert associatedGenes to array and sort by count
            const geneData = Object.entries(this.data.associatedGenes)
                .map(([gene, entries]) => ({
                    gene,
                    count: entries.length
                }))
                .sort((a, b) => b.count - a.count);

            // Create scales
            const x = d3.scaleBand()
                .domain(geneData.map(d => d.gene))
                .range([0, innerWidth])
                .padding(0.1);

            const y = d3.scaleLinear()
                .domain([0, d3.max(geneData, d => d.count)])
                .nice()
                .range([innerHeight, 0]);

            // Add bars
            svg.selectAll('rect')
                .data(geneData)
                .enter()
                .append('rect')
                .attr('x', d => x(d.gene))
                .attr('y', d => y(d.count))
                .attr('width', x.bandwidth())
                .attr('height', d => innerHeight - y(d.count))
                .attr('fill', '#7eb0d5')
                .on('mouseover', function(event, d) {
                    d3.select(this).attr('fill', '#fd7f6f');
                    d3.select('#associated-genes-plot')
                        .append('div')
                        .attr('class', 'tooltip')
                        .style('position', 'absolute')
                        .style('background-color', 'white')
                        .style('padding', '5px')
                        .style('border', '1px solid black')
                        .style('border-radius', '5px')
                        .style('left', `${event.pageX + 10}px`)
                        .style('top', `${event.pageY - 10}px`)
                        .html(`Gene: ${d.gene}<br>Count: ${d.count}`);
                })
                .on('mouseout', function() {
                    d3.select(this).attr('fill', '#7eb0d5');
                    d3.selectAll('.tooltip').remove();
                });

            // Add x-axis
            svg.append('g')
                .attr('transform', `translate(0,${innerHeight})`)
                .call(d3.axisBottom(x))
                .selectAll('text')
                .attr('transform', 'rotate(-45)')
                .style('text-anchor', 'end')
                .style('font-size', '10px');

            // Add y-axis
            svg.append('g')
                .call(d3.axisLeft(y).ticks(5));

            // Add labels
            svg.append('text')
                .attr('x', innerWidth / 2)
                .attr('y', innerHeight + graphConstants.outerMargin.bottom - 10)
                .style('text-anchor', 'middle')
                .text('Gene');

            svg.append('text')
                .attr('transform', 'rotate(-90)')
                .attr('x', -innerHeight / 2)
                .attr('y', -40)
                .style('text-anchor', 'middle')
                .text('Number of Associations');
        },
    }
} 