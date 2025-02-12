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
            this.data.studies.sort((a, b) => a.data_type.localeCompare(b.data_type));

            this.filterByOptions(Alpine.store('graphOptionStore'));
        } catch (error) {
            console.error('Error loading data:', error);
        }
    },

    getSNPName() {
        return this.data ? `RSID: ${this.data.annotation.RSID}` : 'RSID: ...';
    },

    getAnnotationData() {
        return this.data ? this.data.annotation : {};
    },

    getDataForTable() {
        return this.data ? this.data.filteredStudies: {};
    },

    filterByOptions(graphOptions) {
      this.data.filteredStudies = this.data.studies.filter(study => {
        return(study.min_p <= graphOptions.pValue) &&
              (graphOptions.includeTrans ? true : study.cis_trans !== 'trans') &&
            //    study.posterior_prob >= graphOptions.coloc &&
               (graphOptions.onlyMolecularTraits ? study.data_type !== 'phenotype' : true)
               // && rare variants in the future...
      })
    },

    initChordDiagram() {
        if (!this.data) {
            const chartContainer = document.getElementById("snp-chord-diagram");
            chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
            return;
        }

        const graphOptions = Alpine.store('graphOptionStore');
        this.filterByOptions(graphOptions);
        this.getChordDiagram();
    },


    getChordDiagram() {
      if (!this.data) return;
      const self = this;
      const container = document.getElementById('snp-chord-diagram');
      container.innerHTML = '';

      // Clear any existing SVG
      d3.select('#snp-chord-diagram').select('svg').remove();

      // Set dimensions
      const width = 800;
      const height = 800;
      const innerRadius = Math.min(width, height) * 0.45;
      const outerRadius = innerRadius * 1.01;

      // Append SVG
      const svg = d3.select('#snp-chord-diagram')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width / 2},${height / 2})`);

      // Process data
      const candidate_snp = this.data.annotation.RSID;
      const studies = this.data.filteredStudies;

      // Extract unique data_types
      const dataTypes = Array.from(new Set(studies.map(d => d.data_type)));

      // Extract unique traits
      const traits = studies.map(d => d.trait);

      // Combine candidate_snp and traits into nodes
      const nodes = [candidate_snp, ...traits];

      // Create data_type mapping for coloring
      const dataTypeMap = {};
      studies.forEach(study => {
        dataTypeMap[study.trait] = study.data_type;
      });

      // Create color scale based on data_type
      const color = d3.scaleOrdinal()
        .domain(dataTypes)
        .range(Object.values(constants.colors));

      // Create index mapping
      const indexMap = {};
      nodes.forEach((node, i) => {
        indexMap[node] = i;
      });

      // Initialize matrix
      const matrix = Array(nodes.length).fill(null).map(() => Array(nodes.length).fill(0));

      // Populate matrix: connections from candidate_snp to each trait
      studies.forEach(study => {
        const source = indexMap[candidate_snp];
        const target = indexMap[study.trait];
        matrix[source][target] = 1; // Each trait connects once to the SNP
      });

      // Define chord layout
      const chordGenerator = d3.chord()
        .padAngle(0.005)
        .sortSubgroups(d3.descending);

      const chords = chordGenerator(matrix);

      // Define arc generator
      const arc = d3.arc()
        .innerRadius(innerRadius)
        .outerRadius(outerRadius);

      // Define ribbon generator
      const ribbon = d3.ribbon()
        .radius(innerRadius);

      // Add groups (candidate_snp and traits)
      const group = svg.selectAll('.group')
        .data(chords.groups)
        .enter().append('g')
        .attr('class', 'group');

      group.append('path')
        .style('fill', d => {
          const name = nodes[d.index];
          if (name === candidate_snp) {
            return '#808080'; // Gray for SNP
          }
          return color(dataTypeMap[name]);
        })
        .style('stroke', d => d3.rgb(color(dataTypeMap[nodes[d.index]])).darker())
        .attr('d', arc)
        .on('mouseover', function(event, d) {
          d3.select(this).transition().duration(200).style('fill', d3.rgb(color(dataTypeMap[nodes[d.index]])).brighter());
        })
        .on('mouseout', function(event, d) {
          d3.select(this).transition().duration(200).style('fill', nodes[d.index] === candidate_snp ? '#808080' : color(dataTypeMap[nodes[d.index]]));
        });

      // Add chords
      svg.selectAll('.chord')
        .data(chords)
        .enter().append('path')
        .attr('class', 'chord')
        .attr('d', ribbon)
        .style('fill', d => {
          const trait = nodes[d.target.index];
          return color(dataTypeMap[trait]);
        })
        .style('stroke', d => d3.rgb(color(dataTypeMap[nodes[d.target.index]])).darker())
        .attr('opacity', 0.7)
        .on('mouseover', function(event, d) {
          d3.select(this).transition().duration(200).attr('opacity', 1);
          const study = self.data.filteredStudies.find(study => study.trait === nodes[d.target.index]);
          d3.select('#snp-chord-diagram')
              .append('div')
              .attr('class', 'tooltip')
              .style('position', 'absolute')
              .style('background-color', 'white')
              .style('padding', '5px')
              .style('border', '1px solid black')
              .style('border-radius', '5px')
              .style('left', `${event.pageX + 10}px`)
              .style('top', `${event.pageY - 10}px`)
              .html(`Trait: ${study.trait}<br>
                    p-value: ${study.min_p}<br>
                    Cis/Trans: ${study.cis_trans}<br>
                    `);
        })
        .on('mouseout', function(event, d) {
          d3.select(this).transition().duration(200).attr('opacity', 0.7);
          d3.selectAll('.tooltip').remove();
        })
        // .append('title')
        // .text(d => `${candidate_snp} → ${nodes[d.target.index]} (${dataTypeMap[nodes[d.target.index]]})`);

      // Add legend
      const legend = svg.append("g")
        .attr("class", "legend")
        .attr("transform", `translate(${-width / 2 + 20}, ${-height / 2 + 20})`);

      dataTypes.forEach((type, i) => {
        const legendItem = legend.append("g")
          .attr("transform", `translate(0, ${i * 20})`);

        legendItem.append("rect")
          .attr("width", 18)
          .attr("height", 18)
          .attr("fill", color(type));

        legendItem.append("text")
          .attr("x", 24)
          .attr("y", 9)
          .attr("dy", "0.35em")
          .text(type)
          .style("font-size", "12px");
      });

      // Add SNP to legend
      const snpLegend = legend.append("g")
        .attr("transform", `translate(0, ${dataTypes.length * 20})`);

      snpLegend.append("rect")
        .attr("width", 18)
        .attr("height", 18)
        .attr("fill", "#808080");

      snpLegend.append("text")
        .attr("x", 24)
        .attr("y", 9)
        .attr("dy", "0.35em")
        .text("Candidate SNP")
        .style("font-size", "12px");
    }

  }
} 