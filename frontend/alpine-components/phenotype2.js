import * as d3 from 'd3';
import constants from './constants.js'
import JSZip from 'jszip';

export default function pheontype() {
    return {
        userUpload: false,
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
        svgs: {
            metadata: null,
            full: null,
            chromosomes: {}
        },

        async loadData() {
            let traitId = (new URLSearchParams(location.search).get('id'))
            let traitUrl = constants.apiUrl + '/traits/' + traitId

            if (traitId && traitId.includes('-')) {
                this.userUpload = true
                traitUrl = constants.apiUrl + '/gwas/' + traitId
            }

            try {
                await this.getSvgData(traitId)
                const response = await fetch(traitUrl)
                if (!response.ok) {
                    this.errorMessage = `Failed to load data: ${response.status} ${response.statusText}`
                    return
                }
 
                this.data = await response.json()

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

        async getSvgData(traitId) {
            if (constants.isLocal) {
                traitId = 'full_gwas'
            }

            const metadataUrl = `${constants.assetBaseUrl}/${traitId}_metadata.json`
            const svgsUrl = `${constants.assetBaseUrl}/${traitId}_svgs.zip`

            this.svgs.metadata = await fetch(metadataUrl)
            this.svgs.metadata = await this.svgs.metadata.json()

            const zipResponse = await fetch(svgsUrl)
            const zipBlob = await zipResponse.blob()
            const zip = await JSZip.loadAsync(zipBlob)

            for (const [filename, file] of Object.entries(zip.files)) {
                if (filename.endsWith('.svg')) {
                    const svgContent = await file.async('text')
                    if (filename.includes('_chr')) {
                        // Extract chromosome number from filename
                        const chrNum = filename.match(/_chr(\d+)\.svg/)[1]
                        this.svgs.chromosomes[`chr${chrNum}`] = svgContent
                    } else {
                        // This is the full genome SVG
                        this.svgs.full = svgContent
                    }
                }
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
                clearTimeout(this.resizeTimer);
                this.resizeTimer = setTimeout(() => {
                    this.getPhenotypeGraph();
                }, 250);
            });
            
            setTimeout(() => {
                this.getPhenotypeGraph();
            }, 0);
        },

        //overlay options: https://codepen.io/hanconsol/pen/bGPBGxb
        //splitting into chromosomes, using scaleBand: https://stackoverflow.com/questions/65499073/how-to-create-a-facetplot-in-d3-js
        // looks cool: https://nvd3.org/examples/scatter.html //https://observablehq.com/@d3/splom/2?intent=fork

        getPhenotypeGraph() {
            const chartContainer = document.getElementById("phenotype-chart");
            const resetButton = document.getElementById("reset-zoom");
            chartContainer.innerHTML = ''; // Clear existing content
        
            let self = this;
            let currentView = "full"; // Track current view state
            let currentChr = null; // Track currently selected chromosome
            
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
            const aspectRatio = this.svgs.metadata.svg_height / this.svgs.metadata.svg_width;
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
        
            // Create a foreignObject to properly embed the SVG
            const foreignObject = plotGroup.append("foreignObject")
                .attr("width", width)
                .attr("height", height)
                .attr("overflow", "hidden");
        
            function loadSvg(specificSvg) {
                foreignObject.selectAll("*").remove();
                const parser = new DOMParser();
                const svgDoc = parser.parseFromString(specificSvg, "image/svg+xml");
                const importedSvg = svgDoc.documentElement;
                
                // Remove width/height attributes to allow scaling
                importedSvg.removeAttribute("width")
                importedSvg.removeAttribute("height")
                importedSvg.setAttribute("preserveAspectRatio", "xMidYMid meet")
                importedSvg.setAttribute("viewBox", `0 0 ${self.svgs.metadata.svg_width} ${self.svgs.metadata.svg_height}`)
                importedSvg.style.pointerEvents = "none"; // Make the SVG non-interactive

                // Append the SVG to foreignObject
                foreignObject.node().appendChild(importedSvg);
            }

            loadSvg(this.svgs.full)
        
            // Add chromosome backgrounds for ALL chromosomes
            const chrBackgrounds = plotGroup.append("g")
                .attr("class", "chr-backgrounds")
                .style("pointer-events", "all"); // Ensure backgrounds are clickable
        
            this.svgs.metadata.x_axis.forEach((chr, i) => {
                const xStart = (chr.pixel_start / this.svgs.metadata.svg_width) * width;
                const xEnd = (chr.pixel_end / this.svgs.metadata.svg_width) * width;
                chrBackgrounds.append("rect")
                    .datum(chr)  // Bind the chromosome data to the rectangle
                    .attr("x", xStart)
                    .attr("y", 0)
                    .attr("width", xEnd - xStart)
                    .attr("height", height)
                    .attr("fill", i % 2 === 0 ? "#e5e5e5" : "#ffffff")  // Alternating colors
                    .attr("opacity", 0.5)
                    .style("cursor", "pointer")
                    .on('mouseover', function() {
                        if (currentView === "full") {
                            d3.select(this)
                                .transition()
                                .duration(200)
                                .attr("fill", "#e6f3ff");  // Light blue on hover
                        }
                    })
                    .on('mouseout', function() {
                        if (currentView === "full") {
                            d3.select(this)
                                .transition()
                                .duration(200)
                                .attr("fill", i % 2 === 0 ? "#e5e5e5" : "#ffffff");  // Return to original color
                        }
                    })
                    .on('click', function(d) {
                        if (currentView === "full") {
                            zoomToChromosome({CHR: chr.CHR});
                        }
                    });
            });
        
            // Create scales
            const xScale = d3.scaleLinear()
                .domain([0, this.svgs.metadata.x_axis[this.svgs.metadata.x_axis.length - 1].bp_end])
                .range([0, width]);
        
            const yScale = d3.scaleLinear()
                .domain([this.svgs.metadata.y_axis.min_lp, this.svgs.metadata.y_axis.max_lp])
                .range([height, 0]);
        
            // Add X axis
            const xAxis = d3.axisBottom(xScale)
                .ticks(0)  // Remove all ticks
                .tickSize(0);  // Remove tick lines
        
            const xAxisGroup = plotGroup.append("g")
                .attr("transform", `translate(0,${height})`)
                .call(xAxis);
        
            // Add X axis label
            const xAxisLabel = plotGroup.append("text")
                .attr("x", width / 2)
                .attr("y", height + 40)
                .style("text-anchor", "middle")
                .style("font-size", "14px")
                .text("Chromosome");
        
            // Add Y axis
            const yAxis = d3.axisLeft(yScale)
                .ticks(10)
                .tickFormat(d => d);
        
            const yAxisGroup = plotGroup.append("g")
                .call(yAxis)
                .selectAll("text")
                .style("text-anchor", "end")
                .style("font-size", "12px");
        
            // Add Y axis label
            const yAxisLabel = plotGroup.append("text")
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

            this.svgs.metadata.x_axis.forEach(chr => {
                const xPos = ((chr.pixel_start + chr.pixel_end) / 2 / this.svgs.metadata.svg_width) * width;
                chrLabels.append("text")
                    .attr("x", xPos)
                    .attr("y", height + 20)
                    .style("text-anchor", "middle")
                    .style("font-size", "10px")
                    .text(chr.CHR);
            });
        
            // Store coloc circles in a group for easy manipulation
            const colocCirclesGroup = plotGroup.append("g")
                .attr("class", "coloc-circles");
        
            // Function to draw coloc circles
            function drawColocCircles() {
                // Clear existing circles
                colocCirclesGroup.selectAll("*").remove();
        
                if (self.filteredGroupedColoc) {
                    const allGroups = Object.values(self.filteredGroupedColoc);
                    allGroups.forEach(group => {
                        // Find the relevant study for the current trait_id
                        const traitId = self.data.trait.id;
                        const study = group.find(s => s.trait_id === traitId);
                        if (!study) return;
                        
                        // Skip if we're in chromosome view and this isn't the selected chromosome
                        if (currentView === "chromosome" && study.chr != currentChr) return;
                        
                        // Find the chromosome metadata
                        const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == study.chr);
                        if (!chrMeta) return;
                        
                        // Convert bp to pixel (linear interpolation)
                        const chrLength = chrMeta.bp_end - chrMeta.bp_start;
                        const bpRatio = study.bp / chrLength;
                        const xPixel = (chrMeta.pixel_start + (bpRatio * (chrMeta.pixel_end - chrMeta.pixel_start))) / self.svgs.metadata.svg_width * width;
                        
                        const yValue = -Math.log10(study.min_p);
                        const yPixel = yScale(yValue);
                        
                        // Draw the circle
                        colocCirclesGroup.append("circle")
                            .datum(study)  // Bind the study data to the circle
                            .attr("cx", xPixel)
                            .attr("cy", yPixel)
                            .attr("r", Math.min(group.length + 2, 20))  // Base size on number of elements in group
                            .attr("fill", "#1976d2")
                            .attr("stroke", "#fff")
                            .attr("stroke-width", 1.5)
                            .attr("opacity", 0.8)
                            .on('mouseover', function(event, d) {
                                d3.select(this).style("cursor", "pointer"); 
        
                                let allTraits = group.map(s => s.trait_name)
                                let uniqueTraits = [...new Set(allTraits)]
                                let traitNames = uniqueTraits.slice(0,9)
                                traitNames = traitNames.join("<br />")
                                if (uniqueTraits.length > 10) traitNames += "<br /> " + (uniqueTraits.length - 10) + " more..."
                                traitNames = 'SNP: ' + d.candidate_snp + '<br />' + traitNames
        
                                d3.select(this).transition()
                                    .duration('100')
                                    .attr("r", Math.min(group.length + 2, 20) + 8)  // Increase size on hover
                                tooltip.transition()
                                    .duration(100)
                                    .style("opacity", 1)
                                    .style("visibility", "visible")
                                    .style("display", "flex");
                                tooltip.html(traitNames)
                                    .style("left", (event.pageX + 10) + "px")
                                    .style("top", (event.pageY - 15) + "px");
                            })
                            .on('mouseout', function () {
                                d3.select(this).transition()
                                    .duration('200')
                                    .attr("r", Math.min(group.length + 2, 20))  // Return to original size
                                tooltip.transition()
                                    .duration(100)
                                    .style("visibility", "hidden")
                                    .style("display", "none");
                            })
                            .on('click', function(event, d) {
                                if (currentView === "full") {
                                    self.displayFilters.chr = d.chr;
                                    self.displayFilters.candidate_snp = null;
                                    zoomToChromosome({CHR: d.chr});
                                } else {
                                    self.displayFilters.candidate_snp = d.candidate_snp;
                                    self.displayFilters.chr = null;
                                }
                            });
                    });
                }
            }
        
            // Initial draw of coloc circles
            drawColocCircles();
        
            // Function to zoom to a specific chromosome
            function zoomToChromosome(chrData) {
                currentView = "chromosome";
                currentChr = chrData.CHR;
                const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == chrData.CHR);
                const chrSvg = self.svgs.chromosomes[`chr${chrData.CHR}`];

                loadSvg(chrSvg)

                // Update x-scale domain to this chromosome's bp range
                xScale.domain([chrMeta.bp_start, chrMeta.bp_end])
                       .range([0, width]);
                
                // Update x-axis
                xAxisGroup.transition()
                    .duration(500)
                    .call(xAxis.scale(xScale));
                
                // Update x-axis label
                xAxisLabel.text(`Chromosome ${chrData.CHR} Position (bp)`);
                
                // Update chromosome background
                chrBackgrounds.selectAll("rect")
                    .transition()
                    .duration(500)
                    .attr("opacity", 0);
                
                chrBackgrounds.selectAll("rect")
                    .filter(d => d.CHR == chrData.CHR)
                    .transition()
                    .duration(500)
                    .attr("x", 0)
                    .attr("width", width)
                    .attr("opacity", 0.5);
                
                // Update chromosome labels
                chrLabels.selectAll("text")
                    .transition()
                    .duration(500)
                    .attr("opacity", 0);
                
                // Update reference lines
                referenceLines.selectAll("line")
                    .transition()
                    .duration(500)
                    .attr("x2", width);
                
                // Reposition coloc circles
                colocCirclesGroup.selectAll("circle")
                    .transition()
                    .duration(500)
                    .attr("opacity", d => d.chr == chrData.CHR ? 1 : 0)
                    .attr("cx", d => {
                        const circleChrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == d.chr);
                        const bpPosition = (d.bp) / (circleChrMeta.bp_end - circleChrMeta.bp_start);
                        return bpPosition * width;
                    });
                
                // Show the reset button
                resetButton.style.display = "block";
            }
            
            function resetZoom() {
                currentView = "full";
                currentChr = null;

                loadSvg(self.svgs.full)
                
                // Reset x-scale to full genome
                xScale.domain([0, self.svgs.metadata.x_axis[self.svgs.metadata.x_axis.length - 1].bp_end])
                    .range([0, width]);
                
                // Reset x-axis
                xAxisGroup.transition()
                    .duration(500)
                    .call(xAxis.scale(xScale));
                
                // Reset x-axis label
                xAxisLabel.text("Chromosome");
                
                // Reset chromosome backgrounds
                self.svgs.metadata.x_axis.forEach((chr, i) => {
                    const xStart = (chr.pixel_start / self.svgs.metadata.svg_width) * width;
                    const xEnd = (chr.pixel_end / self.svgs.metadata.svg_width) * width;
                    
                    chrBackgrounds.selectAll("rect")
                        .filter(d => d.CHR == chr.CHR)
                        .transition()
                        .duration(500)
                        .attr("x", xStart)
                        .attr("width", xEnd - xStart)
                        .attr("fill", i % 2 === 0 ? "#e5e5e5" : "#ffffff")
                        .attr("opacity", 0.5);
                });
                
                // Reset chromosome labels
                chrLabels.selectAll("text")
                    .transition()
                    .duration(500)
                    .attr("opacity", 1)
                    .attr("x", (d, i) => {
                        const chr = self.svgs.metadata.x_axis[i];
                        return ((chr.pixel_start + chr.pixel_end) / 2 / self.svgs.metadata.svg_width) * width;
                    });
                
                // Reset reference lines
                referenceLines.selectAll("line")
                    .transition()
                    .duration(500)
                    .attr("x2", width);
                
                // Reset coloc circles positions
                colocCirclesGroup.selectAll("circle")
                    .transition()
                    .duration(500)
                    .attr("opacity", 1)
                    .attr("cx", d => {
                        const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == d.chr);
                        
                        // Calculate original pixel position
                        const bpRatio = (d.bp) / (chrMeta.bp_end - chrMeta.bp_start);
                        const chrPixelWidth = chrMeta.pixel_end - chrMeta.pixel_start;
                        const pixelPos = chrMeta.pixel_start + (bpRatio * chrPixelWidth);
                        
                        // Convert to view coordinates
                        return (pixelPos / self.svgs.metadata.svg_width) * width;
                    });
                
                // Hide the reset button
                resetButton.style.display = "none";
            }
        
            // Add reset button event listener
            resetButton.addEventListener("click", resetZoom);
        }
    }
}
