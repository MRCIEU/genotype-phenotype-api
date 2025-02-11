import * as d3 from 'd3';
import constants from './constants.js'

// TODO: change to have the chromosomes differ by chr size: https://ars.els-cdn.com/content/image/3-s2.0-B9780123852120000068-f06-12-9780123852120.jpg

export default function pheontype() {
  return {
    studyData: null,
    colocData: null,
    filteredColocData: null,
    filteredGroupedColoc: null,
    filteredStudies: null,
    orderedTraitsToFilterBy: null,
    colocDisplayFilters: {
      chr: null,
      candidate_snp: null
    },

    loadData() {
      fetch('../sample_data/coloc_result.json')
        .then(response => {
          return response.json()
        }).then(data => {
          this.colocData = data

          const [scaledMinNumStudies, scaledMaxNumStudies] = [2,10]
          const { maxNumStudies, minNumStudies } = this.colocData.colocs.reduce( (acc, obj) => {
            if (obj.num_unique_studies !== undefined) {
              acc.minNumStudies = Math.min(acc.minNumStudies, obj.num_unique_studies);
              acc.maxNumStudies = Math.max(acc.maxNumStudies, obj.num_unique_studies);
            }
            return acc;
            },
            { minNumStudies: Infinity, maxNumStudies: -Infinity }
          );

          this.colocData.colocs = this.colocData.colocs.map(c => {
            c.MbP = c.bp / 1000000
            c.chrText = 'CHR '.concat(c.chr)
            c.annotationColor = constants.colors[Math.floor(Math.random()*Object.keys(constants.colors).length)]
            c.ignore = false
            c.scaledNumStudies = ((c.num_unique_studies - minNumStudies) / (maxNumStudies- minNumStudies)) * (scaledMaxNumStudies- scaledMinNumStudies) + scaledMinNumStudies 
            return c
          })
          this.colocData.colocs.sort((a, b) => a.chr > b.chr);

          const graphOptions = Alpine.store('graphOptionStore')
          this.filterByOptions(graphOptions) 

        })

      fetch('../sample_data/studies.json')
        .then(response => {
          return response.json()
        }).then(data => {
          this.studyData = data
        })
    },

    get getStudyToDisplay() {
      if (this.studyData === null) return
      let studyId = (new URLSearchParams(location.search).get('id'))
      const study = this.studyData.find((item) => {
          return item.id == studyId
      })
      return study.name
    },

    filterByOptions(graphOptions) {
      this.filteredColocData = this.colocData.colocs.filter(coloc => {
        return((coloc.min_p <= graphOptions.pValue &&
               coloc.posterior_prob >= graphOptions.coloc &&
               (graphOptions.includeTrans ? true : !coloc.includes_trans) &&
               (graphOptions.onlyMolecularTraits ? coloc.includes_qtl : true))
              || coloc.rare)
               // && rare variants in the future...
      })

      this.filteredGroupedColoc = Object.groupBy(this.filteredColocData, ({ candidate_snp }) => candidate_snp);
      // deduplicate studies and sort based on frequency
      let allTraits = this.filteredColocData.map(s => [s.trait_a, s.trait_b]).flat()
      let frequency = {};
      allTraits.forEach(item => {
        frequency[item] = (frequency[item] || 0) + 1;
      });

      // sort by frequency
      let uniqueTraits = [...new Set(allTraits)];
      uniqueTraits.sort((a, b) => frequency[b] - frequency[a]);

      this.orderedTraitsToFilterBy = uniqueTraits

      this.filteredStudies = this.colocData.studies
      // this.filteredStudies = this.colocData.studies.filter(study => {
        // return(this.orderedTraitsToFilterBy.includes(study.trait))
      // })
    },

    filterByStudy(study) {
      if (study === null) {
        this.filteredColocData = this.colocData
      } else {
        this.colocDisplayFilters =  {
          chr: null,
          candidate_snp: null
        }
        this.filteredColocData = this.colocData.colocs.filter(c => c.study_a === study || c.study_b === study)
      }
    },

    get getDataForColocTable() {
      if (this.filteredGroupedColoc === null || this.filteredGroupedColoc == null) return
      return(Object.values(this.filteredGroupedColoc))

      // let uniqueStudies = this.filteredColocData.map
      // this.filteredStudies = this.colocData.studies.filter(study => {

      //   if (this.colocDisplayFilters.chr !== null) return coloc.chr == this.colocDisplayFilters.chr
      //   else if (this.colocDisplayFilters.candidate_snp !== null)  return coloc.candidate_snp === this.colocDisplayFilters.candidate_snp 
      //   else return true
      // })
      // return filteredColocData
    },

    initPhenotypeGraph() {
      if (this.filteredColocData === null) {
        const chartContainer = document.getElementById("phenotype-chart");
        chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>'
        return
      }

      const graphOptions = Alpine.store('graphOptionStore')
      this.filterByOptions(graphOptions)
      this.getPhenotypeGraph(graphOptions)
    },

    //overlay options: https://codepen.io/hanconsol/pen/bGPBGxb
    //splitting into chromosomes, using scaleBand: https://stackoverflow.com/questions/65499073/how-to-create-a-facetplot-in-d3-js
    // looks cool: https://nvd3.org/examples/scatter.html //https://observablehq.com/@d3/splom/2?intent=fork
    getPhenotypeGraph(graphOptions) {
      if (this.filteredColocData === null) {
        return
      }

      const chartElement = document.getElementById("phenotype-chart");
      chartElement.innerHTML = ''

      const chartContainer = d3.select("#phenotype-chart");
      chartContainer.select("svg").remove()
      let graphWidth = chartContainer.node().getBoundingClientRect().width - 50

      const graphConstants = {
        width: graphWidth, 
        height: Math.floor(graphWidth / 2.5),
        outerMargin: {
          top: 20,
          right: 0,
          bottom: 60,
          left: 60,
        },
        rareMargin: {
          top: 40,
          right: 0,
          bottom: 0,
          left: 0,
        }
      }

      if (!graphOptions.includeRareVariants) {
        graphConstants.rareMargin.top = 0 
      }

      let self = this

      // calculating the y axis ticks (and number of them)
      const lowerYScale = graphOptions.coloc - 0.01
      const step = 0.05
      const len = Math.floor((1 - lowerYScale) / step) + 1
      let yAxisValues = Array(len).fill().map((_, i) => graphOptions.coloc + (i * step))
      yAxisValues = yAxisValues.map((num) => Math.round((num + Number.EPSILON) * 100) / 100)

      // data wrangling around the colocData payload (this can be simplified and provided by the backend)
      let chromosomes = Array.from(Array(22).keys()).map(c => 'CHR '.concat(c+1))

      let graphData = this.filteredColocData
      // fill in missing CHRs, so we don't get a weird looking graph
      chromosomes.forEach(chrText => {
        graphData.push({chrText: chrText, ignore: true})
      })
      
      // place wrapper g with margins
      const svg = chartContainer
        .append("svg")
        .attr('width', graphConstants.width + graphConstants.outerMargin.left)
        .attr('height', graphConstants.height + graphConstants.outerMargin.top + graphConstants.outerMargin.bottom)
        .append('g')
        .attr('transform', 'translate(' + graphConstants.outerMargin.left + ',' + (graphConstants.outerMargin.top + graphConstants.rareMargin.top) + ')');

      //Labels for x and y axis
      svg.append("text")
        .attr("font-size", "14px")
        .attr("transform", "rotate (-90)")
        .attr("x", "-220" - (graphConstants.rareMargin.top / 2))
        .attr("y", "-30")
        .text("Coloc posterior probability");

      svg.append("text")
        .attr("font-size", "14px")
        .attr("x", graphConstants.width/2 - graphConstants.outerMargin.left)
        .attr("y", graphConstants.height - 40 + graphConstants.rareMargin.top)
        .text("Genomic Position (MB)");

      // calculate the outer scale band for each line graph
      const outerXScale = d3
        .scaleBand()
        .domain(chromosomes)
        .range([0, graphConstants.width]);

      // inner dimensions of chart based on bandwidth of outer scale
      const innerWidth = outerXScale.bandwidth()
      const innerHeight = graphConstants.height + graphConstants.rareMargin.top - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

      // creating each inner graph 
      const innerGraph = svg
        .selectAll('.outer')
        .data(d3.group(graphData, (d) => d.chrText))
        .enter()
        .append('g')
        .attr('class', 'outer')
        .attr('transform', function (d, i) {
          return 'translate(' + outerXScale(d[0]) + ',' + 0 + ')';
        })

      // main rectangle
      innerGraph
        .append('rect')
        .attr('width', innerWidth)
        .attr('height', innerHeight - graphConstants.rareMargin.top)
        .attr('fill', '#f9f9f9');

      // CHR header box
      innerGraph
        .append('rect')
        .attr('width', innerWidth)
        .attr('height', 15)
        .attr('transform', 'translate(' + 0 + ',' + -15 + ')')
        .attr('fill', '#d6d6d6');

      // CHR header text
      innerGraph
        .append('text')
        .text(function (d) { return d[0] })
        .attr("font-weight", 700)
        .attr('text-anchor', 'middle')
        .attr('transform', 'translate(' + innerWidth / 2 + ',' + -2 + ')')
        .attr("font-size", "12px")
        .on('mouseover', function (d, i) {
          d3.select(this).style("cursor", "pointer"); 
        })
        .on('click', function(d, i) {
          let chr = parseInt(i[0].slice(4))
          self.colocDisplayFilters.chr = chr
          self.colocDisplayFilters.candidate_snp = null
        })

      // inner y scales
      const innerXScale = d3.scaleLinear()
        .domain(d3.extent(graphData, (d) => d.MbP))
        .domain([0,270])
        .range([0, innerWidth]);

      let innerYScale = d3.scaleLinear()
        .domain([lowerYScale, 1.01])
        .range([innerHeight - graphConstants.rareMargin.top, 0]);

      // inner x scales
      innerGraph
        .append('g')
        .call(d3.axisBottom(innerXScale).tickValues([50,100,150,200,250]).tickSize(-innerHeight))
        .attr('transform', `translate(0,${innerHeight})`)
        .selectAll("text")  
        .style("text-anchor", "end")
        .attr("dx", "-.8em")
        .attr("dy", ".15em")
        .attr("transform", "rotate(-65)");

      // inner y axis
      svg.append('g')
        .call(d3.axisLeft(innerYScale).tickValues(yAxisValues).tickSize(-innerWidth))
        .attr('transform', `translate(0,${graphConstants.rareMargin.top})`);

      let tooltip = d3.select("body").append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);

      // drawing the dots, as well as the code to display the tooltip
      innerGraph
        .selectAll('dot')
        .data(d => d[1].filter(item => !item.rare))
        .enter()
        .append('circle')
        .attr("cx", function (d) { return innerXScale(d.MbP); } )
        .attr("cy", d => innerYScale(d.posterior_prob) + graphConstants.rareMargin.top) 
        .attr("r", d => d.scaledNumStudies+1)
        .attr('fill', d => d.annotationColor )
        .on('mouseover', function(d, i) {
          d3.select(this).style("cursor", "pointer"); 

          let allTraits = self.filteredGroupedColoc[i.candidate_snp].map(s => [s.trait_a, s.trait_b]).flat()
          let uniqueTraits = [...new Set(allTraits)]
          let traitNames = uniqueTraits.slice(0,9)
          traitNames = traitNames.join("<br />")
          if (uniqueTraits.length > 10) traitNames += "<br /> " + (uniqueTraits.length - 10) + " more..."

          d3.select(this).transition()
            .duration('100')
            .attr("r", d => d.scaledNumStudies + 8)
          tooltip.transition()
            .duration(100)
            .style("opacity", 1)
            .style("visibiility", "visible")
            .style("display", "flex");
          tooltip.html(traitNames)
            .style("left", (d.pageX + 10) + "px")
            .style("top", (d.pageY - 15) + "px");
        })
        .on('mouseout', function (d, i) {
            d3.select(this).transition()
              .duration('200')
              .attr("r", d => d.scaledNumStudies + 1)
            tooltip.transition()
            .duration(100)
            .style("visibiility", "hidden")
            .style("display", "none");
        })
        .on('click', function(d, i) {
          self.colocDisplayFilters.candidate_snp = i.candidate_snp
          self.colocDisplayFilters.chr = null
        });


      if (graphOptions.includeRareVariants) {
        this.displayRareVariants(self, svg, innerGraph, graphConstants, innerWidth, innerXScale)
      }
    },

    displayRareVariants(self, svg, innerGraph, graphConstants, innerWidth, innerXScale) {
      innerGraph
        .select('rect')
        .attr('y', graphConstants.rareMargin.top);

      // Add background for rare variants section
      innerGraph
        .append('rect')
        .attr('width', innerWidth)
        .attr('height', graphConstants.rareMargin.top)
        .attr('fill', '#f9f9f9')
        .attr('y', 0);

      let tooltip = d3.select("body").append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);
      // Add rare variant dots with stroke outline and no fill
      innerGraph
        .selectAll('.rare-dot')
        .data(d => d[1].filter(item => item.rare))
        .enter()
        .append('circle')
        .attr('class', 'rare-dot')
        .attr("cx", d => innerXScale(d.MbP))
        .attr("cy", graphConstants.rareMargin.top / 2)
        .attr("fill", "transparent")
        .attr("stroke", "black")
        .attr("r", 4)
        .on('mouseover', function(d, i) {
          d3.select(this).style("cursor", "pointer"); 

          let allTraits = self.filteredGroupedColoc[i.candidate_snp].map(s => [s.trait_a, s.trait_b]).flat()
          let uniqueTraits = [...new Set(allTraits)]
          let traitNames = uniqueTraits.slice(0,9)
          traitNames = traitNames.join("<br />")
          if (uniqueTraits.length > 10) traitNames += "<br /> " + (uniqueTraits.length - 10) + " more..."

          d3.select(this).transition()
            .duration('100')
            .attr("r", 8)
          tooltip.transition()
            .duration(100)
            .style("opacity", 1)
            .style("visibiility", "visible")
            .style("display", "flex");
          tooltip.html(traitNames)
            .style("left", (d.pageX + 10) + "px")
            .style("top", (d.pageY - 15) + "px");
        })
        .on('mouseout', function (d, i) {
            d3.select(this).transition()
              .duration('200')
              .attr("r", 4)
            tooltip.transition()
            .duration(100)
            .style("visibiility", "hidden")
            .style("display", "none");
        })
        .on('click', function(d, i) {
          self.colocDisplayFilters.candidate_snp = i.candidate_snp;
          self.colocDisplayFilters.chr = null;
        });

      // Adjust the position of the main plot circles
      innerGraph.selectAll('circle:not(.rare-dot)')
        .attr('y', d => d.y + graphConstants.rareMargin.top);

      // Update y-axis position for each chromosome group separately
      svg.selectAll('.y-axis')
        .attr('transform', `translate(0, ${graphConstants.rareMargin.top})`);

      // Add "Rare Variants" text to y-axis
      svg.append('text')
        .attr('class', 'rare-variants-label')
        .attr('x', -30)
        .attr('y', graphConstants.outerMargin.top)
        .attr('dy', '0.35em')
        .attr('text-anchor', 'start')
        .style('font-size', '12px')
        .text('Rare:');

      // Adjust existing y-axis labels position
      svg.selectAll('.y-axis-label')
        .attr('transform', d => `translate(${graphConstants.outerMargin.left - 50}, ${graphConstants.outerMargin.top + graphConstants.rareMargin.top + (d.height / 2)}) rotate(-90)`);

      // Add separator line in each inner graph
      innerGraph
        .append('line')
        .attr('class', 'separator-line')
        .attr('x1', 0)
        .attr('x2', innerWidth)
        .attr('y1', graphConstants.rareMargin.top)
        .attr('y2', graphConstants.rareMargin.top)
        .attr('stroke', '#ccc')
        .attr('stroke-width', 1);

      // Adjust main coloc data rect position
      innerGraph
        .select('.coloc-background-rect')
        .attr('y', graphConstants.rareMargin.top);
    }
  }
}
