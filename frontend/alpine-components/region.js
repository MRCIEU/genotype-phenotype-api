import * as d3 from 'd3';
import constants from './constants.js';

export default function region() {
  return {
    regionData: null,
    filteredRegionData: null,
    minMbp: null,
    maxMbp: null,
    allTraits: [],

    async loadData() {
      try {
        const response = await fetch('/sample_data/region_result.json');
        this.regionData = await response.json();

        this.regionData.colocs = this.regionData.colocs.map(coloc => ({
            ...coloc,
            mbp : coloc.bp / 1000000,
        }))
        Object.keys(this.regionData.studies).forEach(snp => { 
          this.regionData.studies[snp].studies = this.regionData.studies[snp].studies.map(study => ({
            ...study,
            mbp : study.bp / 1000000,
          }))
        })
        this.minMbp = Math.min(...this.regionData.colocs.map(d => d.mbp))
        this.maxMbp = Math.max(...this.regionData.colocs.map(d => d.mbp))
      } catch (error) {
        console.error('Error loading data:', error);
      }
    },

    get getStudyToDisplay() {
      if (this.regionData === null) return
      return this.regionData.name
    },

    get getDataForTable() {
      return this.regionData.studies
    },

    filterStudies(graphOptions) {
      this.filteredRegionData = this.regionData
      this.filteredRegionData.colocs = this.filteredRegionData.colocs.filter(coloc => {
        return((coloc.min_p <= graphOptions.pValue &&
               coloc.posterior_prob >= graphOptions.coloc &&
               (graphOptions.includeTrans ? true : !coloc.includes_trans) &&
               (graphOptions.onlyMolecularTraits ? coloc.includes_qtl : true))
              || coloc.rare)
               // && rare variants in the future...
      })
      // Filter studies within each SNP group
      Object.keys(this.filteredRegionData.studies).forEach(snp => {
        this.allTraits = [...new Set([...this.allTraits, ...this.filteredRegionData.studies[snp].studies.map(study => study.trait)])]
        this.filteredRegionData.studies[snp].studies = this.filteredRegionData.studies[snp].studies.filter(study => {
          return((study.min_p <= graphOptions.pValue &&
                 (graphOptions.includeTrans ? true : study.cis_trans !== 'trans') &&
                 (graphOptions.onlyMolecularTraits ? study.data_type === 'gene_expression' : true))
                || study.variant_type === 'rare')
        })
      })
    },

    initGraph() {
      if (this.regionData === null || this.regionData.metadata === null) {
        const chartContainer = document.getElementById("region-chart");
        chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>'
        return
      }

      const graphOptions = Alpine.store('graphOptionStore')
      this.filterStudies(graphOptions)
      this.getRegionGraph()
    },

    getRegionGraph() {
      const container = document.getElementById('region-chart');
      container.innerHTML = '';
      const margin = { top: 50, right: 150, bottom: 200, left: 180 }

      // Set up dimensions
      const width = container.clientWidth - margin.left - margin.right;
      const height = 600 - margin.top - margin.bottom;

      const chartElement = document.getElementById("region-chart");
      chartElement.innerHTML = ''

      const chartContainer = d3.select("#region-chart");
      chartContainer.select("svg").remove()
      let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

      const graphConstants = {
        width: graphWidth, 
        height: Math.floor(graphWidth / 2) + 500,
        outerMargin: {
          top: 50,
          right: 30,
          bottom: 80,
          left: 40,
        }
      }

      let self = this
      const innerWidth = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
      const innerHeight = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;


      const svg = chartContainer
        .append("svg")
        .attr('width', graphConstants.width)
        .attr('height', graphConstants.height)
        .append('g')
        .attr('transform', `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

      console.log(this.allTraits)
      const xScale = d3.scaleLinear()
        .domain([this.minMbp, this.maxMbp])
        .nice()
        .range([0, innerWidth]);

      const yScale = d3.scalePoint()
          .domain(this.allTraits)
          .range([innerHeight, 0])
          .padding(0.1)

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
        .call(d3.axisLeft(yScale))
        .selectAll("text")
        .style("display", "none")
        
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

      this.allTraits.forEach(category => {
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
      const tooltipContainer = d3.select('#region-plot')
          .append('div')
          .attr('class', 'tooltip')
          .style('position', 'absolute')
          .style('visibility', 'hidden')
          .style('background-color', 'white')
          .style('padding', '5px')
          .style('border', '1px solid black')
          .style('border-radius', '5px');

      // Add points as a separate group to ensure events work
      // const points = svg.append("g")
      //     .attr("class", "points-group");

      // points.selectAll(".point")
      //     .data(expandedStudies)
      //     .enter()
      //     .append("circle")
      //     .attr("class", "point")
      //     .attr("cx", d => xScale(d.mbp))
      //     .attr("cy", d => yScale(d.trait))
      //     .attr("r", 3)
      //     .attr("fill", d => this.getVariantTypeColor(d.variantType))
      //     .style('opacity', 0.7)
      //     .on('mouseover', function(event, d) {
      //         d3.select(this)
      //             .style('opacity', 1)
      //             .attr('r', 5);
                  
      //         d3.select('#region-plot')
      //             .append('div')
      //             .attr('class', 'tooltip')
      //             .style('position', 'absolute')
      //             .style('background-color', 'white')
      //             .style('padding', '5px')
      //             .style('border', '1px solid black')
      //             .style('border-radius', '5px')
      //             .style('left', `${event.pageX + 10}px`)
      //             .style('top', `${event.pageY - 10}px`)
      //             .html(`Trait: ${d.trait}<br>
      //                   Position: ${d.mbp.toFixed(3)} MB<br>
      //                   Variant Type: ${d.variantType}`);
      //     })
      //     .on('mouseout', function() {
      //         d3.select(this)
      //             .style('opacity', 0.7)
      //             .attr('r', 3);
                  
      //         d3.selectAll('.tooltip').remove();
      //     });
      

      const lines = Object.keys(this.filteredRegionData.studies).map(snp => {
        return this.filteredRegionData.studies[snp].studies.reduce((acc, study) => {
          const bp = snp.match(/\d+:(\d+)_/)[1] / 1000000;
          const prevStudies = acc.length > 0 ? acc[acc.length - 1] : null;
          
          if (!prevStudies) {
            return [study]; // First study, just return it in an array
          }
          
          return [...acc, {
            x1: xScale(bp),
            y1: yScale(prevStudies.trait),
            x2: xScale(bp),
            y2: yScale(study.trait),
          }];
        }, []); // Initialize with empty array
      }).flat();
      console.log(lines)
      // Move the lines to be rendered before the points
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
    },
  }
}