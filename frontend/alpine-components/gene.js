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
          this.geneData.colocalisations.forEach(coloc => coloc.mbp = coloc.bp / 1_000_000)

          this.geneData.studies.forEach((study) => {
            study.mbp = study.bp / 1_000_000
          })
          this.geneData.studies.sort((a, b) => a.mbp - b.mbp);
        })

      fetch('../sample_data/gene_metadata.json')
        .then(response => {
          return response.json()
        }).then(data => {
          this.geneMetadata = data
          this.geneMetadata.gene.start = this.geneMetadata.gene.start / 1_000_000
          this.geneMetadata.gene.stop = this.geneMetadata.gene.stop / 1_000_000
        })
    },

    get getStudyToDisplay() {
      if (this.geneMetadata === null) return
      return this.geneMetadata.name
    },

    get getDataForTable() {
      if (this.filteredGeneData === null) return []
      return this.filteredGeneData.studies
    },

    filterStudies(graphOptions) {
      // best way to deep copy an object in the browser
      this.filteredGeneData = JSON.parse(JSON.stringify(this.geneData))

      // filter based on graphOptions store
      this.filteredGeneData.studies = this.filteredGeneData.studies.filter(study => 
        // study.posterior_prob >= graphOptions.coloc &&
        -Math.log10(study.min_p) > (graphOptions.pValue) &&
        (study.rare == graphOptions.includeRareVariants || study.rare == false) && 
        (!graphOptions.onlyMolecularTraits || study.molecular == graphOptions.onlyMolecularTraits) && 
        (study.trans == graphOptions.includeTrans || study.trans == false)
      )

      this.filteredGeneData.colocalisations = this.filteredGeneData.colocalisations.filter(coloc => 
        coloc.posterior_prob >= graphOptions.coloc
      )
      const allStudyIds = this.filteredGeneData.studies.map(study => study.unique_study_id)
      this.filteredGeneData.colocalisations.forEach(coloc => {
        coloc.studies = coloc.studies.filter(study => allStudyIds.includes(study.id))
      })
    },

    initGraph() {
      if (this.geneData === null || this.geneMetadata === null) {
        const chartContainer = document.getElementById("gene-chart");
        chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100"></progress>'
        return
      }

      const graphOptions = Alpine.store('graphOptionStore')
      this.filterStudies(graphOptions)
      this.produceGraph(graphOptions)
    },

    produceGraph(graphOptions) {
      if (this.filteredGeneData === null || this.geneMetadata === null) {
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
          left: 220,
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
        .domain([this.geneMetadata.gene.start, this.geneMetadata.gene.stop])
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

      // Plot the points
      svg.selectAll(".point")
          .data(this.filteredGeneData.studies)
          .enter()
          .append("circle")
          .attr("cx", d => xScale(d.mbp))
          .attr("cy", d => yScale(d.trait))
          .attr("r", 3)
          .attr("fill", d => d.color)

      // Draw lines connecting points with known colocalisations
      this.filteredGeneData.colocalisations.forEach(coloc => {
          if (coloc.studies.length > 1) {
            const minPoint = coloc.studies.reduce((min, study) => yScale(study.name) < yScale(min.name) ? study : min)
            const maxPoint = coloc.studies.reduce((max, name) => yScale(name.name) > yScale(max.name) ? name : max)

            svg.append("line")
              .attr("class", "graph-line")
              .attr("x1", xScale(coloc.mbp))
              .attr("y1", yScale(minPoint.name))
              .attr("x2", xScale(coloc.mbp))
              .attr("y2", yScale(maxPoint.name));
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