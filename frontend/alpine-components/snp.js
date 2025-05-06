import Alpine from 'alpinejs'
import * as d3 from "d3";
import constants from './constants.js'
import downloads from './downloads.js'

export default function snp() {
    return {
        data: null,
        errorMessage: null,

        async loadData() {
            // Extract SNP ID from the URL path
            const pathParts = window.location.pathname.split('/');
            const snpId = pathParts[pathParts.length - 1];
            const requestUrl = constants.apiUrl + '/snps/' + snpId;

            try {
                const response = await fetch(requestUrl);
                if (!response.ok) {
                    this.errorMessage = `Failed to load data: ${response.status} ${response.statusText}`;
                    return;
                }
                
                this.data = await response.json();

                this.data.colocs = this.data.colocs.map(coloc => ({
                    ...coloc,
                    tissue: coloc.tissue ? coloc.tissue : "N/A",
                    cis_trans: coloc.cis_trans? coloc.cis_trans : "N/A"
                })) 
                this.data.colocs.sort((a, b) => a.data_type.localeCompare(b.data_type));

                this.filterByOptions(Alpine.store('graphOptionStore'));
                this.initForestPlot();
            } catch (error) {
                console.error('Error loading data:', error);
            }
        },

        getSNPName() {
            return this.data ? this.data.variant.rsid.split(',')[0] : '...'
        },

        getVariantData() {
            return this.data ? this.data.variant : {};
        },

        getDataForTable() {
            return this.data ? this.data.filteredColocs: [];
        },

        downloadData() {
            if (!this.data || !this.data.colocs || this.data.colocs.length === 0) {
                return;
            }
            
            const filename = `${this.getSNPName()}_coloc_data.csv`;
            
            downloads.downloadColocsToCSV(
                this.data.variant,
                this.data.filteredColocs,
                filename
            );
        },

        filterByOptions(graphOptions) {
            this.data.filteredColocs = this.data.colocs.filter(coloc => {
                return(coloc.min_p <= graphOptions.pValue &&
                    coloc.posterior_prob >= graphOptions.coloc &&
                    (graphOptions.includeTrans ? true : coloc.cis_trans !== 'trans') &&
                    (graphOptions.onlyMolecularTraits ? coloc.data_type !== 'phenotype' : true)
                )
            });
            this.data.filteredColocs.sort((a, b) => a.association.beta - b.association.beta);
            this.initForestPlot();
        },

        initChordDiagram() {
                if (!this.data) {
                        const chartContainer = document.getElementById("snp-chord-diagram");
                        chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>';
                        return;
                }

                const graphOptions = Alpine.store('graphOptionStore');
                this.filterByOptions(graphOptions);
                window.addEventListener('resize', () => {
                        // Debounce the resize event to prevent too many redraws
                        clearTimeout(this.resizeTimer);
                        this.resizeTimer = setTimeout(() => {
                                this.getChordDiagram();
                        }, 250); // Wait for 250ms after the last resize event
                });
                this.getChordDiagram();
        },

        getChordDiagram() {
            if (!this.data) return;
            const self = this;
            const chartElement = document.getElementById('snp-chord-diagram');
            chartElement.innerHTML = '';

            const chartContainer = d3.select("#snp-chord-diagram");
            chartContainer.select("svg").remove();
            let graphWidth = chartContainer.node().getBoundingClientRect().width - 50
            let graphHeight = 600

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
            const candidate_snp = this.data.variant.RSID;
            const colocs = this.data.filteredColocs;

            // Extract unique data_types
            const dataTypes = Array.from(new Set(colocs.map(d => d.data_type)));

            // Extract unique traits
            const traits = colocs.map(d => d.trait_name);

            // Combine candidate_snp and traits into nodes
            const nodes = [candidate_snp, ...traits];

            // Create data_type mapping for coloring
            const dataTypeMap = {};
            colocs.forEach(coloc => {
                dataTypeMap[coloc.trait_name] = coloc.data_type;
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
            colocs.forEach(coloc => {
                const source = indexMap[candidate_snp];
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
                    const coloc = self.data.filteredColocs.find(coloc => coloc.trait_name === nodes[d.target.index]);
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

        initForestPlot() {
            if (!this.data || !this.data.filteredColocs) return;

            const plotContainer = d3.select("#forest-plot");
            plotContainer.selectAll("*").remove();

            const margin = { top: 50, right: 20, bottom: 40, left: 10 };
            // const width = 300 - margin.left - margin.right;
            let width = plotContainer.node().getBoundingClientRect().width;
            const height = this.data.filteredColocs.length * 27;

            const svg = plotContainer.append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);

            // Filter out items without association data
            const validData = this.data.filteredColocs.filter(d => d.association && d.association.beta !== null && d.association.se !== null);
            
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
        }
    }
} 