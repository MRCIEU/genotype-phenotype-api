import Alpine from 'alpinejs'
import * as d3 from "d3";
import constants from './constants.js'

export default function gene() {
  return {
    data: null,
    svg: null,
    margin: { top: 50, right: 150, bottom: 200, left: 180 },
    variantTypes: null, 

    async loadData() {
        try {
            const response = await fetch('/sample_data/gene_result.json');
            this.data = await response.json();
            this.data.gene.start = this.data.gene.start / 1000000
            this.data.gene.stop = this.data.gene.stop / 1000000

            this.data.colocs = this.data.colocs.map(coloc => ({
                ...coloc,
                mbp : coloc.bp / 1000000,
                variantType: this.data.snps[coloc.candidate_snp].Consequence
            }))
            this.data.studies = this.data.studies.map(study => ({
                ...study,
                mbp : study.bp / 1000000,
            }))
            // Create set of traits from colocs for efficient lookup
            const colocTraits = new Set(
                this.data.colocs.flatMap(coloc => [coloc.trait_a, coloc.trait_b])
            );

            // Filter studies to only include those not in colocs
            this.data.studiesNotInColoc = this.data.studies.filter(study => 
                !colocTraits.has(study.trait)
            );
            let variantTypesInData = Object.values(this.data.snps).map(snp => snp.Consequence)
            let filteredVariantTypes = constants.variantTypes.filter(variantType => variantTypesInData.includes(variantType))
            this.variantTypes = Object.fromEntries(filteredVariantTypes.map((key, index) => [key, constants.colors[index]]));

        } catch (error) {
            console.error('Error loading data:', error);
        }
    },

    getGeneName() {
        return this.data ? `Gene: ${this.data.gene.name}` : 'Gene: ...';
    },

    getDataForTable() {
        return this.data ? this.data.filteredColocs: [];
    },

    filterByOptions(graphOptions) {
      this.data.filteredColocs = this.data.colocs.filter(coloc => {
        return(coloc.min_p <= graphOptions.pValue &&
               coloc.posterior_prob >= graphOptions.coloc &&
               (graphOptions.includeTrans ? true : !coloc.includes_trans) &&
               (graphOptions.onlyMolecularTraits ? coloc.includes_qtl : true))
               // && rare variants in the future...
      })
      this.data.filteredStudies = this.data.studies.filter(study => {
        return(study.min_p <= graphOptions.pValue && 
               (graphOptions.includeTrans ? true : study.cis_trans !== 'trans') &&
               (graphOptions.onlyMolecularTraits ? study.data_type !== 'phenotype' : true))
      })
      this.data.filteredStudies.sort((a, b) => a.mbp - b.mbp)
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
        this.getTissueByTraitGraph();
    },

    getTissueByTraitGraph() {
        // Clear any existing plot
        const container = document.getElementById('gene-dot-plot');
        container.innerHTML = '';

        // TODO: start using this, and change to a local svg variable
        const graphConstants = {
            width: 1,
            height: 1,
            outerMargin: { top: 50, right: 150, bottom: 200, left: 180 }
        }


        // Set up dimensions
        const width = container.clientWidth - this.margin.left - this.margin.right;
        const height = 600 - this.margin.top - this.margin.bottom;

        // Create SVG
        this.svg = d3.select('#gene-dot-plot')
            .append('svg')
            .attr('width', width + this.margin.left + this.margin.right)
            .attr('height', height + this.margin.top + this.margin.bottom)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        // Create scales
        const uniqueTraits = [...new Set(this.data.filteredColocs.map(d => d.trait_b))];
        const uniqueTissues = [...new Set(this.data.filteredColocs.map(d => d.tissue_a))];

        const x = d3.scaleBand()
            .domain(uniqueTraits)
            .range([0, width])
            .padding(0.1);

        const y = d3.scaleBand()
            .domain(uniqueTissues)
            .range([height, 0])
            .padding(0.1);

        // Add vertical grid lines
        this.svg.append('g')
            .attr('class', 'grid-lines')
            .selectAll('line')
            .data(uniqueTraits)
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
            .data(uniqueTissues)
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

        // Add dots with variant type-based colors
        this.svg.selectAll('circle')
            .data(this.data.filteredColocs)
            .enter()
            .append('circle')
            .attr('cx', d => x(d.trait_b) + x.bandwidth()/2)
            .attr('cy', d => y(d.tissue_a) + y.bandwidth()/2)
            .attr('r', 5)
            .style('fill', d => this.getVariantTypeColor(d.variantType))
            .style('opacity', 0.7)
            .on('mouseover', (event, d) => {
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
                    .html(`Tissue: ${d.tissue_a}<br>
                          Trait: ${d.trait_b}<br>
                          p-value: ${d.min_p}<br>
                          Variant Type: ${this.data.snps[d.candidate_snp].Consequence}`
                         );
            })
            .on('mouseout', () => {
                d3.selectAll('.tooltip').remove();
            });

        // Add axis labels
        this.svg.append('text')
            .attr('x', width/2)
            .attr('y', height + this.margin.bottom - 10)
            .style('text-anchor', 'middle')
            .text('Trait');

        this.svg.append('text')
            .attr('transform', 'rotate(-90)')
            .attr('x', -height/2)
            .attr('y', -this.margin.left + 30)
            .style('text-anchor', 'middle')
            .text('Tissue');

        const legendSpacing = 25;
        const legendX = width + 10;
        
        const legend = this.svg.append('g')
            .attr('class', 'legend')
            .attr('transform', `translate(${legendX}, 20)`);

        // Add colored circles instead of rectangles
        legend.selectAll('circle')
            .data(Object.keys(this.variantTypes))
            .enter()
            .append('circle')
            .attr('cx', 5)  // Half of previous rect width (15/2)
            .attr('cy', (d, i) => i * legendSpacing + 8)  // Center circle vertically
            .attr('r', 5)  // Same size as the dots in the plot
            .style('fill', d => this.getVariantTypeColor(d))
            .style('opacity', 0.7);  // Match the opacity of the plot dots

        // Update text position to align with circles
        legend.selectAll('text')
            .data(Object.keys(this.variantTypes))
            .enter()
            .append('text')
            .attr('x', 25)  // Slightly adjusted for better spacing
            .attr('y', (d, i) => (i * legendSpacing) + 12)
            .style('font-size', '12px')
            .text(d => d.replace(/_/g, ' '));

        // Add legend title
        legend.append('text')
            .attr('x', 0)
            .attr('y', -10)
            .style('font-size', '14px')
            .style('font-weight', 'bold')
            .text('Variant Annotation');
    },

    initNetworkGraph() {
      if (!this.data) {
        const chartContainer = document.getElementById("gene-network-plot");
        chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
        return;
      }

      const graphOptions = Alpine.store('graphOptionStore');
      this.getNetworkGraph(graphOptions);
    },

    getNetworkGraph(graphOptions) {
        const container = document.getElementById('gene-network-plot');
        container.innerHTML = '';

        // Set up dimensions
        const width = container.clientWidth - this.margin.left - this.margin.right;
        const height = 600 - this.margin.top - this.margin.bottom;

      const chartElement = document.getElementById("gene-network-plot");
      chartElement.innerHTML = ''

      const chartContainer = d3.select("#gene-network-plot");
      chartContainer.select("svg").remove()
      let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

      const graphConstants = {
        width: graphWidth, 
        height: Math.floor(graphWidth / 2) + 500,
        outerMargin: {
          top: 50,
          right: 30,
          bottom: 80,
          left: 220,
        }
      }

      let self = this
      const innerWidth = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
      const innerHeight = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

        // Create expanded list with both traits for each coloc
        let expandedStudies = [];
        this.data.filteredColocs.forEach(coloc => {
            expandedStudies.push({ trait: coloc.trait_a, tissue: coloc.tissue_a, pValue: coloc.min_p, variantType: coloc.variantType, mbp: coloc.mbp });
            expandedStudies.push({ trait: coloc.trait_b, tissue: coloc.tissue_b, pValue: coloc.min_p, variantType: coloc.variantType, mbp: coloc.mbp });
        });
        const existingTraits = new Set(expandedStudies.map(study => study.trait));
        this.data.filteredStudies.forEach(study => {
            if (!existingTraits.has(study.trait)) {
                expandedStudies.push({ trait: study.trait, tissue: study.tissue, pValue: study.min_p, variantType: 'phenotype', mbp: study.mbp });
            }
        });
        expandedStudies = expandedStudies.sort((a, b) => a.mbp - b.mbp)
        const minMbp = Math.min(...expandedStudies.map(d => d.mbp))
        const maxMbp = Math.max(...expandedStudies.map(d => d.mbp))

      const svg = chartContainer
        .append("svg")
        .attr('width', graphConstants.width)
        .attr('height', graphConstants.height)
        .append('g')
        .attr('transform', `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

      const yCategories = [...new Set(expandedStudies.map(d => d.trait))];
      const xScale = d3.scaleLinear()
        .domain([minMbp, maxMbp])
        .nice()
        .range([0, innerWidth]);

      const yScale = d3.scalePoint()
          .domain(yCategories)
          .range([innerHeight, 0])
          .padding(0.5);

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
        .call(d3.axisLeft(yScale));
        
      //Labels for x and y axis
      svg.append("text")
        .attr("font-size", "14px")
        .attr("transform", "rotate (-90)")
        .attr("x", "-220")
        .attr("y", graphConstants.outerMargin.left * -1 + 20)
        .text("Trait / Study");

      svg.append("text")
        .attr("font-size", "14px")
        .attr("x", graphConstants.width/2 - graphConstants.outerMargin.left)
        .attr("y", graphConstants.height - graphConstants.outerMargin.bottom + 30)
        .text("Genomic Position (MB)");

      yCategories.forEach(category => {
        const yPos = yScale(category) + yScale.bandwidth() / 2;
        svg.append("line")
          .attr("x1", 0)
          .attr("x2", graphConstants.width)
          .attr("y1", yPos)
          .attr("y2", yPos)
          .attr("stroke", "lightgray")
          .attr("stroke-width", 1)
          .attr("stroke-dasharray", "4 2");
      })

      // Add clip path and plot group
      svg.append("defs").append("clipPath")
          .attr("id", "clip")
          .append("rect")
          .attr("width", innerWidth)
          .attr("height", innerHeight);

      const plotGroup = svg.append("g")
          .attr("clip-path", "url(#clip)");

      // Create brush without zoom functionality
      const brush = d3.brushX()
          .extent([[0, 0], [innerWidth, innerHeight]])
          .on("end", function(event) {
              // Clear the brush selection after it's made
              if (event.selection) {
                  svg.select(".brush").call(brush.move, null);
              }
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

      // Add points as a separate group to ensure events work
      const points = svg.append("g")
          .attr("class", "points-group");

      points.selectAll(".point")
          .data(expandedStudies)
          .enter()
          .append("circle")
          .attr("class", "point")
          .attr("cx", d => xScale(d.mbp))
          .attr("cy", d => yScale(d.trait))
          .attr("r", 3)
          .attr("fill", d => this.getVariantTypeColor(d.variantType))
          .style('opacity', 0.7)
          .on('mouseover', function(event, d) {
              d3.select(this)
                  .style('opacity', 1)
                  .attr('r', 5);
                  
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
                  .html(`Trait: ${d.trait}<br>
                        Position: ${d.mbp.toFixed(3)} MB<br>
                        Variant Type: ${d.variantType}`);
          })
          .on('mouseout', function() {
              d3.select(this)
                  .style('opacity', 0.7)
                  .attr('r', 3);
                  
              d3.selectAll('.tooltip').remove();
          });

      // Move the lines to be rendered before the points
      plotGroup.selectAll(".graph-line")
          .data(this.data.filteredColocs)
          .enter()
          .append("line")
          .attr("class", "graph-line")
          .attr("x1", d => xScale(d.mbp))
          .attr("y1", d => yScale(d.trait_a))
          .attr("x2", d => xScale(d.mbp))
          .attr("y2", d => yScale(d.trait_b))
          .style("stroke", "black")
          .style("stroke-width", 2);
    },

    // Clean up when component is destroyed
    destroy() {
        if (this.svg) {
            d3.select('#gene-dot-plot svg').remove();
        }
    }
  }
} 