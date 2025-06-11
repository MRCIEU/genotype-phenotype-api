import * as d3 from 'd3';
import constants from './constants.js'


export default function pheontype() {
    return {
        userUpload: false,
        svgMetadata: null,
        svg: null,
        data: null,
        filteredColocData: null,
        filteredGroupedColoc: null,
        orderedTraitsToFilterBy: null,
        displayFilters: {
            chr: null,
            candidate_snp: null,
            trait: null
        },
        errorMessage: null,

        async loadData() {
            let traitId = (new URLSearchParams(location.search).get('id'))
            let requestUrl = constants.apiUrl + '/traits/' + traitId

            if (traitId && traitId.includes('-')) {
                this.userUpload = true
                requestUrl = constants.apiUrl + '/gwas/' + traitId
            }

            try {
                const response = await fetch(requestUrl)
                if (!response.ok) {
                    this.errorMessage = `Failed to load data: ${response.status} ${response.statusText}`
                    return
                }
                
                this.data = await response.json()

                this.svgMetadata = await fetch('/assets/images/manhattan_plot_metadata_hemoglobin.json')
                this.svgMetadata = await this.svgMetadata.json()

                this.svg = await fetch('/assets/images/manhattan_plot_hemoglobin.svg')
                this.svg = await this.svg.text()

                // Count frequency of each id in colocs and scale between 2 and 10
                const [scaledMinNumStudies, scaledMaxNumStudies] = [2,10]
                const idFrequencies = this.data.colocs.reduce((acc, obj) => {
                    if (obj.coloc_group_id) {
                        acc[obj.coloc_group_id] = (acc[obj.coloc_group_id] || 0) + 1;
                    }
                    return acc;
                }, {});

                // Get min and max frequencies
                const frequencies = Object.values(idFrequencies);
                const minNumStudies = Math.min(...frequencies);
                const maxNumStudies = Math.max(...frequencies);

                this.data.study_extractions = this.data.study_extractions.map(se => {
                    se.MbP = se.bp / 1000000
                    se.chrText = 'CHR '.concat(se.chr)
                    se.ignore = false
                    return se
                })
                this.data.rare_results = this.data.rare_results.map(r => {
                    r.MbP = r.bp / 1000000
                    r.chrText = 'CHR '.concat(r.chr)
                    r.ignore = false
                    return r
                })
                this.data.colocs = this.data.colocs.map(c => {
                    c.MbP = c.bp / 1000000
                    c.chrText = 'CHR '.concat(c.chr)
                    c.annotationColor = constants.colors[Math.floor(Math.random()*Object.keys(constants.colors).length)]
                    c.ignore = false
                    if (minNumStudies === maxNumStudies) {
                        c.scaledNumStudies = 4 
                    } else {
                        c.scaledNumStudies = ((idFrequencies[c.coloc_group_id] - minNumStudies) / (maxNumStudies - minNumStudies)) * (scaledMaxNumStudies- scaledMinNumStudies) + scaledMinNumStudies 
                    }
                    return c
                })
                this.data.colocs.sort((a, b) => a.chr > b.chr);

                // order traits by frequency in order to display in dropdown for filtering
                let allTraits = this.data.colocs.map(c => c.trait)
                let frequency = {};
                allTraits.forEach(item => {
                    frequency[item] = (frequency[item] || 0) + 1;
                });

                // sort by frequency
                let uniqueTraits = [...new Set(allTraits)];
                uniqueTraits.sort((a, b) => frequency[b] - frequency[a]);

                this.orderedTraitsToFilterBy = uniqueTraits.filter(t => t !== this.data.trait.trait)

                this.filterByOptions(Alpine.store('graphOptionStore')) 

            } catch (error) {
                console.error('Error loading data:', error);
            }
        },

        get showResults() {
            if (this.data === null) return false
            if (this.userUpload) return this.data.trait.status === 'completed'
            return true
        },

        get getStudyToDisplay() {
            let text = 'Trait: '
            if (this.data === null) return text + '...'
            if (this.userUpload) {
                return 'GWAS Upload: ' + this.data.trait.name
            }

            return text + this.data.trait.trait_name
        },

        get getUploadStatus() {
            let text = 'Status: '
            if (this.data === null) return text + '...'
            return text + this.data.trait.status
        },

        filterByOptions(graphOptions) {
            let colocIdsWithTraits = []
            if (this.displayFilters.trait) {
                colocIdsWithTraits = this.data.colocs.filter(c => c.trait === this.displayFilters.trait).map(c => c.coloc_group_id)
            } 
            this.filteredColocData = this.data.colocs.filter(coloc => {
                let graphOptionFilters = ((coloc.min_p <= graphOptions.pValue &&
                    coloc.posterior_prob >= graphOptions.coloc &&
                    (graphOptions.includeTrans ? true : coloc.cis_trans !== 'trans') &&
                    (coloc.trait_id === this.data.trait.id ||
                        (graphOptions.traitType === 'all' ? true : 
                        graphOptions.traitType === 'molecular' ? coloc.data_type !== 'phenotype' :
                        graphOptions.traitType === 'phenotype' ? coloc.data_type === 'phenotype' : true))
                    )
                )

                if (Object.values(graphOptions.categories).some(c => c)) {
                    graphOptionFilters = graphOptionFilters && (graphOptions.categories[coloc.trait_category] === true || coloc.trait_id === this.data.trait.id)
                }

                const traitFilter = this.displayFilters.trait ? colocIdsWithTraits.includes(coloc.coloc_group_id) : true

                return graphOptionFilters && traitFilter
            })
            // this.filteredRareResults = this.data.rare_results.filter(r => r.min_p <= graphOptions.pValue)
            this.filteredRareResults = this.data.rare_results
            this.filteredStudyExtractions = this.data.study_extractions.filter(se => {
                let graphOptionFilters = (se.min_p <= graphOptions.pValue &&
                    (graphOptions.includeTrans ? true : se.cis_trans !== 'trans') &&
                    (graphOptions.onlyMolecularTraits ? se.data_type !== 'phenotype' : true)
                )
                if (Object.values(graphOptions.categories).some(c => c)) {
                    graphOptionFilters = graphOptionFilters && graphOptions.categories[se.trait_category] === true
                }

                return graphOptionFilters
            })

            // deduplicate studies and sort based on frequency
            this.filteredGroupedColoc = Object.groupBy(this.filteredColocData, ({ candidate_snp }) => candidate_snp);
            // Filter out groups with only one element
            this.filteredGroupedColoc = Object.fromEntries(
                Object.entries(this.filteredGroupedColoc).filter(([_, group]) => group.length > 1)
            );
        },

        filterByStudy(trait) {
            if (trait === null) {
                this.filteredColocData = this.data
            } else {
                this.displayFilters =    {
                    chr: null,
                    candidate_snp: null,
                    trait: trait
                }
                this.filterByOptions(Alpine.store('graphOptionStore'))
            }
        },

        removeDisplayFilters() {
            this.displayFilters = {
                chr: null,
                candidate_snp: null,
                trait: null
            }
        },

        get getDataForColocTable() {
            if (!this.filteredColocData || this.filteredColocData.length === 0) return []
            let tableData = this.filteredColocData.filter(coloc => {
                if (this.displayFilters.chr !== null) return coloc.chr == this.displayFilters.chr
                else if (this.displayFilters.candidate_snp !== null) return coloc.candidate_snp === this.displayFilters.candidate_snp 
                else return true
            })

            tableData.forEach(coloc => {
                const hash = [...coloc.candidate_snp].reduce((hash, char) => (hash * 31 + char.charCodeAt(0)) % constants.tableColors.length, 0)
                coloc.color = constants.tableColors[hash]
            })

            this.filteredGroupedColoc = Object.groupBy(tableData, ({ candidate_snp }) => candidate_snp);

            return Object.fromEntries(Object.entries(this.filteredGroupedColoc).slice(0, 100))
        },

        initPhenotypeGraph() {
            if (this.errorMessage) {
                const chartContainer = document.getElementById("phenotype-chart");
                chartContainer.innerHTML = '<div class="notification is-danger is-light mt-4">' + this.errorMessage + '</div>'
                return
            }
            else if (this.filteredColocData === null) {
                const chartContainer = document.getElementById("phenotype-chart");
                chartContainer.innerHTML = '<progress class="progress is-large is-info" max="100">60%</progress>'
                return
            }

            // Ensure the container is visible before proceeding
            const waitToLoad = document.getElementById("wait-to-load");
            if (waitToLoad) {
                waitToLoad.style.display = "block";
            }

            const graphOptions = Alpine.store('graphOptionStore')
            this.filterByOptions(graphOptions)
            
            // Add resize listener when initializing the graph
            window.addEventListener('resize', () => {
                // Debounce the resize event to prevent too many redraws
                clearTimeout(this.resizeTimer);
                this.resizeTimer = setTimeout(() => {
                    this.getPhenotypeGraph();
                }, 250); // Wait for 250ms after the last resize event
            });
            
            // Small delay to ensure DOM is updated
            setTimeout(() => {
                this.getPhenotypeGraph();
            }, 0);
        },

        //overlay options: https://codepen.io/hanconsol/pen/bGPBGxb
        //splitting into chromosomes, using scaleBand: https://stackoverflow.com/questions/65499073/how-to-create-a-facetplot-in-d3-js
        // looks cool: https://nvd3.org/examples/scatter.html //https://observablehq.com/@d3/splom/2?intent=fork

        getPhenotypeGraph() {
            const chartContainer = document.getElementById("phenotype-chart");
            chartContainer.innerHTML = ''; // Clear existing content

            let self = this
            // Remove any existing tooltips first
            d3.selectAll(".tooltip").remove();

            // Create a single tooltip that will be reused
            const tooltip = d3.select("body").append("div")
                .attr("class", "tooltip")
                .style("opacity", 0)
                .style("position", "absolute")
                .style("background-color", "white")
                .style("border", "1px solid #ddd")
                .style("padding", "10px")
                .style("border-radius", "5px")
                .style("pointer-events", "none")
                .style("z-index", "1000")
                .on('mouseover', function() {
                    d3.select(this)
                        .style("opacity", 1)
                        .style("visibility", "visible")
                        .style("display", "flex");
                })
                .on('mouseout', function() {
                    d3.select(this)
                        .transition()
                        .duration(100)
                        .style("visibility", "hidden")
                        .style("display", "none");
                });
        
            // Define margins
            const margin = { top: 20, right: 20, bottom: 60, left: 80 };
        
            // Get container dimensions
            const containerWidth = chartContainer.clientWidth;
            const aspectRatio = this.svgMetadata.svg_height / this.svgMetadata.svg_width;
            const width = containerWidth - margin.left - margin.right;
            const height = width * aspectRatio;
        
            // Create SVG container
            const svg = d3.select(chartContainer)
                .append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`);
        
            // Create main plot group
            const plotGroup = svg.append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);

            // Add alternating chromosome backgrounds
            const chrBackgrounds = plotGroup.append("g")
                .attr("class", "chr-backgrounds");

            this.svgMetadata.x_axis.forEach((chr, i) => {
                if (i % 2 === 0) {  // Only add background for even-numbered chromosomes
                    const xStart = (chr.pixel_start / this.svgMetadata.svg_width) * width;
                    const xEnd = (chr.pixel_end / this.svgMetadata.svg_width) * width;
                    chrBackgrounds.append("rect")
                        .attr("x", xStart)
                        .attr("y", 0)
                        .attr("width", xEnd - xStart)
                        .attr("height", height)
                        .attr("fill", "#e5e5e5")  // Very light grey
                        .attr("opacity", 0.5);
                }
            });

            // Create a foreignObject to properly embed the SVG
            const foreignObject = plotGroup.append("foreignObject")
                .attr("width", width)
                .attr("height", height);
        
            // Parse the SVG string and set its dimensions
            const parser = new DOMParser();
            const svgDoc = parser.parseFromString(this.svg, "image/svg+xml");
            const importedSvg = svgDoc.documentElement;
            
            // Remove width/height attributes to allow scaling
            importedSvg.removeAttribute("width");
            importedSvg.removeAttribute("height");
            importedSvg.setAttribute("preserveAspectRatio", "xMidYMid meet");
            importedSvg.setAttribute("viewBox", `0 0 ${this.svgMetadata.svg_width} ${this.svgMetadata.svg_height}`);
        
            // Append the SVG to foreignObject
            foreignObject.node().appendChild(importedSvg);

            // Create scales
            const xScale = d3.scaleLinear()
                .domain([0, this.svgMetadata.x_axis[this.svgMetadata.x_axis.length - 1].bp_end])
                .range([0, width]);

            const yScale = d3.scaleLinear()
                .domain([this.svgMetadata.y_axis.min_lp, this.svgMetadata.y_axis.max_lp])
                .range([height, 0]);

            // Add X axis
            const xAxis = d3.axisBottom(xScale)
                .ticks(0)  // Remove all ticks
                .tickSize(0);  // Remove tick lines

            plotGroup.append("g")
                .attr("transform", `translate(0,${height})`)
                .call(xAxis);

            // Add X axis label
            plotGroup.append("text")
                .attr("x", width / 2)
                .attr("y", height + 40)
                .style("text-anchor", "middle")
                .style("font-size", "14px")
                .text("Chromosome");

            // Add Y axis
            const yAxis = d3.axisLeft(yScale)
                .ticks(10)
                .tickFormat(d => d);

            plotGroup.append("g")
                .call(yAxis)
                .selectAll("text")
                .style("text-anchor", "end")
                .style("font-size", "12px");

            // Add Y axis label
            plotGroup.append("text")
                .attr("transform", "rotate(-90)")
                .attr("x", -height / 2)
                .attr("y", -50)
                .style("text-anchor", "middle")
                .style("font-size", "14px")
                .text("-log10(p-value)");

            // Add horizontal reference lines
            const referenceLines = plotGroup.append("g")
                .attr("class", "reference-lines");

            // Line at y=5
            referenceLines.append("line")
                .attr("x1", 0)
                .attr("x2", width)
                .attr("y1", yScale(5))
                .attr("y2", yScale(5))
                .attr("stroke", "darkred")
                .attr("opacity", 0.5)
                .attr("stroke-width", 0.5)
                .attr("stroke-dasharray", "5,5");

            // Line at y=7.3
            referenceLines.append("line")
                .attr("x1", 0)
                .attr("x2", width)
                .attr("y1", yScale(7.3))
                .attr("y2", yScale(7.3))
                .attr("stroke", "darkred")
                .attr("opacity", 0.5)
                .attr("stroke-width", 0.5)

            // Add chromosome labels
            const chrLabels = plotGroup.append("g")
                .attr("class", "chr-labels");

            this.svgMetadata.x_axis.forEach(chr => {
                const xPos = ((chr.pixel_start + chr.pixel_end) / 2 / this.svgMetadata.svg_width) * width;
                chrLabels.append("text")
                    .attr("x", xPos)
                    .attr("y", height + 20)
                    .style("text-anchor", "middle")
                    .style("font-size", "10px")
                    .text(chr.CHR);
            });

            // Add circles for grouped coloc data
            if (this.filteredGroupedColoc) {
                const allGroups = Object.values(this.filteredGroupedColoc);
                allGroups.forEach(group => {
                    // Find the relevant study for the current trait_id
                    const traitId = this.data.trait.id;
                    const study = group.find(s => s.trait_id === traitId);
                    if (!study) return;
                    // Find the chromosome metadata
                    const chrMeta = this.svgMetadata.x_axis.find(chr => chr.CHR == study.chr);
                    if (!chrMeta) return;
                    // Convert bp to pixel (linear interpolation)
                    const chrLength = chrMeta.bp_end - chrMeta.bp_start;
                    const bpRatio = study.bp / chrLength;
                    const xPixel = (chrMeta.pixel_start + (bpRatio * (chrMeta.pixel_end - chrMeta.pixel_start))) / this.svgMetadata.svg_width * width;
                    // Y axis: -log10(min_p)
                    const yValue = -Math.log10(study.min_p);
                    // Map yValue to pixel
                    const yPixel = yScale(yValue);
                    // Draw the circle
                    plotGroup.append("circle")
                        .attr("cx", xPixel)
                        .attr("cy", yPixel)
                        .attr("r", Math.min(group.length + 2, 20))  // Base size on number of elements in group
                        .attr("fill", "#1976d2")
                        .attr("stroke", "#fff")
                        .attr("stroke-width", 1.5)
                        .attr("opacity", 0.8)
                        .on('mouseover', function(d) {
                            d3.select(this).style("cursor", "pointer"); 

                            let allTraits = group.map(s => s.trait_name)
                            let uniqueTraits = [...new Set(allTraits)]
                            let traitNames = uniqueTraits.slice(0,9)
                            traitNames = traitNames.join("<br />")
                            if (uniqueTraits.length > 10) traitNames += "<br /> " + (uniqueTraits.length - 10) + " more..."
                            traitNames = 'SNP: ' + study.candidate_snp + '<br />' + traitNames

                            d3.select(this).transition()
                                .duration('100')
                                .attr("r", Math.min(group.length + 2, 20) + 8)  // Increase size on hover
                            tooltip.transition()
                                .duration(100)
                                .style("opacity", 1)
                                .style("visibiility", "visible")
                                .style("display", "flex");
                            tooltip.html(traitNames)
                                .style("left", (d.pageX + 10) + "px")
                                .style("top", (d.pageY - 15) + "px");
                        })
                        .on('mouseout', function () {
                            d3.select(this).transition()
                                .duration('200')
                                .attr("r", Math.min(group.length + 2, 20))  // Return to original size
                            tooltip.transition()
                                .duration(100)
                                .style("visibiility", "hidden")
                                .style("display", "none");
                        })
                        .on('click', function() {
                            self.displayFilters.candidate_snp = study.candidate_snp
                            self.displayFilters.chr = null
                        });
                });
            }
        }
    }
}
