import JSZip from 'jszip';
import * as d3 from 'd3';

import constants from './constants.js'
import downloads from './downloads.js';

export default function pheontype() {
    return {
        userUpload: false,
        data: null,
        filteredColocData: null,
        filteredGroupedColoc: null,
        showTables: {
            coloc: true,
            rare: true 
        },
        displayFilters: {
            view: "full",
            chr: null,
            candidate_snp: null,
            trait_name: null
        },
        traitSearch: {
            text: '',
            showDropDown: false,
            orderedTraits: null,
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
                    c.annotationColor = constants.colors.palette[Math.floor(Math.random()*constants.colors.palette.length)]
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
                let allTraits = this.data.colocs.map(c => c.trait_name)
                allTraits = allTraits.concat(this.data.rare_results.map(r => r.trait_name))
                let frequency = {};
                allTraits.forEach(item => {
                    frequency[item] = (frequency[item] || 0) + 1;
                });

                let uniqueTraits = [...new Set(allTraits)];
                uniqueTraits.sort((a, b) => frequency[b] - frequency[a]);
                this.traitSearch.orderedTraits = uniqueTraits.filter(t => t !== this.data.trait.trait_name)

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
                    if (filename.includes('chr')) {
                        // Extract chromosome number from filename
                        const chrNum = filename.match(/chr(\d+)\.svg/)[1]
                        this.svgs.chromosomes[`chr${chrNum}`] = svgContent
                    } else {
                        // This is the full genome SVG
                        this.svgs.full = svgContent
                    }
                }
            }
        },

        async downloadData() {
            await downloads.downloadDataToZip(this.data, 'phenotype');
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
            if (this.displayFilters.trait_name) {
                colocIdsWithTraits = this.data.colocs.filter(c => c.trait === this.displayFilters.trait_name).map(c => c.coloc_group_id)
            } 
            this.filteredColocData = this.data.colocs.filter(coloc => {
                let graphOptionFilters = ((coloc.min_p <= graphOptions.pValue &&
                    coloc.posterior_prob >= graphOptions.coloc &&
                    (graphOptions.includeTrans ? true : coloc.cis_trans !== 'trans') &&
                    (coloc.trait_id === this.data.trait.id ||
                        (graphOptions.traitType === 'all' ? true : 
                        graphOptions.traitType === 'molecular' ? coloc.data_type !== 'Phenotype' :
                        graphOptions.traitType === 'phenotype' ? coloc.data_type === 'Phenotype' : true))
                    )
                )
                let displayFilters = this.displayFilters.chr !== null ? coloc.chr == this.displayFilters.chr : true

                if (Object.values(graphOptions.categories).some(c => c)) {
                    graphOptionFilters = graphOptionFilters && (graphOptions.categories[coloc.trait_category] === true || coloc.trait_id === this.data.trait.id)
                }

                const traitFilter = graphOptionFilters && (
                    this.displayFilters.trait_name ? coloc.trait_name === this.displayFilters.trait_name : true
                ) || (
                    this.data.trait.id === coloc.trait_id
                )

                return graphOptionFilters && displayFilters && traitFilter
            })

            this.filteredRareResults = this.data.rare_results.filter(rare => {
                const traitFilter = this.displayFilters.trait_name ? rare.trait_name === this.displayFilters.trait_name : true
                const graphOptionFilters = (rare.min_p <= graphOptions.pValue && 
                    !graphOptions.includeTrans && 
                    (graphOptions.traitType === 'all' || graphOptions.traitType === 'phenotype')
                )
                return graphOptionFilters && traitFilter
            })

            this.filteredGroupedRareResults = Object.groupBy(this.filteredRareResults, ({candidate_snp}) => candidate_snp)
            this.filteredGroupedRareResults = Object.fromEntries(
                Object.entries(this.filteredGroupedRareResults).filter(([_, group]) => group.length > 1)
            );

            this.filteredGroupedColoc = Object.groupBy(this.filteredColocData, ({ candidate_snp }) => candidate_snp);
            this.filteredGroupedColoc = Object.fromEntries(
                Object.entries(this.filteredGroupedColoc).filter(([_, group]) => group.length > 1)
            );
        },

        getTraitsToFilterBy() {
            if (this.traitSearch.orderedTraits === null) return []
            return this.traitSearch.orderedTraits.filter(t => !this.traitSearch.text || t.toLowerCase().includes(this.traitSearch.text.toLowerCase()))
        },

        filterByStudy(trait) {
            if (trait !== null) {
                this.displayFilters.trait_name = trait
            } 
        },

        removeDisplayFilters() {
            this.displayFilters = {
                view: "full",
                chr: null,
                candidate_snp: null,
                trait_name: null
            }
            this.traitSearch.text = ''
        },

        get getDataForColocTable() {
            if (!this.filteredColocData || this.filteredColocData.length === 0) return []

            let tableData = this.filteredColocData.filter(coloc => {
                if (this.displayFilters.candidate_snp !== null) return coloc.candidate_snp === this.displayFilters.candidate_snp 
                else if (this.displayFilters.chr !== null) return coloc.chr == this.displayFilters.chr
                else return true
            })

            tableData.forEach(coloc => {
                const hash = [...coloc.candidate_snp].reduce((hash, char) => (hash * 31 + char.charCodeAt(0)) % constants.tableColors.length, 0)
                coloc.color = constants.tableColors[hash]
            })

            tableData = Object.groupBy(tableData, ({ candidate_snp }) => candidate_snp);
            // Remove entries with only one study
            tableData = Object.fromEntries(
                Object.entries(tableData).filter(([_, group]) => group.length > 1)
            );

            return Object.fromEntries(Object.entries(tableData).slice(0, 100))
        },

        get getDataForRareTable() {
            if (!this.filteredRareResults || this.filteredRareResults.length === 0) return []

            let tableData = this.filteredRareResults.filter(rare => {
                if (this.displayFilters.candidate_snp !== null) return rare.candidate_snp === this.displayFilters.candidate_snp 
                else if (this.displayFilters.chr !== null) return rare.chr == this.displayFilters.chr
                else return true
            })

            tableData.forEach(rare => {
                const hash = [...rare.candidate_snp].reduce((hash, char) => (hash * 31 + char.charCodeAt(0)) % constants.tableColors.length, 0)
                rare.color = constants.tableColors[hash]
            })

            tableData = Object.groupBy(tableData, ({ candidate_snp }) => candidate_snp);
            tableData = Object.fromEntries(
                Object.entries(tableData).filter(([_, group]) => group.length > 1)
            );

            return Object.fromEntries(Object.entries(tableData).slice(0, 100))
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

        getPhenotypeGraph() {
            const chartContainer = document.getElementById("phenotype-chart");
            const resetButton = document.getElementById("reset-display");
            chartContainer.innerHTML = ''; // Clear existing content
        
            let self = this;
        
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

            // Add chromosome backgrounds for ALL chromosomes
            const chrBackgrounds = plotGroup.append("g")
                .attr("class", "chr-backgrounds")
                .style("pointer-events", "all");

            // Add chromosome labels
            const chrLabels = plotGroup.append("g")
                .attr("class", "chr-labels");

            const yScale = d3.scaleLinear()
                .domain([self.svgs.metadata.y_axis.min_lp, self.svgs.metadata.y_axis.max_lp])
                .range([height, 0]);

            const yAxis = d3.axisLeft(yScale)
                .ticks(10)
                .tickFormat(d => d);
            plotGroup.append("g")
                .call(yAxis)
                .selectAll("text")
                .style("text-anchor", "end")
                .style("font-size", "12px");
            plotGroup.append("text")
                .attr("transform", "rotate(-90)")
                .attr("x", -height / 2)
                .attr("y", -50)
                .style("text-anchor", "middle")
                .style("font-size", "14px")
                .text("-log10(p-value)");

            // Add legend above y-axis
            const legendGroup = plotGroup.append("g")
                .attr("class", "legend")
                .attr("transform", `translate(${width - 110}, -10)`);

            // Common variant legend item
            legendGroup.append("circle")
                .attr("cx", 0)
                .attr("cy", 0)
                .attr("r", 5)
                .attr("fill", constants.colors.dataTypes.common)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);

            legendGroup.append("text")
                .attr("x", 7)
                .attr("y", 4)
                .style("font-size", "12px")
                .text("Common");

            // Rare variant legend item
            legendGroup.append("circle")
                .attr("cx", 75)
                .attr("cy", 0)
                .attr("r", 5)
                .attr("fill", constants.colors.dataTypes.rare)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);

            legendGroup.append("text")
                .attr("x", 82)
                .attr("y", 4)
                .style("font-size", "12px")
                .text("Rare");

            // Add reference lines
            const referenceLines = plotGroup.append("g")
                .attr("class", "reference-lines");
            referenceLines.append("line")
                .attr("x1", 0)
                .attr("x2", width)
                .attr("y1", yScale(5))
                .attr("y2", yScale(5))
                .attr("stroke", "darkred")
                .attr("opacity", 0.5)
                .attr("stroke-width", 0.5)
                .attr("stroke-dasharray", "5,5");

            referenceLines.append("line")
                .attr("x1", 0)
                .attr("x2", width)
                .attr("y1", yScale(7.3))
                .attr("y2", yScale(7.3))
                .attr("stroke", "darkred")
                .attr("opacity", 0.5)
                .attr("stroke-width", 0.5);

            // Store coloc circles in a group for easy manipulation
            const colocCirclesGroup = plotGroup.append("g")
                .attr("class", "coloc-circles");

            // Quick fade out all circles before switching views
            colocCirclesGroup.selectAll("circle")
                .transition()
                .duration(500)
                .attr("opacity", 0)
                .remove();

            function renderChromosomeView() {
                const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == self.displayFilters.chr);
                const chrSvg = self.svgs.chromosomes[`chr${self.displayFilters.chr}`];
                loadSvg(chrSvg);

                const xScale = d3.scaleLinear()
                    .domain([chrMeta.bp_start, chrMeta.bp_end])
                    .range([0, width]);

                const xAxis = d3.axisBottom(xScale)
                    .ticks(0)
                    .tickSize(0);
                plotGroup.append("g")
                    .attr("transform", `translate(0,${height})`)
                    .call(xAxis);
                plotGroup.append("text")
                    .attr("x", width / 2)
                    .attr("y", height + 40)
                    .style("text-anchor", "middle")
                    .style("font-size", "14px")
                    .text(`Chromosome ${self.displayFilters.chr}`);

                chrLabels.selectAll("text")
                    .data(self.svgs.metadata.x_axis)
                    .join("text")
                    .transition()
                    .duration(500)
                    .attr("opacity", 0);

                if (self.filteredGroupedColoc || self.filteredGroupedRareResults) {
                    const allGroups = Object.values(self.filteredGroupedColoc).concat(Object.values(self.filteredGroupedRareResults))
                    const circleData = allGroups.map(group => {
                        const traitId = self.data.trait.id;
                        const study = group.find(s => s.trait_id === traitId);
                        if (!study) return null;
                        if (study.chr != self.displayFilters.chr) return null;
                        study._group = group;
                        return study;
                    }).filter(Boolean);

                    const circles = colocCirclesGroup.selectAll("circle")
                        .data(circleData, d => d.candidate_snp);

                    circles.enter()
                        .append("circle")
                        .attr("cx", d => {
                            const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == d.chr);
                            const bpPosition = (d.bp) / (chrMeta.bp_end - chrMeta.bp_start);
                            console.log(d.bp, (chrMeta.bp_end - chrMeta.bp_start), bpPosition * width)
                            return bpPosition * width;
                        })
                        .attr("cy", d => {
                            const yValue = -Math.log10(d.min_p);
                            return yScale(yValue);
                        })
                        .attr("r", d => Math.min(d._group.length + 2, 20))
                        .attr("fill", d => d.coloc_group_id ? constants.colors.dataTypes.common : constants.colors.dataTypes.rare)
                        .attr("stroke", "#fff")
                        .attr("stroke-width", 1.5)
                        .attr("opacity", 0)
                        .on('mouseover', function(event, d) {
                            d3.select(this).style("cursor", "pointer");
                            let allTraits = d._group.map(s => s.trait_name)
                            let uniqueTraits = [...new Set(allTraits)]
                            let traitNames = uniqueTraits.slice(0,9)
                            traitNames = traitNames.join("<br />")
                            if (uniqueTraits.length > 10) traitNames += "<br /> " + (uniqueTraits.length - 10) + " more..."
                            traitNames = '<b>SNP: ' + d.candidate_snp + '</b><br />' + traitNames
                            d3.select(this).transition()
                                .duration('100')
                                .attr("fill", constants.colors.dataTypes.highlighted)
                                .attr("r", Math.min(d._group.length + 2, 20) + 8)
                            tooltip.transition()
                                .duration(100)
                                .style("opacity", 1)
                                .style("visibility", "visible")
                                .style("display", "block");
                            tooltip.html(traitNames)
                                .style("left", (event.pageX + 10) + "px")
                                .style("top", (event.pageY - 15) + "px");
                        })
                        .on('mouseout', function () {
                            d3.select(this).transition()
                                .duration('200')
                                .attr("fill", d => d.coloc_group_id ? constants.colors.dataTypes.common : constants.colors.dataTypes.rare)
                                .attr("r", d => Math.min(d._group.length + 2, 20))
                            tooltip.transition()
                                .duration(100)
                                .style("visibility", "hidden")
                                .style("display", "none");
                        })
                        .on('click', function(event, d) {
                            self.displayFilters.candidate_snp = d.candidate_snp;
                        })
                        .transition()
                        .duration(500)
                        .attr("opacity", 0.8);
                }
            }

            function renderFullView() {
                loadSvg(self.svgs.full);

                const xScale = d3.scaleLinear()
                    .domain([0, self.svgs.metadata.x_axis[self.svgs.metadata.x_axis.length - 1].bp_end])
                    .range([0, width]);
                const xAxis = d3.axisBottom(xScale)
                    .ticks(0)
                    .tickSize(0);
                plotGroup.append("g")
                    .attr("transform", `translate(0,${height})`)
                    .call(xAxis);
                plotGroup.append("text")
                    .attr("x", width / 2)
                    .attr("y", height + 40)
                    .style("text-anchor", "middle")
                    .style("font-size", "14px")
                    .text("Chromosome");

                self.svgs.metadata.x_axis.forEach((chr, i) => {
                    const xStart = (chr.pixel_start / self.svgs.metadata.svg_width) * width;
                    const xEnd = (chr.pixel_end / self.svgs.metadata.svg_width) * width;
                    const rect = chrBackgrounds.append("rect")
                        .datum(chr)
                        .attr("x", xStart)
                        .attr("y", 0)
                        .attr("width", xEnd - xStart)
                        .attr("height", height)
                        .attr("fill", i % 2 === 0 ? "#e5e5e5" : "#ffffff")
                        .attr("opacity", 0.5)
                        .style("cursor", "pointer")
                        .on('mouseover', function() {
                            d3.select(this)
                                .transition()
                                .duration(200)
                                .attr("fill", "#e6f3ff");
                        })
                        .on('mouseout', function() {
                            d3.select(this)
                                .transition()
                                .duration(200)
                                .attr("fill", i % 2 === 0 ? "#e5e5e5" : "#ffffff");
                        })
                        .on('click', function(d) {
                            console.log(chr.CHR)
                            self.displayFilters.view = "chromosome";
                            self.displayFilters.chr = chr.CHR;
                            self.displayFilters.candidate_snp = null;
                        });
                });

                self.svgs.metadata.x_axis.forEach(chr => {
                    const xPos = ((chr.pixel_start + chr.pixel_end) / 2 / self.svgs.metadata.svg_width) * width;
                    const label = chrLabels.append("text")
                        .attr("x", xPos)
                        .attr("y", height + 20)
                        .style("text-anchor", "middle")
                        .style("font-size", "10px")
                        .text(chr.CHR);
                    label.transition().duration(500).attr("opacity", 1);
                });
                // Draw coloc circles for all chromosomes with fade transition
                if (self.filteredGroupedColoc || self.filteredGroupedRareResults) {
                    const allGroups = Object.values(self.filteredGroupedColoc).concat(Object.values(self.filteredGroupedRareResults))
                    const circleData = allGroups.map(group => {
                        const traitId = self.data.trait.id;
                        const study = group.find(s => s.trait_id === traitId);
                        if (!study) return null;
                        study._group = group;
                        return study;
                    }).filter(Boolean);

                    const circles = colocCirclesGroup.selectAll("circle")
                        .data(circleData, d => d.candidate_snp);

                    circles.enter()
                        .append("circle")
                        .attr("cx", d => {
                            const chrMeta = self.svgs.metadata.x_axis.find(chr => chr.CHR == d.chr);
                            const chrLength = chrMeta.bp_end - chrMeta.bp_start;
                            const bpRatio = d.bp / chrLength;
                            const xPixel = (chrMeta.pixel_start + (bpRatio * (chrMeta.pixel_end - chrMeta.pixel_start))) / self.svgs.metadata.svg_width * width;
                            return xPixel;
                        })
                        .attr("cy", d => {
                            const yValue = -Math.log10(d.min_p);
                            return yScale(yValue);
                        })
                        .attr("r", d => Math.min(d._group.length + 2, 20))
                        .attr("fill", d => d.coloc_group_id ? constants.colors.dataTypes.common : constants.colors.dataTypes.rare)
                        .attr("stroke", "#fff")
                        .attr("stroke-width", 1.5)
                        .attr("opacity", 0)
                        .on('mouseover', function(event, d) {
                            d3.select(this).style("cursor", "pointer");
                            let allTraits = d._group.map(s => s.trait_name)
                            let uniqueTraits = [...new Set(allTraits)]
                            let traitNames = uniqueTraits.slice(0,9)
                            traitNames = traitNames.join("<br />")
                            if (uniqueTraits.length > 10) traitNames += "<br /> " + (uniqueTraits.length - 10) + " more..."
                            traitNames = '<b>SNP: ' + d.candidate_snp + '</b><br />' + traitNames 
                            d3.select(this).transition()
                                .duration('100')
                                .attr("fill", constants.colors.dataTypes.highlighted)
                                .attr("r", Math.min(d._group.length + 2, 20) + 8)
                            tooltip.transition()
                                .duration(100)
                                .style("opacity", 1)
                                .style("visibility", "visible")
                                .style("display", "block");
                            tooltip.html(traitNames)
                                .style("left", (event.pageX + 10) + "px")
                                .style("top", (event.pageY - 15) + "px");
                        })
                        .on('mouseout', function () {
                            d3.select(this).transition()
                                .duration('200')
                                .attr("fill", d => d.coloc_group_id ? constants.colors.dataTypes.common : constants.colors.dataTypes.rare)
                                .attr("r", d => Math.min(d._group.length + 2, 20))
                            tooltip.transition()
                                .duration(100)
                                .style("visibility", "hidden")
                                .style("display", "none");
                        })
                        .on('click', function(event, d) {
                            self.displayFilters.candidate_snp = d.candidate_snp;
                        })
                        .transition()
                        .duration(500)
                        .attr("opacity", 0.8);
                }
            }

            if (self.displayFilters.view === "chromosome" && self.displayFilters.chr) {
                renderChromosomeView();
            } else {
                renderFullView();
            }
        },
    }
}
