import * as d3 from 'd3';
import constants from './constants.js'

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

        async loadData() {
            let studyId = (new URLSearchParams(location.search).get('id'))
            let requestUrl = constants.apiUrl + '/studies/' + studyId

            if (studyId && studyId.includes('-')) {
                this.userUpload = true
                requestUrl = constants.apiUrl + '/gwas/' + studyId
            }

            try {
                // const response = await fetch(requestUrl)
                // if (!response.ok) {
                //     this.errorMessage = `Failed to load data: ${response.status} ${response.statusText}`
                //     return
                // }
                
                // this.data = await response.json()
                this.data = {"study": {"id": 16, "guid": "22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b", "email": "ae@email.com", "name": "Example Study", "sample_size": 23423, "ancestry": "EUR", "category": "continuous", "is_published": false, "doi": "None", "should_be_added": false, "status": "completed"}, "study_extractions": [{"id": 2931118, "study_id": 1507, "snp_id": 4261896, "snp": "19:58383088_A_G", "ld_block_id": 1287, "unique_study_id": "ebi-a-GCST90018994_EUR_19_58383088_1", "study": "ebi-a-GCST90018994", "file": "/local-scratch/projects/genotype-phenotype-map/data/study/ebi-a-GCST90018994/finemapped/EUR_19_58383088_1.tsv.gz", "chr": 19, "bp": 58383088, "min_p": 8.405044354731217e-05, "cis_trans": null, "ld_block": "EUR/19/56919549-58607520", "known_gene": null}, {"id": 2931479, "study_id": 2343, "snp_id": 4261880, "snp": "19:58378824_A_G", "ld_block_id": 1287, "unique_study_id": "ebi-a-GCST003766_EUR_19_57004872_3", "study": "ebi-a-GCST003766", "file": "/local-scratch/projects/genotype-phenotype-map/data/study/ebi-a-GCST003766/finemapped/EUR_19_57004872_3.tsv.gz", "chr": 19, "bp": 58378824, "min_p": 3.484585048379826e-30, "cis_trans": null, "ld_block": "EUR/19/56919549-58607520", "known_gene": null}, {"id": 2933060, "study_id": 117701, "snp_id": 4259885, "snp": "19:57844874_A_G", "ld_block_id": 1287, "unique_study_id": "GTEx-eQTL-v10-Artery-Coronary-ENSG00000198466-12_EUR_19_57844874_2", "study": "GTEx-eQTL-v10-Artery-Coronary-ENSG00000198466-12", "file": "/local-scratch/projects/genotype-phenotype-map/data/study/GTEx-eQTL-v10-Artery-Coronary-ENSG00000198466-12/finemapped/EUR_19_57860905_2.tsv.gz", "chr": 19, "bp": 57844874, "min_p": 2.01859101725357e-17, "cis_trans": "cis", "ld_block": "EUR/19/56919549-58607520", "known_gene": "ZNF587"}, {"id": 2933094, "study_id": 134358, "snp_id": 4258659, "snp": "19:57490144_A_T", "ld_block_id": 1287, "unique_study_id": "GTEx-eQTL-v10-Artery-Tibial-ENSG00000105136-22_EUR_19_57490144_1", "study": "GTEx-eQTL-v10-Artery-Tibial-ENSG00000105136-22", "file": "/local-scratch/projects/genotype-phenotype-map/data/study/GTEx-eQTL-v10-Artery-Tibial-ENSG00000105136-22/finemapped/EUR_19_57492120_1.tsv.gz", "chr": 19, "bp": 57490144, "min_p": 1.7796490496925177e-43, "cis_trans": "cis", "ld_block": "EUR/19/56919549-58607520", "known_gene": "ZNF419"}, {"id": 2933333, "study_id": 172257, "snp_id": 4258648, "snp": "19:57488345_C_G", "ld_block_id": 1287, "unique_study_id": "GTEx-eQTL-v10-Brain-Caudate-basal-ganglia-ENSG00000268545-1_EUR_19_57488345_1", "study": "GTEx-eQTL-v10-Brain-Caudate-basal-ganglia-ENSG00000268545-1", "file": "/local-scratch/projects/genotype-phenotype-map/data/study/GTEx-eQTL-v10-Brain-Caudate-basal-ganglia-ENSG00000268545-1/finemapped/EUR_19_57488345_1.tsv.gz", "chr": 19, "bp": 57488345, "min_p": 7.930009815027006e-06, "cis_trans": "cis", "ld_block": "EUR/19/56919549-58607520", "known_gene": "VN1R107P"}, {"id": 2934051, "study_id": 331407, "snp_id": 4258659, "snp": "19:57490144_A_T", "ld_block_id": 1287, "unique_study_id": "GTEx-eQTL-v10-Breast-Mammary-Tissue-ENSG00000105136-22_EUR_19_57490144_1", "study": "GTEx-eQTL-v10-Breast-Mammary-Tissue-ENSG00000105136-22", "file": "/local-scratch/projects/genotype-phenotype-map/data/study/GTEx-eQTL-v10-Breast-Mammary-Tissue-ENSG00000105136-22/finemapped/EUR_19_57524397_1.tsv.gz", "chr": 19, "bp": 57490144, "min_p": 9.753223619360374e-13, "cis_trans": "cis", "ld_block": "EUR/19/56919549-58607520", "known_gene": "ZNF419"}], "upload_study_extractions": [{"id": 181, "gwas_upload_id": 16, "snp_id": 4258648, "snp": "19:57488345_C_G", "ld_block_id": 49, "unique_study_id": "22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b_EUR_1_103423003_1", "study": "22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b", "file": "/local-scratch/projects/genotype-phenotype-map/test/data/study/gwas_upload/22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b//finemapped/EUR_1_101950949_1.tsv.gz", "chr": 1, "bp": 103423003, "min_p": 3.0203e-22, "cis_trans": null, "ld_block": "EUR/1/101384499-103762931", "known_gene": null}, {"id": 182, "gwas_upload_id": 16, "snp_id": 4258648, "snp": "19:57488345_C_G", "ld_block_id": 49, "unique_study_id": "22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b_EUR_1_103430485_2", "study": "22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b", "file": "/local-scratch/projects/genotype-phenotype-map/test/data/study/gwas_upload/22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b//finemapped/EUR_1_101950949_2.tsv.gz", "chr": 1, "bp": 103430485, "min_p": 3.4851e-18, "cis_trans": null, "ld_block": "EUR/1/101384499-103762931", "known_gene": null}], "colocs": [{"gwas_upload_id": 16, "upload_study_extraction_id": null, "existing_study_extraction_id": null, "snp_id": 4258648, "ld_block_id": null, "coloc_group_id": 1, "iteration": 2, "unique_study_id": "22d5cdd8-ac0b-bb58-d2c3-c342ac8ec78b_EUR_1_103423003_1", "posterior_prob": 0.673799991607666, "regional_prob": 0.7142999768257141, "posterior_explained_by_snp": 0.3646000027656555, "candidate_snp": "19:57488345_C_G", "study_id": null, "chr": 1, "bp": 103423003, "min_p": 3.0203e-22, "cis_trans": null, "ld_block": "EUR/1/101384499-103762931", "known_gene": null, "trait": "Example Study", "data_type": "phenotype", "tissue": null}, {"gwas_upload_id": 16, "upload_study_extraction_id": null, "existing_study_extraction_id": 2934051, "snp_id": 4258648, "ld_block_id": null, "coloc_group_id": 1, "iteration": 2, "unique_study_id": "GTEx-eQTL-v10-Breast-Mammary-Tissue-ENSG00000105136-22_EUR_19_57490144_1", "posterior_prob": 0.673799991607666, "regional_prob": 0.7142999768257141, "posterior_explained_by_snp": 0.3646000027656555, "candidate_snp": "19:57488345_C_G", "study_id": 331407, "chr": 19, "bp": 57490144, "min_p": 9.753223619360374e-13, "cis_trans": "cis", "ld_block": "EUR/19/56919549-58607520", "known_gene": "ZNF419", "trait": "GTEx-eQTL-v10 Breast Mammary Tissue ZNF419", "data_type": "gene_expression", "tissue": "Breast Mammary Tissue"}, {"gwas_upload_id": 16, "upload_study_extraction_id": null, "existing_study_extraction_id": 2931118, "snp_id": 4258648, "ld_block_id": null, "coloc_group_id": 2, "iteration": 1, "unique_study_id": "ebi-a-GCST90018994_EUR_19_58383088_1", "posterior_prob": 0.7675999999046326, "regional_prob": 0.8600999712944031, "posterior_explained_by_snp": 1.0, "candidate_snp": "19:57488345_C_G", "study_id": 1507, "chr": 19, "bp": 58383088, "min_p": 8.405044354731217e-05, "cis_trans": null, "ld_block": "EUR/19/56919549-58607520", "known_gene": null, "trait": "Medication use (opioids)", "data_type": "phenotype", "tissue": null}, {"gwas_upload_id": 16, "upload_study_extraction_id": null, "existing_study_extraction_id": 2931479, "snp_id": 4258648, "ld_block_id": null, "coloc_group_id": 2, "iteration": 1, "unique_study_id": "ebi-a-GCST003766_EUR_19_57004872_3", "posterior_prob": 0.7675999999046326, "regional_prob": 0.8600999712944031, "posterior_explained_by_snp": 1.0, "candidate_snp": "19:57488345_C_G", "study_id": 2343, "chr": 19, "bp": 58378824, "min_p": 3.484585048379826e-30, "cis_trans": null, "ld_block": "EUR/19/56919549-58607520", "known_gene": null, "trait": "Subjective well-being", "data_type": "phenotype", "tissue": null}, {"gwas_upload_id": 16, "upload_study_extraction_id": null, "existing_study_extraction_id": 2933060, "snp_id": 4258648, "ld_block_id": null, "coloc_group_id": 2, "iteration": 1, "unique_study_id": "GTEx-eQTL-v10-Artery-Coronary-ENSG00000198466-12_EUR_19_57844874_2", "posterior_prob": 0.7675999999046326, "regional_prob": 0.8600999712944031, "posterior_explained_by_snp": 1.0, "candidate_snp": "19:57488345_C_G", "study_id": 117701, "chr": 19, "bp": 57844874, "min_p": 2.01859101725357e-17, "cis_trans": "cis", "ld_block": "EUR/19/56919549-58607520", "known_gene": "ZNF587", "trait": "GTEx-eQTL-v10 Artery Coronary ZNF587", "data_type": "gene_expression", "tissue": "Artery Coronary"}, {"gwas_upload_id": 16, "upload_study_extraction_id": null, "existing_study_extraction_id": 2933094, "snp_id": 4258648, "ld_block_id": null, "coloc_group_id": 1, "iteration": 2, "unique_study_id": "GTEx-eQTL-v10-Artery-Tibial-ENSG00000105136-22_EUR_19_57490144_1", "posterior_prob": 0.673799991607666, "regional_prob": 0.7142999768257141, "posterior_explained_by_snp": 0.3646000027656555, "candidate_snp": "19:57488345_C_G", "study_id": 134358, "chr": 19, "bp": 57490144, "min_p": 1.7796490496925177e-43, "cis_trans": "cis", "ld_block": "EUR/19/56919549-58607520", "known_gene": "ZNF419", "trait": "GTEx-eQTL-v10 Artery Tibial ZNF419", "data_type": "gene_expression", "tissue": "Artery Tibial"}, {"gwas_upload_id": 16, "upload_study_extraction_id": null, "existing_study_extraction_id": 2933333, "snp_id": 4258648, "ld_block_id": null, "coloc_group_id": 1, "iteration": 2, "unique_study_id": "GTEx-eQTL-v10-Brain-Caudate-basal-ganglia-ENSG00000268545-1_EUR_19_57488345_1", "posterior_prob": 0.673799991607666, "regional_prob": 0.7142999768257141, "posterior_explained_by_snp": 0.3646000027656555, "candidate_snp": "19:57488345_C_G", "study_id": 172257, "chr": 19, "bp": 57488345, "min_p": 7.930009815027006e-06, "cis_trans": "cis", "ld_block": "EUR/19/56919549-58607520", "known_gene": "VN1R107P", "trait": "GTEx-eQTL-v10 Brain Caudate basal ganglia VN1R107P", "data_type": "gene_expression", "tissue": "Brain Caudate basal ganglia"}]}


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

                this.orderedTraitsToFilterBy = uniqueTraits.filter(t => t !== this.data.study.trait)

                this.filterByOptions(Alpine.store('graphOptionStore')) 

            } catch (error) {
                console.error('Error loading data:', error);
            }
        },

        get showResults() {
            if (this.data === null) return false
            if (this.userUpload) return this.data.study.status === 'completed'
            return true
        },

        get getStudyToDisplay() {
            if (this.data === null) return '...'
            if (this.userUpload) {
                return 'GWAS Upload: ' + this.data.study.name
            }

            return text + this.data.study.trait
        },

        filterByOptions(graphOptions) {
            let colocIdsWithTraits = []
            if (this.displayFilters.trait) {
                colocIdsWithTraits = this.data.colocs.filter(c => c.trait === this.displayFilters.trait).map(c => c.coloc_group_id)
            } 
            this.filteredColocData = this.data.colocs.filter(coloc => {
                const graphOptionFilters = ((coloc.min_p <= graphOptions.pValue &&
                    coloc.posterior_prob >= graphOptions.coloc &&
                    (graphOptions.includeTrans ? true : coloc.cis_trans !== 'trans') &&
                    (graphOptions.onlyMolecularTraits ? coloc.data_type !== 'phenotype' : true))
                 || coloc.rare)

                const traitFilter = this.displayFilters.trait ? colocIdsWithTraits.includes(coloc.coloc_group_id) : true

                return graphOptionFilters && traitFilter
            })
            this.filteredStudyExtractions = this.data.study_extractions.filter(se => {
                return se.min_p <= graphOptions.pValue &&
                    (graphOptions.includeTrans ? true : se.cis_trans !== 'trans') &&
                    (graphOptions.onlyMolecularTraits ? se.data_type !== 'phenotype' : true)
            })

            // deduplicate studies and sort based on frequency
            this.filteredGroupedColoc = Object.groupBy(this.filteredColocData, ({ candidate_snp }) => candidate_snp);
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

            const graphOptions = Alpine.store('graphOptionStore')
            this.filterByOptions(graphOptions)
            
            // Add resize listener when initializing the graph
            window.addEventListener('resize', () => {
                // Debounce the resize event to prevent too many redraws
                clearTimeout(this.resizeTimer);
                this.resizeTimer = setTimeout(() => {
                    this.getPhenotypeGraph(graphOptions);
                }, 250); // Wait for 250ms after the last resize event
            });
            
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

            // Remove any existing tooltips first
            d3.selectAll(".tooltip").remove();

            // Create a single tooltip that will be reused
            // let tooltip = d3.select("body").append("div")
            //     .attr("class", "tooltip")
            //     .style("opacity", 0)
            //     .on('mouseover', function() {
            //         d3.select(this)
            //             .style("opacity", 1)
            //             .style("visibility", "visible")
            //             .style("display", "flex");
            //     })
            //     .on('mouseout', function() {
            //         d3.select(this)
            //             .transition()
            //             .duration(100)
            //             .style("visibility", "hidden")
            //             .style("display", "none");
            //     });

            const chartContainer = d3.select("#phenotype-chart");
            chartContainer.select("svg").remove()
            
            // Get the current width of the container
            let graphWidth = chartContainer.node().getBoundingClientRect().width - 50;

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
                },
                noColocMargin: {
                    bottom: 40,
                    right: 0,
                    top: 0,
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

            let graphData = this.filteredColocData.slice()
            // fill in missing CHRs, so we don't get a weird looking graph
            chromosomes.forEach(chrText => {
                graphData.push({chrText: chrText, ignore: true})
            })
            
            // place wrapper g with margins
            const svg = chartContainer
                .append("svg")
                .attr('width', graphConstants.width + graphConstants.outerMargin.left)
                .attr('height', graphConstants.height + graphConstants.outerMargin.top + graphConstants.outerMargin.bottom + graphConstants.noColocMargin.bottom + graphConstants.rareMargin.top)
                .append('g')
                .attr('transform', 'translate(' + graphConstants.outerMargin.left + ',' + (graphConstants.outerMargin.top) + ')');

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
                .attr("y", graphConstants.height - 40 + graphConstants.rareMargin.top + graphConstants.noColocMargin.bottom)
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
                .attr('height', innerHeight + graphConstants.rareMargin.top + graphConstants.noColocMargin.bottom)
                .attr('fill', '#f9f9f9');

            // Add vertical separator lines between chromosomes
            svg.selectAll('.chr-separator')
                .data(chromosomes.slice(1))  // Skip first chromosome since we don't need a line before it
                .enter()
                .append('line')
                .attr('class', 'chr-separator')
                .attr('x1', d => outerXScale(d))
                .attr('x2', d => outerXScale(d))
                .attr('y1', -15)  // Start from the header
                .attr('y2', innerHeight + graphConstants.rareMargin.top + graphConstants.noColocMargin.bottom)  // Extend to bottom
                .attr('stroke', '#000000')
                .attr('stroke-width', 1);

            // CHR header box
            innerGraph
                .append('rect')
                .attr('width', innerWidth)
                .attr('height', 15)
                .attr('transform', 'translate(' + 0 + ',' + -15 + ')')
                .attr('fill', '#d6d6d6');

            // Add horizontal line below headers
            svg.append('line')
                .attr('x1', 0)
                .attr('x2', graphConstants.width)
                .attr('y1', 0)  // Position at y=0 (where the main plot starts)
                .attr('y2', 0)
                .attr('stroke', '#000000')
                .attr('stroke-width', 2);

            // CHR header text
            innerGraph
                .append('text')
                .text(function (d) { return d[0] })
                .attr("font-weight", 700)
                .attr('text-anchor', 'middle')
                .attr('transform', 'translate(' + innerWidth / 2 + ',' + -2 + ')')
                .attr("font-size", "12px")
                // Highlight the column of the header when hovering over it
                .on('mouseover', function (d, i) {
                    d3.select(this).style("cursor", "pointer");
                    d3.select(this.parentNode)
                        .selectAll('rect')
                        .transition()
                        .duration(200)
                        .attr('fill', '#ececec')
                })
                // Restore original background color for all rectangles
                .on('mouseout', function(d, i) {
                    d3.select(this.parentNode)
                        .selectAll('rect')
                        .transition()
                        .duration(200)
                        .attr('fill', function() {
                            // Keep header background color for the header rect
                            return d3.select(this).attr('height') === '15' ? '#d6d6d6' : '#f9f9f9';
                        });
                })
                .on('click', function(d, i) {
                    let chr = parseInt(i[0].slice(4))
                    self.displayFilters.chr = chr
                    self.displayFilters.candidate_snp = null
                })

            // Create scales for each chromosome
            const innerXScales = {};
            chromosomes.forEach(chr => {
                const chrNum = parseInt(chr.slice(4));
                const maxMb = constants.maxBpPerChr[chrNum] / 1000000;
                innerXScales[chr] = d3.scaleLinear()
                    .domain([0, maxMb])
                    .range([0, innerWidth]);
            });

            let tooltip = d3.select("body").append("div")
                .attr("class", "tooltip")
                .style("opacity", 0);

            // Use the scales in the x-axis creation
            innerGraph
                .append('g')
                .each(function(d) {
                    const chr = d[0];
                    const scale = innerXScales[chr];
                    const maxMb = constants.maxBpPerChr[parseInt(chr.slice(4))] / 1000000;
                    const tickStep = maxMb > 100 ? 50 : 25;
                    const tickValues = d3.range(0, maxMb, tickStep).filter(t => t <= maxMb && t > 0);
                    d3.select(this)
                        .call(d3.axisBottom(scale)
                            .tickValues(tickValues)
                            .tickSize(-innerHeight))
                        .attr('transform', `translate(0,${innerHeight + graphConstants.noColocMargin.bottom + graphConstants.rareMargin.top})`)
                        .selectAll("text")    
                        .style("text-anchor", "end")
                        .attr("dx", "-.8em")
                        .attr("dy", ".15em")
                        .attr("transform", "rotate(-65)");
                });

            // inner y scales
            let innerYScale = d3.scaleLinear()
                .domain([lowerYScale, 1.01])
                .range([innerHeight, 0]);

            // inner y axis
            svg.append('g')
                .call(d3.axisLeft(innerYScale).tickValues(yAxisValues).tickSize(-innerWidth))
                .attr('transform', `translate(0,0)`);

            // drawing the dots, as well as the code to display the tooltip
            innerGraph
                .selectAll('dot')
                .data(d => d[1].filter(item => !item.rare))
                .enter()
                .append('circle')
                .attr("cx", function (d) { 
                    return innerXScales[d.chrText](d.MbP); 
                })
                .attr("cy", d => innerYScale(d.posterior_prob)) 
                .attr("r", d => d.scaledNumStudies+1)
                .attr('fill', d => d.annotationColor )
                .on('mouseover', function(d, i) {
                    d3.select(this).style("cursor", "pointer"); 

                    let allTraits = self.filteredGroupedColoc[i.candidate_snp].map(s => s.trait)
                    let uniqueTraits = [...new Set(allTraits)]
                    let traitNames = uniqueTraits.slice(0,9)
                    traitNames = traitNames.join("<br />")
                    if (uniqueTraits.length > 10) traitNames += "<br /> " + (uniqueTraits.length - 10) + " more..."
                    traitNames = 'SNP: ' + i.candidate_snp + '<br />' + traitNames

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
                    self.displayFilters.candidate_snp = i.candidate_snp
                    self.displayFilters.chr = null
                });

            // Add horizontal grid lines for each 0.05 marker
            innerGraph
                .selectAll('.grid-line')
                .data(yAxisValues)
                .enter()
                .append('line')
                .attr('class', 'grid-line')
                .attr('x1', 0)
                .attr('x2', innerWidth)
                .attr('y1', d => innerYScale(d))
                .attr('y2', d => innerYScale(d))
                .attr('stroke', '#e0e0e0')
                .attr('opacity', 0.5)
                .attr('stroke-width', 1);

            if (graphOptions.includeRareVariants) {
                this.displayRareVariants(self, svg, innerGraph, graphConstants, innerWidth, innerXScales, innerHeight)
            }

            // Add no-coloc variants section
            this.displayNoColocVariants(self, svg, innerGraph, graphConstants, innerWidth, innerXScales, innerHeight)
        },

        displayRareVariants(self, svg, innerGraph, graphConstants, innerWidth, innerXScales, innerHeight) {
            // Remove the previous margin adjustment
            innerGraph
                .select('rect')
                .attr('y', 0);  // Main plot starts at top now

            // Add background for rare variants section below main plot
            innerGraph
                .append('rect')
                .attr('width', innerWidth)
                .attr('height', graphConstants.rareMargin.top)
                .attr('fill', '#f9f9f9')
                .attr('y', innerHeight);  // Position after main plot

            let tooltip = d3.select("body").append("div")
                .attr("class", "tooltip")
                .style("opacity", 0);

            // Update rare variant dots position
            innerGraph
                .selectAll('.rare-dot')
                .data(d => d[1].filter(item => item.rare))
                .enter()
                .append('circle')
                .attr('class', 'rare-dot')
                .attr("cx", d => innerXScales[d.chrText](d.MbP))
                .attr("cy", innerHeight)  // Position in middle of rare section
                .attr("fill", "transparent")
                .attr("stroke", "black")
                .attr("r", 4)
                .on('mouseover', function(d, i) {
                    d3.select(this).style("cursor", "pointer"); 

                    let allTraits = self.filteredGroupedColoc[i.candidate_snp].map(s => s.trait)
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

            // Add "Rare Variants" text to y-axis
            svg.append('text')
                .attr('class', 'rare-variants-label')
                .attr('x', -35)
                .attr('y', innerHeight + (graphConstants.rareMargin.top / 2))  // Update position
                .attr('dy', '0.35em')
                .attr('text-anchor', 'start')
                .style('font-size', '12px')
                .text('Rare:');

            // Add separator lines
            innerGraph
                .append('line')
                .attr('class', 'separator-line')
                .attr('x1', 0)
                .attr('x2', innerWidth)
                .attr('y1', innerHeight)  // Line between main plot and rare variants
                .attr('y2', innerHeight)
                .attr('stroke', '#000000')
                .attr('stroke-width', 1);

            innerGraph
                .append('line')
                .attr('class', 'separator-line')
                .attr('x1', 0)
                .attr('x2', innerWidth)
                .attr('y1', innerHeight + graphConstants.rareMargin.top)  // Line between rare variants and no-coloc
                .attr('y2', innerHeight + graphConstants.rareMargin.top)
                .attr('stroke', '#000000')
                .attr('stroke-width', 1);
        },

        displayNoColocVariants(self, svg, innerGraph, graphConstants, innerWidth, innerXScales, innerHeight) {
            // Update position of no-coloc section to be below rare variants
            innerGraph
                .append('rect')
                .attr('width', innerWidth)
                .attr('height', graphConstants.noColocMargin.bottom)
                .attr('fill', '#f9f9f9')
                .attr('y', innerHeight + graphConstants.rareMargin.top);  // Position after rare variants section

            // Update no-coloc dots position
            innerGraph
                .selectAll('.no-coloc-dot')
                .data(d => {
                    const chr = d[0];
                    return self.filteredStudyExtractions.filter(item => 'CHR ' + item.chr === chr);
                })
                .enter()
                .append('circle')
                .attr('class', 'no-coloc-dot')
                .attr("cx", d => innerXScales[`CHR ${d.chr}`](d.bp / 1000000))
                .attr("cy", innerHeight + graphConstants.rareMargin.top + (graphConstants.noColocMargin.bottom / 2))  // Update position
                .attr("fill", "#666666")
                .attr("r", 3)
                .on('mouseover', function(d, i) {
                    d3.select(this).style("cursor", "pointer"); 
                    d3.select(this).transition()
                        .duration('100')
                        .attr("r", 6);
                    tooltip.transition()
                        .duration(100)
                        .style("opacity", 1)
                        .style("visibility", "visible")
                        .style("display", "flex");
                    tooltip.html(`SNP: ${i.candidate_snp}<br/>P-value: ${i.min_p.toExponential(2)}`)
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

            // Update "No coloc" label position
            svg.append('text')
                .attr('class', 'no-coloc-label')
                .attr('x', -55)
                .attr('y', innerHeight + graphConstants.rareMargin.top + (graphConstants.noColocMargin.bottom / 2))  // Update position
                .attr('dy', '0.35em')
                .attr('text-anchor', 'start')
                .style('font-size', '12px')
                .text('No coloc:');
        },

        // Clean up the resize listener when the component is destroyed
        disconnected() {
            window.removeEventListener('resize', this.handleResize);
        }
    }
}
