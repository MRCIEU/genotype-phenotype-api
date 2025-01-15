import * as d3 from 'd3';
import constants from './constants.js';

export default function region() {
  return {
    regionMetadata: null,
    regionData: null,
    filteredRegionData: null,
    minBP: null,
    maxBP: null,

    loadData() {
      fetch('../sample_data/region.json')
        .then(response => {
          return response.json()
        }).then(data => {
          this.regionData = data
          this.minBP = this.regionData.studies.reduce((min, study) => study.bp < min.bp ? study : min).bp
          this.maxBP = this.regionData.studies.reduce((min, study) => study.bp > min.bp ? study : min).bp
          this.regionData.studies.forEach((study) => {
            study.trait = study.trait.replace('GTEx-cis', '')
            study.trait = study.trait.replace('BrainMeta-cis-eQTL', 'BrainMeta')
            study.trait = study.trait.replace(' chr', ' ')
            study.trait = study.trait.replace('GTEx-sQTL-cis', '')
            study.trait = study.trait.substring(0, 25)
          })
          this.regionData.studies.sort((a, b) => a.bp - b.bp);
        })

      fetch('../sample_data/region_metadata.json')
        .then(response => {
          return response.json()
        }).then(data => {
          this.regionMetadata = data
          this.regionMetadata.genes.forEach((gene, index) => {
            gene.color = constants.colors[index % constants.colors.length]
          })
        })
    },

    get getStudyToDisplay() {
      if (this.regionMetadata === null) return
      return this.regionMetadata.name
    },

    get getDataForTable() {
      return this.regionData.studies
    },

    filterStudies(graphOptions) {
      this.filteredRegionData = this.regionData
      this.filteredRegionData.studies = this.filteredRegionData.studies.filter(study => 
        -Math.log10(study.min_p) > (graphOptions.pValue)
      )
      const justGene = this.filteredRegionData.studies.filter(study => study.bp > 55581037 && study.bp < 55868248)
    },

    initGraph() {
      if (this.regionData === null || this.regionMetadata === null) {
        const chartContainer = document.getElementById("region-chart");
        chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>'
        return
      }

      const graphOptions = Alpine.store('graphOptionStore')
      this.filterStudies(graphOptions)
      this.getGraph(graphOptions)
    },

    getGraph(graphOptions) {
      if (this.regionData.studies === null || this.regionMetadata === null) {
        return
      }
      this.regionData.studies.forEach((study) => {
        const gene = this.regionMetadata.genes.find(gene => study.bp > gene.start && study.bp < gene.stop)
        study.color = (gene !== undefined) ? gene.color : '#888888' 
      })

      const chartElement = document.getElementById("region-chart");
      chartElement.innerHTML = ''

      const chartContainer = d3.select("#region-chart");
      chartContainer.select("svg").remove()
      let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

      const graphConstants = {
        width: graphWidth, 
        height: Math.floor(graphWidth / 1),
        outerMargin: {
          top: 20,
          right: 30,
          bottom: 80,
          left: 100,
        },
        innerMargin: {
          top: 20,
          right: 0,
          bottom: 20,
          left: 0,
        },
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

      const yCategories = [...new Set(this.regionData.studies.map(d => d.trait))];
      // let allStudies = grouped_by_snp[i.candidate_snp].map(s => [s.study_a, s.study_b]).flat()
      // let uniqueStudies = [...new Set(allStudies)]

      const xScale = d3.scaleLinear()
        .domain([this.minBP - 5, this.maxBP + 5]) // Add some padding on the x-axis
        .nice()
        .range([0, innerWidth]);

      const yScale = d3.scalePoint()
          .domain(yCategories)
          .range([innerHeight, 0])
          .padding(0.5);

      // Draw the axes
      svg.append("g")
          .attr("class", "x-axis")
          .attr("transform", `translate(0,${innerHeight})`)
          .call(d3.axisBottom(xScale))
          // .style("text-anchor", "end")
          // .attr("dx", "-.8em")
          // .attr("dy", ".15em")
          // .attr("transform", "rotate(-65)");

      svg.append("g")
          .attr("class", "y-axis")
          .call(d3.axisLeft(yScale));

      // Plot the points
      svg.selectAll(".point")
          .data(this.regionData.studies)
          .enter()
          .append("circle")
          .attr("cx", d => xScale(d.bp))
          .attr("cy", d => yScale(d.trait))
          .attr("r", 3)
          .attr("fill", d => d.color)

      // Group points by their x-value to find pairs for line drawing
      const groupedByX = d3.groups(this.regionData.studies, d => d.BP);

      // // Draw lines connecting points with the same x-value
      // groupedByX.forEach(([xValue, points]) => {
      //     if (points.length > 1) { // Only draw lines if more than one point has the same x-value
      //         svg.append("line")
      //             .attr("class", "graph-line")
      //             .attr("x1", xScale(xValue))
      //             .attr("y1", yScale(points[0].category))
      //             .attr("x2", xScale(xValue))
      //             .attr("y2", yScale(points[1].category));
      //     }
      // });

      // Add annotations as shaded regions below the x-axis
      const annotationHeight = 20; // Height for annotation rectangles
      const annotationY = innerHeight + 30; // Position below the x-axis

      svg.selectAll(".annotation")
          .data(this.regionMetadata.genes)
          .enter()
          .append("rect")
          .attr("class", "annotation")
          .attr("x", d => xScale(d.start))
          .attr("y", annotationY)
          .attr("width", d => xScale(d.stop) - xScale(d.start))
          .attr("height", annotationHeight)
          .attr("fill", d => d.color)


      svg.selectAll(".annotation-text")
          .data(this.regionMetadata.genes)
          .enter()
          .append("text")
          .attr("class", "annotation-text")
          .attr("x", d => (xScale(d.start) + xScale(d.stop)) / 2)
          .attr("y", annotationY + annotationHeight / 2 + 4) // Center vertically within the rectangle
          .text(d => d.gene_name)
    },










    getTestGraph(graphOptions) {
      if (this.regionData.studies === null) {
        return
      }

      const chartElement = document.getElementById("region-chart");
      chartElement.innerHTML = ''

      const chartContainer = d3.select("#region-chart");
      chartContainer.select("svg").remove()
      let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

      const graphConstants = {
        width: graphWidth, 
        height: Math.floor(graphWidth / 2.5),
        outerMargin: {
          top: 20,
          right: 30,
          bottom: 80,
          left: 50,
        },
        innerMargin: {
          top: 20,
          right: 0,
          bottom: 20,
          left: 0,
        },
      }

      let self = this

      const data = [
        { category: 'A', value: 5 },
        { category: 'B', value: 10 },
        { category: 'C', value: 5 },
        { category: 'D', value: 15 },
        { category: 'E', value: 10 },
        { category: 'F', value: 20 }
      ];

      const geneAnnotations = [
        { start: 0, end: 8.2, label: "Low Range", color: '#fd7f6f' },
        { start: 8, end: 16, label: "Medium Range", color: '#7eb0d5' },
        { start: 15, end: 25, label: "High Range", color: '#b2e061' }
      ];

      const innerWidth = graphConstants.width - graphConstants.outerMargin.left - graphConstants.outerMargin.right;
      const innerHeight = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

      const svg = chartContainer
        .append("svg")
        .attr('width', graphConstants.width)
        .attr('height', graphConstants.height)
        .append('g')
        .attr('transform', `translate(${graphConstants.outerMargin.left},${graphConstants.outerMargin.top})`);

      const yCategories = [...new Set(data.map(d => d.category))];
      // let allStudies = grouped_by_snp[i.candidate_snp].map(s => [s.study_a, s.study_b]).flat()
      // let uniqueStudies = [...new Set(allStudies)]

      const xScale = d3.scaleLinear()
        .domain([0, d3.max(data, d => d.value) + 5]) // Add some padding on the x-axis
        .nice()
        .range([0, innerWidth]);

      const yScale = d3.scalePoint()
          .domain(yCategories)
          .range([innerHeight, 0])
          .padding(0.5);

      // Draw the axes
      svg.append("g")
          .attr("class", "x-axis")
          .attr("transform", `translate(0,${innerHeight})`)
          .call(d3.axisBottom(xScale));

      svg.append("g")
          .attr("class", "y-axis")
          .call(d3.axisLeft(yScale));

      // Plot the points
      svg.selectAll(".point")
          .data(data)
          .enter().append("circle")
          .attr("class", "point")
          .attr("cx", d => xScale(d.value))
          .attr("cy", d => yScale(d.category))
          .attr("r", 5);

      // Group points by their x-value to find pairs for line drawing
      const groupedByX = d3.groups(data, d => d.value);

      // Draw lines connecting points with the same x-value
      groupedByX.forEach(([xValue, points]) => {
          if (points.length > 1) { // Only draw lines if more than one point has the same x-value
              svg.append("line")
                  .attr("class", "graph-line")
                  .attr("x1", xScale(xValue))
                  .attr("y1", yScale(points[0].category))
                  .attr("x2", xScale(xValue))
                  .attr("y2", yScale(points[1].category));
          }
      });
      // Add annotations as shaded regions below the x-axis
      const annotationHeight = 20; // Height for annotation rectangles
      const annotationY = innerHeight + 30; // Position below the x-axis

      svg.selectAll(".annotation")
          .data(geneAnnotations)
          .enter()
          .append("rect")
          .attr("class", "annotation")
          .attr("x", d => xScale(d.start))
          .attr("y", annotationY)
          .attr("width", d => xScale(d.end) - xScale(d.start))
          .attr("height", annotationHeight)
          .attr("fill", d => d.color)

      // Add annotation labels
      svg.selectAll(".annotation-text")
          .data(geneAnnotations)
          .enter()
          .append("text")
          .attr("class", "annotation-text")
          .attr("x", d => (xScale(d.start) + xScale(d.end)) / 2)
          .attr("y", annotationY + annotationHeight / 2 + 4) // Center vertically within the rectangle
          .text(d => d.label)
    }
  }
}