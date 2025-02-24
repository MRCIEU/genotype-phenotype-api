import Alpine from 'alpinejs'
import * as d3 from "d3";
import constants from './constants.js'

export default function gene() {
  return {
    data: null,
    svg: null,
    tissueByTraits: {},
    variantTypes: null, 
    minMbp: null,
    maxMbp: null,

    async loadData() {
        let geneId = (new URLSearchParams(location.search).get('id'))
        try {
            const response = await fetch(constants.apiUrl + '/genes/' + geneId);
            this.data = await response.json();
            this.data.gene.minMbp = this.data.gene.min_bp / 1000000
            this.data.gene.maxMbp = this.data.gene.max_bp / 1000000

            this.data.gene.genes_in_region = this.data.gene.genes_in_region.map(gene => ({
                ...gene,
                minMbp : gene.min_bp / 1000000,
                maxMbp : gene.max_bp / 1000000,
            }))
            this.data.colocs = this.data.colocs.map(coloc => {
                const variantType = this.data.variants.find(variant => variant.SNP === coloc.candidate_snp)
                return {
                    ...coloc,
                    mbp : coloc.bp / 1000000,
                    variantType: variantType ? variantType.Consequence.split(",")[0] : null,
                }
            })
            this.data.study_extractions = this.data.study_extractions.map(study => ({
                ...study,
                mbp : study.bp / 1000000,
            }))

            this.minMbp = Math.min(...this.data.colocs.map(d => d.mbp), ...this.data.study_extractions.map(d => d.mbp))
            this.maxMbp = Math.max(...this.data.colocs.map(d => d.mbp), ...this.data.study_extractions.map(d => d.mbp))

            this.data.study_extractions = this.data.study_extractions.map(study => ({
                ...study,
                mbp : study.bp / 1000000,
            }))

            let variantTypesInData = Object.values(this.data.variants).map(variant => variant.Consequence)
            let filteredVariantTypes = constants.variantTypes.filter(variantType => variantTypesInData.includes(variantType))
            this.variantTypes = Object.fromEntries(filteredVariantTypes.map((key, index) => [key, constants.colors[index]]));

        } catch (error) {
            console.error('Error loading data:', error);
        }
    },

    get geneName() {
        return this.data ? `${this.data.gene.symbol}` : '...';
    },
    
    get filteredColocsExist() {
        return this.data && this.data.filteredColocs && this.data.filteredColocs.length > 0
    },

    get genomicRange() {
        return this.data ? `${this.data.gene.chr}:${this.data.gene.min_bp}-${this.data.gene.max_bp}` : '...';
    },

    get ldRegion() {
        return this.data && this.data.colocs ? this.data.colocs[0].ld_block : null
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
        return(coloc.min_p <= graphOptions.pValue &&
               coloc.posterior_prob >= graphOptions.coloc &&
               (graphOptions.includeTrans ? true : coloc.cis_trans !== 'trans') &&
               (graphOptions.onlyMolecularTraits ? coloc.data_type !== 'phenotype' : true))
               // && rare variants in the future...
      })
      this.data.filteredStudies = this.data.study_extractions.filter(study => {
        return(study.min_p <= graphOptions.pValue && 
               (graphOptions.includeTrans ? true : study.cis_trans !== 'trans') &&
               (graphOptions.onlyMolecularTraits ? study.data_type !== 'phenotype' : true))
      })
      this.data.filteredStudies.sort((a, b) => a.mbp - b.mbp)

      this.data.tissues.forEach(tissue => {
        const traitsByTissue = this.data.filteredColocs.filter(coloc => coloc.tissue === tissue)
        const colocIds = traitsByTissue.map(coloc => coloc.id)
        let colocs = {}
        if (traitsByTissue.length === 0) {
          colocs = {None: [{}]}
        } else {
          const phenotypeColocs = this.data.filteredColocs.filter(coloc => colocIds.includes(coloc.id) && coloc.data_type === 'phenotype')
          const qtlColocs = traitsByTissue.filter(coloc => coloc.data_type !== 'phenotype')
          colocs = {Phenotype: phenotypeColocs, 'Other QTLs': qtlColocs}
        }
        this.tissueByTraits[tissue] = colocs
      })

      this.data.filteredColocs.forEach(coloc => {
        const hash = [...coloc.candidate_snp].reduce((hash, char) => (hash * 31 + char.charCodeAt(0)) % 7, 0)
        coloc.color = constants.tableColors[hash]
      })
      this.data.groupedColocs = Object.groupBy(this.data.filteredColocs, ({ candidate_snp }) => candidate_snp);
    },

    getVariantTypeColor(variantType) {
        return this.variantTypes[variantType] || '#000000';
    },

    initTissueByTraitGraph() {
        if (!this.data) {
            const chartContainer = document.getElementById("gene-dot-plot");
            chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
            return;
        }

        const graphOptions = Alpine.store('graphOptionStore');
        this.filterByOptions(graphOptions);

        // listen to resize events to redraw the graph
        window.addEventListener('resize', () => {
            clearTimeout(this.resizeTimer);
            this.resizeTimer = setTimeout(() => {
                this.getTissueByTraitGraph();
            }, 250);
        });
        this.getTissueByTraitGraph();
    },


    getTissueByTraitGraph() {
        const container = document.getElementById('gene-dot-plot');
        container.innerHTML = '';

        const graphConstants = {
            width: container.clientWidth,
            height: Math.max(400, window.innerHeight * 1.6), // Responsive height
            outerMargin: {
                top: 0,
                right: 10,
                bottom: 100,
                left: 220
            }
        }

        const innerWidth = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
        const innerHeight = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

        // Create SVG with viewBox for responsiveness
        this.svg = d3.select('#gene-dot-plot')
            .append('svg')
            .attr('viewBox', `0 0 ${graphConstants.width} ${graphConstants.height}`)
            .attr('preserveAspectRatio', 'xMidYMid meet')
            .style('width', '100%')
            .style('height', '100%')
            .append('g')
            .attr('transform', `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

        // Create scales
        const tissues = Object.keys(this.tissueByTraits);
        const categories = ['None', 'Phenotype', 'Other QTLs'];

        const x = d3.scaleBand()
            .domain(categories)
            .range([0, innerWidth])
            .padding(0.1);

        const y = d3.scaleBand()
            .domain(tissues.reverse())
            .range([innerHeight, 0])
            .padding(0.1);

        // Add vertical grid lines
        this.svg.append('g')
            .attr('class', 'grid-lines')
            .selectAll('line')
            .data(categories)
            .enter()
            .append('line')
            .attr('x1', d => x(d) + x.bandwidth()/2)
            .attr('x2', d => x(d) + x.bandwidth()/2)
            .attr('y1', 0)
            .attr('y2', innerHeight)
            .style('stroke', '#e0e0e0')
            .style('stroke-width', 1);

        // Add horizontal grid lines
        this.svg.append('g')
            .attr('class', 'grid-lines')
            .selectAll('line')
            .data(tissues)
            .enter()
            .append('line')
            .attr('x1', 0)
            .attr('x2', innerWidth)
            .attr('y1', d => y(d) + y.bandwidth()/2)
            .attr('y2', d => y(d) + y.bandwidth()/2)
            .style('stroke', '#e0e0e0')
            .style('stroke-width', 1);

        // Add X axis
        this.svg.append('g')
            .attr('transform', `translate(0,${innerHeight})`)
            .call(d3.axisBottom(x))
            .selectAll('text')
            .attr('transform', 'rotate(-45)')
            .style('text-anchor', 'end');

        // Add Y axis
        this.svg.append('g')
            .call(d3.axisLeft(y));

        // Add dots for each tissue and category
        tissues.forEach(tissue => {
            categories.forEach(category => {
                const colocs = this.tissueByTraits[tissue][category] || [];
                const baseRadius = 2;
                let traitNames = ""
                let uniqueTraits = []
                if (category === 'None' && colocs.length > 0) {
                    uniqueTraits = ['None'];
                }
                else if (colocs.length > 1) {
                    uniqueTraits = [...new Set(colocs.map(t => t.trait))]
                    traitNames = uniqueTraits.slice(0,9)
                    traitNames = traitNames.join("<br />")
                    if (uniqueTraits.length > 10) traitNames += "<br /> " + (uniqueTraits.length - 10) + " more..."
                } 
                else if (colocs.length === 0) {
                    return;
                }
                const radius = uniqueTraits.length > 0 ? 
                    Math.min(baseRadius + Math.sqrt(uniqueTraits.length) * 2, 8) : // Square root scale with max size
                    0;
                
                this.svg.append('circle')
                    .attr('cx', x(category) + x.bandwidth()/2)
                    .attr('cy', y(tissue) + y.bandwidth()/2)
                    .attr('r', radius)
                    .style('fill', 'black')
                    .style('opacity', 0.7)
                    .on('mouseover', (event) => {
                        // Bold the y-axis label for this tissue
                        this.svg.selectAll('.tick text')
                            .filter(d => d === tissue)
                            .style('font-weight', 'bold');

                        if (category !== 'None') {
                            d3.select('#gene-dot-plot')
                                .append('div')
                                .attr('class', 'tooltip')
                                .style('position', 'absolute')
                                .style('background-color', 'white')
                                .style('padding', '5px')
                                .style('border', '1px solid black')
                                .style('border-radius', '5px')
                                .style('left', `${event.pageX + 10}px`)
                                .style('top', `${event.pageY - 10}px`)
                                .html(traitNames);
                        }
                    })
                    .on('mouseout', () => {
                        // Remove bold from y-axis label
                        this.svg.selectAll('.tick text')
                            .style('font-weight', 'normal');
                        
                        d3.selectAll('.tooltip').remove();
                    });
            });
        });

        // Add axis labels
        this.svg.append('text')
            .attr('x', innerWidth/2)
            .attr('y', innerHeight + graphConstants.outerMargin.bottom - 10)
            .style('text-anchor', 'middle')
            .text('Category');

        this.svg.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('x', -innerHeight/2)
            .attr('y', -graphConstants.outerMargin.left + 30)
            .style('text-anchor', 'middle')
            .text('Tissue');

        // Add window resize listener
        const resizeGraph = () => {
            const newWidth = container.clientWidth;
            const newHeight = Math.max(400, window.innerHeight * 0.6);
            
            d3.select('#gene-dot-plot svg')
                .attr('viewBox', `0 0 ${newWidth} ${newHeight}`);
        };

        // Add resize listener
        window.addEventListener('resize', resizeGraph);

        // Clean up listener when component is destroyed
        return () => {
            window.removeEventListener('resize', resizeGraph);
        };
    },

    initNetworkGraph() {
      if (!this.data) {
        const chartContainer = document.getElementById("gene-network-plot");
        chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
        return;
      }
      // listen to resize events to redraw the graph
      window.addEventListener('resize', () => {
          clearTimeout(this.resizeTimer);
          this.resizeTimer = setTimeout(() => {
              this.getNetworkGraph();
          }, 250);
      });

      this.getNetworkGraph();
    },

    getNetworkGraph() {
        const container = document.getElementById('gene-network-plot');
        container.innerHTML = '';

        const graphConstants = {
            width: container.clientWidth,
            height: Math.max(300, window.innerHeight * 0.3),
            outerMargin: {
                top: 50,
                right: 150,
                bottom: 90,
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

        // Prepare SNP groups with position data
        const snpGroups = Object.entries(this.data.groupedColocs).map(([snp, studies]) => ({
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

        // Assign levels to prevent overlaps
        const positionedGroups = assignCircleLevels(snpGroups);
        const maxLevel = Math.max(...positionedGroups.map(g => g.level));

        // Add circles for each SNP group with adjusted vertical positions
        positionedGroups.forEach(({snp, studies, bp, level}) => {
            const baseRadius = 2;
            const radius = studies.length > 0 ? 
                Math.min(baseRadius + Math.sqrt(studies.length) * 1.5, 10) : 
                baseRadius;

            const variant = this.data.variants.find(v => v.SNP === snp);
            const variantType = variant ? variant.Consequence.split(",")[0] : null;

            // Calculate y position with more compact spacing
            const yPos = (innerHeight/2) + (level - maxLevel/2) * (radius * 2.2); // Adjust multiplier (2.2) to control spacing

            svg.append('circle')
                .attr('cx', xScale(bp))
                .attr('cy', yPos)
                .attr('r', radius)
                .style('fill', this.getVariantTypeColor(variantType))
                .style('opacity', 0.9)
                .on('mouseover', (event) => {
                    // Get unique traits and format them
                    const uniqueTraits = [...new Set(studies.map(s => s.trait))];
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
                .on('mouseout', () => {
                    d3.selectAll('.tooltip').remove();
                });
        });

        // Add gene track
        const geneTrackY = innerHeight + graphConstants.geneTrackMargin.top;
        const genes = [...this.data.gene.genes_in_region];
        genes.push({
            symbol: this.data.gene.symbol,
            min_bp: this.data.gene.min_bp,
            max_bp: this.data.gene.max_bp,
            chr: this.data.gene.chr
        });

        // Function to detect overlaps and assign levels
        function assignLevels(genes) {
            let levels = [];
            genes.forEach(gene => {
                let level = 0;
                while (true) {
                    const hasOverlap = levels[level]?.some(existingGene => 
                        !(gene.max_bp < existingGene.min_bp || gene.min_bp > existingGene.max_bp)
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

        const geneLevels = assignLevels(genes);
        const geneGroup = svg.append("g")
            .attr("class", "gene-track");

        geneGroup.selectAll(".gene-rect")
            .data(genes)
            .enter()
            .append("rect")
            .attr("class", "gene-rect")
            .attr("x", d => xScale(d.min_bp / 1000000))
            .attr("y", d => geneTrackY + (d.level * (graphConstants.geneTrackMargin.height + 5)))
            .attr("width", d => xScale(d.max_bp / 1000000) - xScale(d.min_bp / 1000000))
            .attr("height", graphConstants.geneTrackMargin.height)
            .attr("fill", (d, i) => constants.colors[i % constants.colors.length])
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
                    .html(`Gene: ${d.symbol}`);
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

        legend.selectAll('circle')
            .data(Object.keys(this.variantTypes))
            .enter()
            .append('circle')
            .attr('cx', 10)
            .attr('cy', (d, i) => i * legendSpacing + 8)
            .attr('r', 5)
            .style('fill', d => this.getVariantTypeColor(d))
            .style('opacity', 0.7);

        legend.selectAll('text')
            .data(Object.keys(this.variantTypes))
            .enter()
            .append('text')
            .attr('x', 25)
            .attr('y', (d, i) => (i * legendSpacing) + 12)
            .style('font-size', '12px')
            .text(d => d.replace(/_/g, ' '));

        legend.append('text')
            .attr('x', 0)
            .attr('y', -10)
            .style('font-size', '14px')
            .style('font-weight', 'bold')
            .text('Variant Annotation');

        // Add x-axis label
        svg.append("text")
            .attr("x", innerWidth/2)
            .attr("y", innerHeight + graphConstants.outerMargin.bottom - 10)
            .style("text-anchor", "middle")
            .text("Genomic Position (MB)");
    },
  }
} 