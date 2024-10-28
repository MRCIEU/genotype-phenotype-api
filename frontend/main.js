import 'bulma/css/bulma.css'
import 'bulma-slider/dist/css/bulma-slider.min.css'
import './custom.css'

import logo from './images/logo.png'
import colocs from './images/colocs.png'
import smallLogo from './images/small_logo.svg'
import coloc from './sample_data/coloc.json'
import studies from './sample_data/studies.json'
import graphStudyData from './sample_data/graph_studies.json'

import * as d3 from 'd3';
import Alpine from 'alpinejs';

/* TODO: look into using alpine with reusable web components here: https://stackoverflow.com/questions/65710987/reusable-alpine-js-components */

window.Alpine = Alpine;
Alpine.data('homepage', () => ({
  logo,
  smallLogo,
  count: 0,
}))

Alpine.data('searchInput', () => ({
  isOpen: false,
  search: '',
  dummyData: studies,

  goToItem(item) {
    window.location.href = 'phenotype.html?id=' + item.id;
    this.search = ''
  },

  closeSearch() {
    this.search = ''
    this.isOpen = false
  },

  get getItemsForSearch() {
    const filterItems = this.dummyData.filter((item) => {
      return item.name.toLowerCase().includes(this.search.toLowerCase())
    })
    if(filterItems.length < this.dummyData.length && filterItems.length > 0) {
      this.isOpen = true
      return filterItems
    } else {
      this.isOpen = false
    }
  }
}))

Alpine.data('graphOptions', () => ({
  coloc: 0.8,
  pValue: 7.3,
  includeRareVariants: true,
  onlyMolecularTraits: false,
  cisTrans: 'cis'
}))

Alpine.data('phenotype', () => ({
  dataReceived: true,
  colocs: colocs,
  studyData: studies,
  colocData: coloc,
  graphStudyData: graphStudyData,

  get getStudyToDisplay() {
    let studyId = (new URLSearchParams(location.search).get('id'))
    const study = this.studyData.find((item) => {
        return item.id == studyId
    })
    return study.name
  },

  get getDataForColocResults() {
    this.dataReceived = true 
    return this.colocData
  },

  //overlay options: https://codepen.io/hanconsol/pen/bGPBGxb
  //splitting into chromosomes, using scaleBand: https://stackoverflow.com/questions/65499073/how-to-create-a-facetplot-in-d3-js
  // looks cool: https://nvd3.org/examples/scatter.html //https://observablehq.com/@d3/splom/2?intent=fork
  get getPhenotypeGraph() {
    const chartContainer = d3.select("#phenotype-chart");
    const annotationInfo = {
      'Nonsense': '#fd7f6f', 
      'Missense': '#7eb0d5',
      'Splice Site': '#b2e061',
      'Intronic': '#ffb55a',
      'Non-coding': '#ffee65',
      'UTR': '#beb9db',
      'Regulatory Region': '#fdcce5',
      'Uknown SNP': '#8bd3c7'
    }
    console.log(this.graphStudyData)

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
      annotation: Object.keys(annotationInfo)[Math.floor(Math.random()*Object.keys(annotationInfo).length)],
      numUniqueTraits: result.numUniqueTraits +2
    }))
    data.sort((a, b) => a.CHR > b.CHR);

    const width = 1100;
    const height = 400;

    const outerMargin = {
      top: 20,
      right: 0,
      bottom: 60,
      left: 60,
    };

    const innerMargin = {
      top: 20,
      right: 0,
      bottom: 20,
      left: 0,
    };

    // place wrapper g with margins
    const svg = chartContainer
      .append("svg")
      .attr('width', width + outerMargin.left)
      .attr('height', height)
      .append('g')
      .attr('transform', 'translate(' + outerMargin.left + ',' + outerMargin.top + ')');

    // calculate the outer scale band for each line graph
    const outerXScale = d3
      .scaleBand()
      .domain(chromosomes)
      .range([0, width]);

    // inner dimensions of chart based on bandwidth of outer scale
    const innerWidth = outerXScale.bandwidth()
    const innerHeight = height - outerMargin.top - outerMargin.bottom;

    // g for each inner chart
    const testG = svg
      .selectAll('.outer')
      .data(d3.group(data, (d) => d.chr))
      .enter()
      .append('g')
      .attr('class', 'outer')
      .attr('transform', function (d, i) {
        return 'translate(' + outerXScale(d[0]) + ',' + 0 + ')';
      })
      .on('mouseover', function (d, i) {
        // console.log(i)
        // could get all data per chromosome here, or on mouseclick
      })

    // some styling
    testG
      .append('rect')
      .attr('width', innerWidth)
      .attr('height', innerHeight)
      .attr('fill', '#f9f9f9');

    testG
      .append('rect')
      .attr('width', innerWidth)
      .attr('height', 17)
      .attr('transform', 'translate(' + 0 + ',' + -17 + ')')
      .attr('fill', '#d6d6d6');

    // CHR header
    testG
      .append('text')
      .text(function (d) {
        return d[0];
      })
      .attr('text-anchor', 'middle')
      .attr('transform', 'translate(' + innerWidth / 2 + ',' + -2 + ')')
      .attr("font-size", "12px")
      .on('mouseover', function (d, i) {
        console.log(i)
        // could get all data per chromosome here, or on mouseclick
      })

    // inner scales
    const innerXScale = d3.scaleLinear()
      .domain(d3.extent(data, (d) => d.MbP))
      .domain([0,270])
      .range([0, innerWidth]);

    let innerYScale = d3.scaleLinear()
      .domain([0.79, 1.01])
      .range([innerHeight, 0]);


    //Labels for x and y axis
    testG
      .append('g')
      .call(d3.axisBottom(innerXScale).tickValues([50,100,150,200,250]).tickSize(-innerHeight))
      .attr('transform', `translate(0,${innerHeight})`)
      .selectAll("text")  
      .style("text-anchor", "end")
      .attr("dx", "-.8em")
      .attr("dy", ".15em")
      .attr("transform", "rotate(-65)");

    svg.append("text")
      .attr("font-size", "14px")
      .attr("transform", "rotate (-90)")
      .attr("x", "-220")
      .attr("y", "-30")
      .text("Coloc posterior probability");

    svg.append("text")
      .attr("font-size", "14px")
      .attr("x", width/2 - outerMargin.left)
      .attr("y", height - outerMargin.bottom + 20)
      .text("Genomic Position (MB)");

    svg.append('g')
      .call(d3.axisLeft(innerYScale).tickValues([0.8, 0.85, 0.9, 0.95, 1]).tickSize(-innerWidth));

    let tooltip = d3.select("body").append("div")
      .attr("class", "tooltip")
      .style("opacity", 0);

    testG
      .selectAll('dot')
      .data(d => d[1])
      .enter()
      .append('circle')
      .attr("cx", function (d) { return innerXScale(d.MbP); } )
      .attr("cy", d => innerYScale(d.coloc)) 
      .attr("r", d => d.numUniqueTraits+1)
      .attr('fill', d => annotationInfo[d.annotation] )
      .on('mouseover', function(d, i) {
        let allStudies = grouped_by_snp[i.candidate_snp].map(s => [s.study_a, s.study_b]).flat()
        let uniqueStudies = [...new Set(allStudies)]
        let studyNames = uniqueStudies
        // let studyNames = this.graphStudyData.filter(s => uniqueStudies.includes(s.study_name))
          // .map(s => s.trait)

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
      });
  },

}))

Alpine.start();
