import * as d3 from 'd3';
import colocs from '../images/colocs.png'
import coloc from '../sample_data/coloc.json'
import studies from '../sample_data/studies.json'

export default function pheontype() {
  return {
    dataReceived: true,
    colocs: colocs,
    studyData: studies,
    colocData: coloc,
    colocDisplayFilters: {
      chr: null,
      candidate_snp: null
    },

    get getStudyToDisplay() {
      let studyId = (new URLSearchParams(location.search).get('id'))
      const study = this.studyData.find((item) => {
          return item.id == studyId
      })
      return study.name
    },

    get getDataForColocTable() {
      this.dataReceived = true 
      let filteredColocData = this.colocData.filter(coloc => {
        if (this.colocDisplayFilters.chr !== null) return coloc.CHR == this.colocDisplayFilters.chr
        else if (this.colocDisplayFilters.candidate_snp !== null)  return coloc.candidate_snp === this.colocDisplayFilters.candidate_snp 
        else return true
      })
      return filteredColocData
    },

    initPhenotypeGraph() {
      const graphOptions = Alpine.store('graphOptionStore')
      this.getPhenotypeGraph(graphOptions, false)

      this.$watch('$store.graphOptionStore', (graphOptions) => {
        this.getPhenotypeGraph(graphOptions, true)
      })
    },

    //overlay options: https://codepen.io/hanconsol/pen/bGPBGxb
    //splitting into chromosomes, using scaleBand: https://stackoverflow.com/questions/65499073/how-to-create-a-facetplot-in-d3-js
    // looks cool: https://nvd3.org/examples/scatter.html //https://observablehq.com/@d3/splom/2?intent=fork
    getPhenotypeGraph(graphOptions, redraw) {
      const chartContainer = d3.select("#phenotype-chart");
      let graphWidth = chartContainer.node().getBoundingClientRect().width - 50
      if (redraw) {
        chartContainer.select("svg").remove()
      }

      const graphConstants = {
        width: graphWidth, 
        height: Math.floor(graphWidth / 2.5),
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
        },
        annotationInfo: {
          'Nonsense': '#fd7f6f', 
          'Missense': '#7eb0d5',
          'Splice Site': '#b2e061',
          'Intronic': '#ffb55a',
          'Non-coding': '#ffee65',
          'UTR': '#beb9db',
          'Regulatory Region': '#fdcce5',
          'Uknown SNP': '#8bd3c7'
        }
      }

      let self = this

      // calculating the y axis ticks (and number of them)
      const lowerYScale = graphOptions.coloc - 0.01
      const step = 0.05
      const len = Math.floor((1 - lowerYScale) / step) + 1
      let tickValues = Array(len).fill().map((_, i) => graphOptions.coloc + (i * step))
      tickValues = tickValues.map((num) => Math.round((num + Number.EPSILON) * 100) / 100)

      // data wrangling around the colocData payload (this can be simplified and provided by the backend)
      let chromosomes = Array.from(Array(22).keys()).map(c => 'CHR '.concat(c+1))
      let grouped_by_snp = Object.groupBy(this.colocData, ({ candidate_snp }) => candidate_snp);
      let coloc = this.colocData.map(c => {
        c.MbP = c.BP / 1000000
        c.numUniqueTraits = this.colocData.filter(result => result.candidate_snp == c.candidate_snp).length
        return c
      })

      let data = coloc.map(result => ({
        coloc: result.posterior_prob,
        candidate_snp: result.candidate_snp,
        MbP: result.MbP,
        chr: 'CHR '.concat(result.CHR),
        CHR: result.CHR,
        annotation: Object.keys(graphConstants.annotationInfo)[Math.floor(Math.random()*Object.keys(graphConstants.annotationInfo).length)],
        numUniqueTraits: result.numUniqueTraits +2
      }))
      data.sort((a, b) => a.CHR > b.CHR);

      // place wrapper g with margins
      const svg = chartContainer
        .append("svg")
        .attr('width', graphConstants.width + graphConstants.outerMargin.left)
        .attr('height', graphConstants.height)
        .append('g')
        .attr('transform', 'translate(' + graphConstants.outerMargin.left + ',' + graphConstants.outerMargin.top + ')');

      //Labels for x and y axis
      svg.append("text")
        .attr("font-size", "14px")
        .attr("transform", "rotate (-90)")
        .attr("x", "-220")
        .attr("y", "-30")
        .text("Coloc posterior probability");

      svg.append("text")
        .attr("font-size", "14px")
        .attr("x", graphConstants.width/2 - graphConstants.outerMargin.left)
        .attr("y", graphConstants.height - graphConstants.outerMargin.bottom + 20)
        .text("Genomic Position (MB)");

      // calculate the outer scale band for each line graph
      const outerXScale = d3
        .scaleBand()
        .domain(chromosomes)
        .range([0, graphConstants.width]);

      // inner dimensions of chart based on bandwidth of outer scale
      const innerWidth = outerXScale.bandwidth()
      const innerHeight = graphConstants.height - graphConstants.outerMargin.top - graphConstants.outerMargin.bottom;

      // creating each inner graph 
      const innerGraph = svg
        .selectAll('.outer')
        .data(d3.group(data, (d) => d.chr))
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
        .attr('height', innerHeight)
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
        .text(function (d) {
          return d[0];
        })
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
        .domain(d3.extent(data, (d) => d.MbP))
        .domain([0,270])
        .range([0, innerWidth]);
      let innerYScale = d3.scaleLinear()
        .domain([lowerYScale, 1.01])
        .range([innerHeight, 0]);

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

      svg.append('g')
        .call(d3.axisLeft(innerYScale).tickValues(tickValues).tickSize(-innerWidth));

      let tooltip = d3.select("body").append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);

      // drawing the dots, as well as the code to display the tooltip
      innerGraph
        .selectAll('dot')
        .data(d => d[1])
        .enter()
        .append('circle')
        .attr("cx", function (d) { return innerXScale(d.MbP); } )
        .attr("cy", d => innerYScale(d.coloc)) 
        .attr("r", d => d.numUniqueTraits+1)
        .attr('fill', d => graphConstants.annotationInfo[d.annotation] )
        .on('mouseover', function(d, i) {
          d3.select(this).style("cursor", "pointer"); 
          let allStudies = grouped_by_snp[i.candidate_snp].map(s => [s.study_a, s.study_b]).flat()
          let uniqueStudies = [...new Set(allStudies)]
          let studyNames = uniqueStudies
          studyNames = studyNames.join("<br />")
          d3.select(this).transition()
            .duration('100')
            .attr("r", d => d.numUniqueTraits + 8)
          tooltip.transition()
            .duration(100)
            .style("opacity", 1)
            .style("visibiility", "visible")
            .style("display", "flex");
          tooltip.html(studyNames)
            .style("left", (d.pageX + 10) + "px")
            .style("top", (d.pageY - 15) + "px");
        })
        .on('mouseout', function (d, i) {
            d3.select(this).transition()
              .duration('200')
              .attr("r", d => d.numUniqueTraits + 1)
            tooltip.transition()
            .duration(100)
            .style("visibiility", "hidden")
            .style("display", "none");
        })
        .on('click', function(d, i) {
          self.colocDisplayFilters.candidate_snp = i.candidate_snp
          self.colocDisplayFilters.chr = null
        });
    }
  }
}
