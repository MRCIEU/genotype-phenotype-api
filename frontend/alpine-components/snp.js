import Alpine from 'alpinejs'
import * as d3 from "d3";
import JSZip from 'jszip'

import constants from './constants.js'
import downloads from './downloads.js'
import graphTransformations from './graphTransformations.js'

//TODO: look at thissss: https://observablehq.com/@d3/force-directed-graph-component

export default function snp() {
    return {
        data: null,
        svgs: [],
        filteredData: {
            colocs: null,
            rare: null,
            svgs: null,
            studies: null,
        },
        errorMessage: null,
        highlightedStudy: null,

        async loadData() {
            let variantId = (new URLSearchParams(location.search).get('id'))

            try {
                const response = await fetch(constants.apiUrl + '/variants/' + variantId)
                if (!response.ok) {
                    this.errorMessage = `Failed to load variant: ${response.status} ${constants.apiUrl + '/variants/' + variantId}`
                    return
                }
                this.data = await response.json()

                document.title = 'GP Map: ' +  this.getSNPName()
                await this.getSvgData(variantId)

                this.data.coloc_groups = this.data.coloc_groups.map(coloc => ({
                    ...coloc,
                    tissue: coloc.tissue ? coloc.tissue : "N/A",
                    cis_trans: coloc.cis_trans? coloc.cis_trans : "N/A"
                })) 
                this.data.coloc_groups.sort((a, b) => a.data_type.localeCompare(b.data_type));

                const ld_block = this.data.coloc_groups[0].ld_block
                const ld_info = ld_block.split(/[\/-]/)
                this.data.variant.min_bp = ld_info[2]
                this.data.variant.max_bp = ld_info[3]
            } catch (error) {
                console.error('Error loading data:', error);
            }
        },

        async getSvgData(variantId) {
            if (constants.isLocal) {
                variantId = 'test'
            }
            const svgsUrl = `${constants.assetBaseUrl}/snp_${variantId}_svgs.zip`
            const zipResponse = await fetch(svgsUrl)
            const zipBlob = await zipResponse.blob()
            const zip = await JSZip.loadAsync(zipBlob)

            this.svgs = [];
            const entries = Object.entries(zip.files);
            for (let i = 0; i < entries.length; i++) {
                const [filename, file] = entries[i];
                let studyExtractionId = parseInt(filename.split('.svg')[0]);
                if (constants.isLocal) {
                    studyExtractionId = this.data.coloc_groups[i%this.data.coloc_groups.length].study_extraction_id;
                }
                const svgContent = await file.async('text');
                this.svgs.push({ studyExtractionId, svgContent });
            }
        },

        getSNPName() {
            return this.data ? this.data.variant.rsid.split(',')[0] : '...'
        },

        getVariantData() {
            return this.data ? this.data.variant : {};
        },

        getDataForTable() {
            return this.data ? this.data.coloc_groups: [];
        },

        downloadDataOnly() {
            if (!this.data || !this.data.coloc_groups || this.data.coloc_groups.length === 0) {
                return;
            }
            downloads.downloadDataToZip(this.data, this.getSNPName());
        },

        async downloadDataAndGWAS() {
            if (!this.data || !this.data.coloc_groups || this.data.coloc_groups.length === 0) {
                return;
            }
            const response = await fetch(constants.apiUrl + '/variants/' + this.data.variant.id + '/summary-stats')
            if (!response.ok) {
                this.errorMessage = `Failed to download summary stats: ${response.status} ${constants.apiUrl + '/variants/' + variantId}`
                return
            }
            const zipBlob = await response.blob()
            downloads.downloadDataToZip(this.data, this.getSNPName(), zipBlob);
        },

        filterDataForGraphs() {
            if (!this.data) return
            const graphOptions = Alpine.store('graphOptionStore');
            this.data.coloc_groups = this.data.coloc_groups.filter(coloc => {
                let graphOptionFilters = (coloc.min_p <= graphOptions.pValue &&
                    (graphOptions.colocType === coloc.group_threshold) &&
                    (graphOptions.includeTrans ? true : coloc.cis_trans !== 'trans') &&
                    (graphOptions.traitType === 'all' ? true : 
                     graphOptions.traitType === 'molecular' ? coloc.data_type !== 'Phenotype' :
                     graphOptions.traitType === 'phenotype' ? coloc.data_type === 'Phenotype' : true))

                if (Object.values(graphOptions.categories).some(c => c)) {
                    graphOptionFilters = graphOptionFilters && graphOptions.categories[coloc.trait_category] === true
                }

                return graphOptionFilters
            });
            this.filteredData.svgs = this.svgs.filter(svg => {
                return this.data.coloc_groups.some(coloc => coloc.study_extraction_id === svg.studyExtractionId)
            });
            // this.data.coloc_groups.sort((a, b) => a.association.beta - b.association.beta);
        },

        initForestPlot() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("forest-plot");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () => this.getForestPlot())
        },

        initChordDiagram() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("snp-chord-diagram");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () => this.getChordDiagram())
        },

        initManhattanPlotOverlay() {
            this.filterDataForGraphs();
            const chartContainer = document.getElementById("manhattan-plot");
            graphTransformations.initGraph(chartContainer, this.data, this.errorMessage, () => this.getManhattanPlotOverlay())
        },


        getChordDiagram() {
            if (!this.data) return;
            const self = this;
            const chartElement = document.getElementById('snp-chord-diagram');
            chartElement.innerHTML = '';

            const chartContainer = d3.select("#snp-chord-diagram");
            chartContainer.select("svg").remove();
            let graphWidth = chartContainer.node().getBoundingClientRect().width - 50
            let graphHeight = 500

            const graphConstants = {
                width: graphWidth,
                height: graphHeight,
                innerRadius: Math.min(graphWidth, graphHeight) * 0.45,
                outerRadius: Math.min(graphWidth, graphHeight) * 0.45 * 1.01,
            }

            // Set dimensions
            const innerRadius = Math.min(graphConstants.width, graphConstants.height) * 0.45;
            const outerRadius = innerRadius * 1.01;

            // Append SVG
            const svg = d3.select('#snp-chord-diagram')
                .append('svg')
                .attr('width', graphConstants.width)
                .attr('height', graphConstants.height)
                .append('g')
                .attr('transform', `translate(${graphConstants.width / 2},${graphConstants.height / 2})`);

            // Process data
            const display_snp = this.data.variant.RSID;
            const colocs = this.data.coloc_groups;

            // Extract unique data_types
            const dataTypes = Array.from(new Set(colocs.map(d => d.data_type)));

            // Extract unique traits
            const traits = colocs.map(d => d.trait_name);

            // Combine display_snp and traits into nodes
            const nodes = [display_snp, ...traits];

            // Create data_type mapping for coloring
            const dataTypeMap = {};
            colocs.forEach(coloc => {
                dataTypeMap[coloc.trait_name] = coloc.data_type;
            });

            // Create color scale based on data_type
            const color = d3.scaleOrdinal()
                .domain(dataTypes)
                .range(constants.colors.palette);

            // Create index mapping
            const indexMap = {};
            nodes.forEach((node, i) => {
                indexMap[node] = i;
            });

            // Initialize matrix
            const matrix = Array(nodes.length).fill(null).map(() => Array(nodes.length).fill(0));

            // Populate matrix: connections from display_snp to each trait
            colocs.forEach(coloc => {
                const source = indexMap[display_snp];
                const target = indexMap[coloc.trait_name];
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

            // Add groups (display_snp and traits)
            const group = svg.selectAll('.group')
                .data(chords.groups)
                .enter().append('g')
                .attr('class', 'group');

            group.append('path')
                .style('fill', d => {
                    const name = nodes[d.index];
                    if (name === display_snp) {
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
                    d3.select(this).transition().duration(200).style('fill', nodes[d.index] === display_snp ? '#808080' : color(dataTypeMap[nodes[d.index]]));
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
                    const coloc = self.data.coloc_groups.find(coloc => coloc.trait_name === nodes[d.target.index]);
                    self.highlightedStudy = coloc.study_extraction_id;
                    self.svgs = self.svgs.sort((a, b) =>
                        a.studyExtractionId === coloc.study_extraction_id ? 1 : b.studyExtractionId === coloc.study_extraction_id ? -1 : 0
                    );
                    let tooltipColor = "white";
                    if (coloc.association) {
                        tooltipColor = coloc.association.beta > 0 ? "#afe1af" : "#ee4b2b";
                    }
                    d3.select('#snp-chord-diagram')
                            .append('div')
                            .attr('class', 'tooltip')
                            .style('position', 'absolute')
                            .style('background-color', tooltipColor)
                            .style('padding', '5px')
                            .style('border', '1px solid black')
                            .style('border-radius', '5px')
                            .style('left', `${event.pageX + 10}px`)
                            .style('top', `${event.pageY - 10}px`)
                            .html(`Trait: ${coloc.trait_name}<br>
                                        P-value: ${coloc.min_p.toExponential(2)}<br>
                                        Cis/Trans: ${coloc.cis_trans}<br>
                                        BETA: ${coloc.association ? coloc.association.beta: "N/A"}
                                        `);
                })
                .on('mouseout', function(event, d) {
                    d3.select(this).transition().duration(200).attr('opacity', 0.7);
                    d3.selectAll('.tooltip').remove();
                })

            // Add legend
            const legend = svg.append("g")
                .attr("class", "legend")
                .attr("transform", `translate(${-graphConstants.width / 2 + 20}, ${-graphConstants.height / 2 + 20})`);

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
        },

        getForestPlot() {
            if (!this.data || !this.data.coloc_groups) return;

            const plotContainer = d3.select("#forest-plot");
            plotContainer.selectAll("*").remove();

            const margin = { top: 50, right: 20, bottom: 40, left: 10 };
            let width = plotContainer.node().getBoundingClientRect().width;
            const height = this.data.coloc_groups.length * 27;

            const svg = plotContainer.append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);

            // Filter out items without association data
            const validData = this.data.coloc_groups.filter(d => d.association && d.association.beta !== null && d.association.se !== null);
            
            // Calculate the range for the x-axis
            const maxAbsBeta = d3.max(validData, d => Math.abs(d.association.beta));
            const xRange = [-maxAbsBeta * 1.5, maxAbsBeta * 1.5];

            // Create scales
            const x = d3.scaleLinear()
                .domain(xRange)
                .range([0, width]);

            const y = d3.scaleBand()
                .domain(validData.map(d => d.trait_name))
                .range([0, height])
                .padding(0.1);

            // Add x-axis
            svg.append("g")
                .attr("transform", `translate(0,${height})`)
                .call(d3.axisBottom(x))
                .selectAll("text")
                .style("font-size", "10px")
                .attr("transform", "rotate(-65) translate(-15,-10)");

            // Add y-axis
            svg.append("g")
                .call(d3.axisLeft(y).tickSize(0).tickFormat(""))
                .selectAll(".domain")
                .attr("stroke", "#ddd");

            // Add vertical line at x=0
            svg.append("line")
                .attr("x1", x(0))
                .attr("y1", 0)
                .attr("x2", x(0))
                .attr("y2", height)
                .attr("stroke", "#000")
                .attr("stroke-width", 1);

            // Add points and confidence intervals
            validData.forEach(d => {
                const beta = d.association.beta;
                const se = d.association.se;
                const yPos = y(d.trait_name) + y.bandwidth() / 2;

                // Add confidence interval line
                svg.append("line")
                    .attr("x1", x(beta - 1.96 * se))
                    .attr("y1", yPos)
                    .attr("x2", x(beta + 1.96 * se))
                    .attr("y2", yPos)
                    .attr("stroke", beta > 0 ? "#afe1af" : "#ee4b2b")
                    .attr("stroke-width", 2);

                // Add point estimate
                svg.append("circle")
                    .attr("cx", x(beta))
                    .attr("cy", yPos)
                    .attr("r", 4)
                    .attr("fill", beta > 0 ? "#afe1af" : "#ee4b2b");

                // Add tooltip
                svg.append("title")
                    .text(`Beta: ${beta.toExponential(2)}\nSE: ${se.toExponential(2)}`);
            });

            // Add axis labels
            svg.append("text")
                .attr("transform", `translate(${width/2}, ${height + margin.bottom})`)
                .style("text-anchor", "middle")
                .style("font-size", "12px")
                .text("Effect Size (Beta)");
        },

        getManhattanPlotOverlay() {
            d3.select("#manhattan-plot").selectAll("*").remove();

            const width = document.getElementById("manhattan-plot").clientWidth;
            const originalSvgWidth = 1000;
            const height = 200;
            const margin = {top: 30, right: 30, bottom: 50, left: 20};

            const minBP = this.data.variant.min_bp / 1e6;
            const maxBP = this.data.variant.max_bp / 1e6;

            // Set up scales
            const x = d3.scaleLinear()
                .domain([minBP, maxBP])
                .range([margin.left, width - margin.right]);

            // Create SVG
            const svg = d3.select("#manhattan-plot")
                .append("svg")
                .attr("width", width)
                .attr("height", height);

            // Add axes
            svg.append("g")
                .attr("transform", `translate(0,${height - margin.bottom})`)
                .call(d3.axisBottom(x)
                    .ticks((maxBP - minBP) / 0.1) // one tick every 0.1 Mb
                    .tickFormat(d3.format(".1f"))
                );
            svg.append("text")
                .attr("x", width / 2)
                .attr("y", height - 10)
                .attr("text-anchor", "middle")
                .text(`CHR ${this.data.variant.chr}`);

            // Draw a thin red vertical line at the variant position
            const variantMb = this.data.variant.bp / 1e6;
            const variantX = x(variantMb);
            svg.append("line")
                .attr("x1", variantX)
                .attr("x2", variantX)
                .attr("y1", margin.top)
                .attr("y2", height - margin.bottom)
                .attr("stroke", "red")
                .attr("stroke-width", 0.8)
                .attr("opacity", 0.8);
            

            this.filteredData.svgs.forEach(({ studyExtractionId, svgContent }, i) => {
                let parser = new DOMParser();
                let doc = parser.parseFromString(svgContent, "image/svg+xml");
                let importedSvg = doc.documentElement;

                // Remove width/height to allow scaling
                importedSvg.removeAttribute("width");
                importedSvg.removeAttribute("height");
                importedSvg.setAttribute("preserveAspectRatio", "xMidYMid meet");
                importedSvg.setAttribute("viewBox", `0 0 ${originalSvgWidth} ${height}`);

                if (this.highlightedStudy === studyExtractionId) {
                    importedSvg.querySelectorAll('g, path').forEach(element => {
                        element.removeAttribute('class');
                        element.removeAttribute('style');
                        element.setAttribute('fill', '#1976d2');
                        element.setAttribute('stroke', '#1976d2');
                        element.setAttribute('opacity', '0.9');
                    });
                } else {
                    importedSvg.querySelectorAll('g, path').forEach(element => {
                        element.removeAttribute('class');
                        element.removeAttribute('style');
                        element.setAttribute('opacity', '0.4');
                    });
                }
                let g = document.createElementNS("http://www.w3.org/2000/svg", "g");

                while (importedSvg.childNodes.length > 0) {
                    g.appendChild(importedSvg.childNodes[0]);
                }

                // Scale SVG to fit the D3 plot area
                const plotWidth = width - margin.left - margin.right;
                const plotHeight = height - margin.top - margin.bottom;
                const scaleX = plotWidth / originalSvgWidth;
                const scaleY = plotHeight / height;
                g.setAttribute("transform", `translate(${margin.left},${margin.top}) scale(${scaleX},${scaleY})`);

                svg.node().appendChild(g);
            });

            // Add and update the dynamic marker text
            const markerTextElement = svg.append("text")
                .attr("id", "highlighted-marker")
                .attr("x", margin.left)
                .attr("y", margin.top)
                .attr("text-anchor", "start")
                .attr("font-size", "18px")
                .attr("font-weight", "bold")
                .attr("fill", "#000")
                .text(""); // Start empty

            if (this.highlightedStudy) {
                const study = this.data.coloc_groups.find(d => d.study_extraction_id === this.highlightedStudy);
                if (study) {
                    let traitName = study.trait_name;
                    const pValueText = `: p = ${study.min_p.toExponential(2)}`;
                    markerTextElement.text(`${traitName}${pValueText}`);

                    const plotWidth = width - margin.left - margin.right;
                    
                    // Truncate text if it overflows the plot width
                    while (markerTextElement.node().getBBox().width > plotWidth && traitName.length > 3) {
                        traitName = traitName.slice(0, -1);
                        markerTextElement.text(`${traitName}...${pValueText}`);
                    }
                }
            }
        }
    }
} 