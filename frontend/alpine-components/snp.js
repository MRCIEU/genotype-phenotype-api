import Alpine from 'alpinejs'
import * as d3 from "d3";
import constants from './constants.js'

export default function gene() {
  return {
    data: null,

    async loadData() {
        try {
            const response = await fetch('/sample_data/snp_result.json');
            this.data = await response.json();

            this.data.studies = this.data.studies.map(study => ({
                ...study,
                tissue: study.tissue ? study.tissue : "N/A",
                cis_trans: study.cis_trans? study.cis_trans : "N/A"
            })) 

            this.filterByOptions(Alpine.store('graphOptionStore'));
        } catch (error) {
            console.error('Error loading data:', error);
        }
    },

    getSNPName() {
        return this.data ? `RSID: ${this.data.annotation.rsid}` : 'RSID: ...';
    },

    getAnnotationData() {
        return this.data ? this.data.annotation : {};
    },

    getDataForTable() {
        return this.data ? this.data.studies: {};
    },

    filterByOptions(graphOptions) {
      this.data.filteredStudies = this.data.studies.filter(study => {
        return(study.min_p <= graphOptions.pValue &&
               study.posterior_prob >= graphOptions.coloc &&
               (graphOptions.includeTrans ? true : study.cis_trans !== 'trans') &&
               (graphOptions.onlyMolecularTraits ? study.data_type !== 'phenotype' : true))
               // && rare variants in the future...
      })
      this.data.filteredStudies.sort((a, b) => a.mbp - b.mbp)
    },

    initNetworkGraph() {
      if (!this.data) {
        const chartContainer = document.getElementById("snp-network-plot");
        chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
        return;
      }

      const graphOptions = Alpine.store('graphOptionStore');
      this.filterByOptions(graphOptions);
      this.getNetworkGraph();
    },

    getNetworkGraph() {
      if (this.data.filteredStudies === null) {
        return
      }

      const chartElement = document.getElementById("snp-network-plot");
      chartElement.innerHTML = ''

      const chartContainer = d3.select("#snp-network-plot");
      chartContainer.select("svg").remove()
      let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

      const graphConstants = {
        width: graphWidth, 
        height: graphWidth,
        outerMargin: {
          top: 20,
          right: 0,
          bottom: 60,
          left: 60,
        },
        innerMargin: {
          top: 20,
          right: 0,
          bottom: 20,
          left: 0,
        }
      }
      const svg = chartContainer
        .append("svg")
        .attr('width', graphConstants.width + graphConstants.outerMargin.left)
        .attr('height', graphConstants.height)
        .append('g')
        .attr('transform', 'translate(' + graphConstants.outerMargin.left + ',' + graphConstants.outerMargin.top + ')');
      // Create the network data structure
      const nodes = []
      const links = []
      const nodesByType = {}

      // Group nodes by data_type
      this.data.studies.forEach(study => {
        if (!nodesByType[study.data_type]) {
          nodesByType[study.data_type] = []
        }
        nodesByType[study.data_type].push(study)
        nodes.push({
          id: study.unique_study_id,
          trait: study.trait,
          type: study.data_type,
          size: 2 
        })
      })

      // Create links between nodes of same type
      Object.values(nodesByType).forEach(typeGroup => {
        for (let i = 0; i < typeGroup.length; i++) {
          for (let j = i + 1; j < typeGroup.length; j++) {
            links.push({
              source: typeGroup[i].unique_study_id,
              target: typeGroup[j].unique_study_id,
              type: typeGroup[i].data_type
            })
          }
        }
      })

      // Color scale for different data types
      const color = d3.scaleOrdinal(d3.schemeCategory10)
        .domain(Object.keys(nodesByType))

      // Create force simulation with fixed iterations
      const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(graphConstants.width / 2, graphConstants.height / 2))
        .force("collision", d3.forceCollide().radius(30))
        // Stop the simulation immediately
        .stop()
        // Run simulation manually for 300 iterations
        .tick(300)

      // Draw links with final positions
      const link = svg.append("g")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y)
        .style("stroke", d => color(d.type))
        .style("stroke-opacity", 0.4)
        .style("stroke-width", 1)

      // Draw nodes with final positions
      const node = svg.append("g")
        .selectAll("g")
        .data(nodes)
        .join("g")
        .attr("transform", d => `translate(${d.x},${d.y})`)

      node.append("circle")
        .attr("r", d => d.size)
        .style("fill", d => color(d.type))
        .style("stroke", "#fff")
        .style("stroke-width", 1.5)

      node.append("title")
        .text(d => d.trait)

      // Add labels
      node.append("text")
        .text(d => d.trait)
        .attr("x", 12)
        .attr("y", 3)
        .style("font-size", "8px")

      // Add legend
      const legend = svg.append("g")
        .attr("class", "legend")
        .attr("transform", `translate(${graphConstants.width - 100}, 20)`)

      legend.selectAll("rect")
        .data(Object.keys(nodesByType))
        .join("rect")
        .attr("y", (d, i) => i * 20)
        .attr("width", 10)
        .attr("height", 10)
        .style("fill", d => color(d))

      legend.selectAll("text")
        .data(Object.keys(nodesByType))
        .join("text")
        .attr("x", 20)
        .attr("y", (d, i) => i * 20 + 9)
        .text(d => d)
        .style("font-size", "12px")

      // Modify drag behavior to maintain fixed positions
      function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart()
      }

      function dragged(event) {
        event.subject.x = event.x
        event.subject.y = event.y
        // Update position immediately
        d3.select(this).attr("transform", `translate(${event.x},${event.y})`)
        // Update connected links
        link
          .filter(l => l.source === event.subject || l.target === event.subject)
          .attr("x1", l => l.source.x)
          .attr("y1", l => l.source.y)
          .attr("x2", l => l.target.x)
          .attr("y2", l => l.target.y)
      }

      function dragended(event) {
        if (!event.active) simulation.stop()
      }

    }
  }
} 