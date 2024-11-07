import * as d3 from 'd3';
import constants from './constants.js';

export default function gene() {
  return {
    geneMetadata: null,
    geneData: null,
    filteredGeneData: null,

    loadData() {
      fetch('../sample_data/gene.json')
        .then(response => {
          return response.json()
        }).then(data => {
          this.geneData = data
          this.geneData.studies.sort((a, b) => a.bp - b.bp);

          this.geneData.studies.forEach((study) => {
            study.trait = study.trait.replace('GTEx-cis', '')
            study.trait = study.trait.replace('BrainMeta-cis-eQTL', 'BrainMeta')
            study.trait = study.trait.replace(' chr', ' ')
            study.trait = study.trait.replace('GTEx-sQTL-cis', '')
          })
        })

      fetch('../sample_data/gene_metadata.json')
        .then(response => {
          return response.json()
        }).then(data => {
          this.geneMetadata = data
        })
    },

    get getStudyToDisplay() {
      if (this.geneMetadata === null) return
      return this.geneMetadata.name
    },

    get getDataForTable() {
      return this.geneData.studies
    },

    filterStudies(graphOptions) {
      this.filteredGeneData = this.geneData
      this.filteredGeneData.studies = this.filteredGeneData.studies.filter(study => 
        -Math.log10(study.min_p) > (graphOptions.pValue)
      )
    },

    initGraph() {
      if (this.geneData === null || this.geneMetadata === null) {
        const chartContainer = document.getElementById("gene-chart");
        chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100"></progress>'
        return
      }

      const graphOptions = Alpine.store('graphOptionStore')
      this.filterStudies(graphOptions)
      this.getGraph(graphOptions)
    },

    getGraph(graphOptions) {
      if (this.geneData.studies === null || this.geneMetadata === null) {
        return
      }
      // this.geneData.studies.forEach((study) => {
        // const gene = this.geneMetadata.genes.find(gene => study.bp > gene.start && study.bp < gene.stop)
        // study.color = (gene !== undefined) ? gene.color : '#888888' 
      // })

      const chartElement = document.getElementById("gene-chart");
      chartElement.innerHTML = ''

      const chartContainer = d3.select("#gene-chart");
      chartContainer.select("svg").remove()
      let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

      const graphConstants = {
        width: graphWidth, 
        height: Math.floor(graphWidth / 2),
        outerMargin: {
          top: 20,
          right: 30,
          bottom: 80,
          left: 200,
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

      const yCategories = [...new Set(this.geneData.studies.map(d => d.trait))];

      const xScale = d3.scaleLinear()
        .domain([this.geneMetadata.gene.start - 5, this.geneMetadata.gene.stop + 5])
        .nice()
        .range([0, innerWidth]);

      const yScale = d3.scalePoint()
          .domain(yCategories)
          .range([innerHeight, 0])
          .padding(0.5);

      // Draw the axes
      svg.append("g")
        .attr("class", "x-axis")
        .style("text-anchor", "end")
        .attr("transform", `translate(0,${innerHeight})`)
        .attr("dx", "-0.8em")
        .attr("dy", "0.15em")
        .call(d3.axisBottom(xScale))

      svg.append("g")
        .attr("class", "y-axis")
        .call(d3.axisLeft(yScale));

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

      // Plot the points
      svg.selectAll(".point")
          .data(this.geneData.studies)
          .enter()
          .append("circle")
          .attr("cx", d => xScale(d.bp))
          .attr("cy", d => yScale(d.trait))
          .attr("r", 3)
          .attr("fill", d => d.color)

      // Group points by their x-value to find pairs for line drawing
      const groupedByX = d3.groups(this.geneData.studies, d => d.bp);

      // Draw lines connecting points with the same x-value
      groupedByX.forEach(([xValue, points]) => {
          if (points.length > 1) {
            const minPoint = points.reduce((min, point) => yScale(point.trait) < yScale(min.trait) ? point: min)
            const maxPoint = points.reduce((max, point) => yScale(point.trait) > yScale(max.trait) ? point: max)

            svg.append("line")
              .attr("class", "graph-line")
              .attr("x1", xScale(xValue))
              .attr("y1", yScale(minPoint.trait))
              .attr("x2", xScale(xValue))
              .attr("y2", yScale(maxPoint.trait));
          }
      });

      // Add annotations as shaded regions below the x-axis
      const annotationHeight = 20; // Height for annotation rectangles
      const annotationY = innerHeight + 30; // Position below the x-axis

      // svg.selectAll(".annotation")
      //     .data(this.geneMetadata.genes)
      //     .enter()
      //     .append("rect")
      //     .attr("class", "annotation")
      //     .attr("x", d => xScale(d.start))
      //     .attr("y", annotationY)
      //     .attr("width", d => xScale(d.stop) - xScale(d.start))
      //     .attr("height", annotationHeight)
      //     .attr("fill", d => d.color)


      // svg.selectAll(".annotation-text")
      //     .data(this.geneMetadata.genes)
      //     .enter()
      //     .append("text")
      //     .attr("class", "annotation-text")
      //     .attr("x", d => (xScale(d.start) + xScale(d.stop)) / 2)
      //     .attr("y", annotationY + annotationHeight / 2 + 4) // Center vertically within the rectangle
      //     .text(d => d.gene_name)
    }
  }
}