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

            this.minMbp = Math.min(...this.data.colocs.map(d => d.mbp))
            this.maxMbp = Math.max(...this.data.colocs.map(d => d.mbp))

            this.data.study_extractions = this.data.study_extractions.map(study => ({
                ...study,
                mbp : study.bp / 1000000,
            }))
            // Create set of traits from colocs for efficient lookup
            const colocTraits = new Set(
                this.data.colocs.flatMap(coloc => coloc.trait)
            );

            // Filter studies to only include those not in colocs
            this.data.studiesNotInColoc = this.data.study_extractions.filter(study => 
                !colocTraits.has(study.trait)
            );
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

    get getDataForTable() {
        if (!this.data) return [];
        return this.data.groupedColocs
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
        window.addEventListener('resize', () => {
            // Debounce the resize event to prevent too many redraws
            clearTimeout(this.resizeTimer);
            this.resizeTimer = setTimeout(() => {
                this.getTissueByTraitGraph();
            }, 250); // Wait for 250ms after the last resize event
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

        // Set up dimensions
        const width = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
        const height = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

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
            .range([0, width])
            .padding(0.1);

        const y = d3.scaleBand()
            .domain(tissues.reverse())
            .range([height, 0])
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
            .attr('y2', height)
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
            .attr('x2', width)
            .attr('y1', d => y(d) + y.bandwidth()/2)
            .attr('y2', d => y(d) + y.bandwidth()/2)
            .style('stroke', '#e0e0e0')
            .style('stroke-width', 1);

        // Add X axis
        this.svg.append('g')
            .attr('transform', `translate(0,${height})`)
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
            .attr('x', width/2)
            .attr('y', height + graphConstants.outerMargin.bottom - 10)
            .style('text-anchor', 'middle')
            .text('Category');

        this.svg.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('x', -height/2)
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
      window.addEventListener('resize', () => {
          // Debounce the resize event to prevent too many redraws
          clearTimeout(this.resizeTimer);
          this.resizeTimer = setTimeout(() => {
              this.getNetworkGraph();
          }, 250); // Wait for 250ms after the last resize event
      });

      this.getNetworkGraph();
    },

    getNetworkGraph() {
      const chartElement = document.getElementById("gene-network-plot");
      chartElement.innerHTML = ''

      const chartContainer = d3.select("#gene-network-plot");
      chartContainer.select("svg").remove()
      let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

      const graphConstants = {
        width: graphWidth, 
        height: Math.floor(graphWidth / 2),
        outerMargin: {
          top: 50,
          right: 150,
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
      const maxStudiesPerSnp = Math.max(Object.values(this.data.groupedColocs).length)

      const yScale = d3.scaleLinear()
          .domain([0, maxStudiesPerSnp - 1])  // -1 because we're using 0-based indexing
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
          .tickFormat(d => d + 1))  // Changed from empty string to show numbers, add 1 to make it 1-based
        
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
          .on("end", function(event) {
              if (!event.selection) return; // Ignore empty selections
              
              // Get the selected range in data coordinates
              const extent = event.selection.map(xScale.invert);
              
              // Update the x scale domain to zoom
              xScale.domain(extent);
              
              // Update x-axis
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

              // Clear the brush selection after zooming
              svg.select(".brush").call(brush.move, null);
          });

      // Add brush to svg
      svg.append("g")
          .attr("class", "brush")
          .call(brush);

      // Create a container for tooltips outside of the SVG
      const tooltipContainer = d3.select('#gene-network-plot')
          .append('div')
          .attr('class', 'tooltip')
          .style('position', 'absolute')
          .style('visibility', 'hidden')
          .style('background-color', 'white')
          .style('padding', '5px')
          .style('border', '1px solid black')
          .style('border-radius', '5px');

      const lines = Object.keys(this.data.groupedColocs).map(snp => {
        const studies = this.data.groupedColocs[snp];
          const bp = snp.match(/\d+:(\d+)_/)[1] / 1000000;
          return {
            snp: snp,
            bp: bp,
            x1: xScale(bp),
            y1: yScale(0),
            x2: xScale(bp),
            y2: yScale(studies.length),
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
          .style("stroke", d => {
            const variant = this.data.variants.find(v => v.SNP === d.snp);
            return this.getVariantTypeColor(variant ? variant.Consequence.split(",")[0] : null);
          })
          .style("stroke-width", 3)
          .style("stroke-linecap", "round")
          .on('mouseover', function(event, d) {
            console.log(d)
            const uniqueTraits = [...new Set(this.data.filteredColocs.filter(coloc => coloc.candidate_snp === d.snp).map(s => s.trait))];
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
          

      // Calculate gene track height and position
      const geneTrackY = innerHeight + graphConstants.geneTrackMargin.top; // Position below x-axis
      const geneHeight = 20; // Height of each gene rectangle

      // Reset genes array before adding current gene
      const genes = [...this.data.gene.genes_in_region];  // Create fresh copy
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
          .attr("fill", (d, i) => constants.colors[i % constants.colors.length])
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
        .attr("x", innerWidth - 80)  // Position near top-right
        .attr("y", -20)              // Position above the plot
        .text("Reset Zoom")
        .style("cursor", "pointer")   // Show pointer cursor on hover
        .style("fill", "black")        // Make it look clickable
        .on("click", function() {
          // Reset x scale to original domain
          xScale.domain([self.minMbp, self.maxMbp]);
          
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

        // Add legend with adjusted position
        const legendSpacing = 25;
        const legendX = innerWidth + 10;  // Changed from innerWidth to width
        
        const legend = svg.append('g')
            .attr('class', 'legend')
            .attr('transform', `translate(${legendX}, 20)`);

        legend.selectAll('line')
            .data(Object.keys(this.variantTypes))
            .enter()
            .append('line')
            .attr('x1', 0)
            .attr('x2', 20)
            .attr('y', (d, i) => i * legendSpacing + 8)
            .style('stroke', d => this.getVariantTypeColor(d))
            .style('stroke-width', 6)
            .style('stroke-linecap', 'round');

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
    },

    // getNetworkGraphV1() {
    //   const chartElement = document.getElementById("gene-network-plot");
    //   chartElement.innerHTML = ''

    //   const chartContainer = d3.select("#gene-network-plot");
    //   chartContainer.select("svg").remove()
    //   let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

    //   const graphConstants = {
    //     width: graphWidth, 
    //     height: Math.floor(graphWidth / 2) + 500,
    //     outerMargin: {
    //       top: 50,
    //       right: 30,
    //       bottom: 80,
    //       left: 220,
    //     }
    //   }

    //   const innerWidth = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
    //   const innerHeight = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

    // // Create expanded list with both traits for each coloc
    // let expandedStudies = [];
    // this.data.filteredColocs.forEach(coloc => {
    //     expandedStudies.push({ trait: coloc.trait, tissue: coloc.tissue, pValue: coloc.min_p, variantType: coloc.variantType, mbp: coloc.mbp });
    // });
    // const existingTraits = new Set(expandedStudies.map(study => study.trait));
    // this.data.filteredStudies.forEach(study => {
    //     if (!existingTraits.has(study.trait)) {
    //         expandedStudies.push({ trait: study.trait, tissue: study.tissue, pValue: study.min_p, variantType: 'phenotype', mbp: study.mbp });
    //     }
    // });
    // expandedStudies = expandedStudies.sort((a, b) => a.mbp - b.mbp)
    // const minMbp = Math.min(...expandedStudies.map(d => d.mbp))
    // const maxMbp = Math.max(...expandedStudies.map(d => d.mbp))

    //   const svg = chartContainer
    //     .append("svg")
    //     .attr('width', graphConstants.width)
    //     .attr('height', graphConstants.height)
    //     .append('g')
    //     .attr('transform', `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

    //   const yCategories = [...new Set(expandedStudies.map(d => d.trait))];
    //   const xScale = d3.scaleLinear()
    //     .domain([minMbp, maxMbp])
    //     .nice()
    //     .range([0, innerWidth]);

    //   const yScale = d3.scalePoint()
    //       .domain(yCategories)
    //       .range([innerHeight, 0])
    //       .padding(0.5);

    //   // Draw the axes
    //   svg.append("g")
    //     .attr("class", "x-axis")
    //     .call(d3.axisBottom(xScale))
    //     .attr("transform", `translate(0,${innerHeight})`)
    //     .selectAll("text")  
    //     .style("text-anchor", "end")
    //     .attr("dx", "-0.8em")
    //     .attr("dy", "0.15em")
    //     .attr("transform", "rotate(-65)")

    //   svg.append("g")
    //     .attr("class", "y-axis")
    //     .call(d3.axisLeft(yScale));
        
    //   //Labels for x and y axis
    //   svg.append("text")
    //     .attr("font-size", "14px")
    //     .attr("transform", "rotate (-90)")
    //     .attr("x", "-220")
    //     .attr("y", graphConstants.outerMargin.left * -1 + 20)
    //     .text("Trait / Study");

    //   svg.append("text")
    //     .attr("font-size", "14px")
    //     .attr("x", graphConstants.width/2 - graphConstants.outerMargin.left)
    //     .attr("y", graphConstants.height - graphConstants.outerMargin.bottom + 30)
    //     .text("Genomic Position (MB)");

    //   yCategories.forEach(category => {
    //     const yPos = yScale(category) + yScale.bandwidth() / 2;
    //     svg.append("line")
    //       .attr("x1", 0)
    //       .attr("x2", graphConstants.width)
    //       .attr("y1", yPos)
    //       .attr("y2", yPos)
    //       .attr("stroke", "lightgray")
    //       .attr("stroke-width", 1)
    //       .attr("stroke-dasharray", "4 2");
    //   })

    //   // Add clip path and plot group
    //   svg.append("defs").append("clipPath")
    //       .attr("id", "clip")
    //       .append("rect")
    //       .attr("width", innerWidth)
    //       .attr("height", innerHeight);

    //   const plotGroup = svg.append("g")
    //       .attr("clip-path", "url(#clip)");

    //   // Create brush without zoom functionality
    //   const brush = d3.brushX()
    //       .extent([[0, 0], [innerWidth, innerHeight]])
    //       .on("end", function(event) {
    //           // Clear the brush selection after it's made
    //           if (event.selection) {
    //               svg.select(".brush").call(brush.move, null);
    //           }
    //       });

    //   // Add brush to svg
    //   svg.append("g")
    //       .attr("class", "brush")
    //       .call(brush);

    //   // Create a container for tooltips outside of the SVG
    //   const tooltipContainer = d3.select('#gene-network-plot')
    //       .append('div')
    //       .attr('class', 'tooltip')
    //       .style('position', 'absolute')
    //       .style('visibility', 'hidden')
    //       .style('background-color', 'white')
    //       .style('padding', '5px')
    //       .style('border', '1px solid black')
    //       .style('border-radius', '5px');

    //   // Add points as a separate group to ensure events work
    //   const points = svg.append("g")
    //       .attr("class", "points-group");

    //   points.selectAll(".point")
    //       .data(expandedStudies)
    //       .enter()
    //       .append("circle")
    //       .attr("class", "point")
    //       .attr("cx", d => xScale(d.mbp))
    //       .attr("cy", d => yScale(d.trait))
    //       .attr("r", 3)
    //       .attr("fill", d => this.getVariantTypeColor(d.variantType))
    //       .style('opacity', 0.7)
    //       .on('mouseover', function(event, d) {
    //           d3.select(this)
    //               .style('opacity', 1)
    //               .attr('r', 5);
                  
    //           d3.select('#gene-network-plot')
    //               .append('div')
    //               .attr('class', 'tooltip')
    //               .style('position', 'absolute')
    //               .style('background-color', 'white')
    //               .style('padding', '5px')
    //               .style('border', '1px solid black')
    //               .style('border-radius', '5px')
    //               .style('left', `${event.pageX + 10}px`)
    //               .style('top', `${event.pageY - 10}px`)
    //               .html(`Trait: ${d.trait}<br>
    //                     Position: ${d.mbp.toFixed(3)} MB<br>
    //                     Variant Type: ${d.variantType}`);
    //       })
    //       .on('mouseout', function() {
    //           d3.select(this)
    //               .style('opacity', 0.7)
    //               .attr('r', 3);
                  
    //           d3.selectAll('.tooltip').remove();
    //       });

    //   // Move the lines to be rendered before the points
    //   plotGroup.selectAll(".graph-line")
    //       .data(this.data.filteredColocs)
    //       .enter()
    //       .append("line")
    //       .attr("class", "graph-line")
    //       .attr("x1", d => xScale(d.mbp))
    //       .attr("y1", d => yScale(d.trait))
    //       .attr("x2", d => xScale(d.mbp))
    //       .attr("y2", d => yScale(d.trait))
    //       .style("stroke", "black")
    //       .style("stroke-width", 2);

    //   // Add resize handler
    //   const resizeNetworkGraph = () => {
    //       const newWidth = chartContainer.node().getBoundingClientRect().width;
    //       const newHeight = Math.max(400, window.innerHeight * 0.6);
          
    //       chartContainer.select('svg')
    //           .attr('viewBox', `0 0 ${newWidth} ${newHeight}`);
    //   };

    //   // Add resize listener
    //   window.addEventListener('resize', resizeNetworkGraph);

    //   // Clean up listener when component is destroyed
    //   return () => {
    //       window.removeEventListener('resize', resizeNetworkGraph);
    //   };
    // },

  }
} 