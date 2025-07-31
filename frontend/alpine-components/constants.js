export default {
    isLocal: import.meta.env.MODE === "development" || !import.meta.env.PROD,
    apiUrl:
        import.meta.env.MODE === "development" || !import.meta.env.PROD
            ? "http://localhost:8000/v1"
            : "https://gpmap.opengwas.io/api/v1",
    assetBaseUrl:
        import.meta.env.MODE === "development" || !import.meta.env.PROD
            ? "/assets/images/"
            : "https://gpmap.opengwas.io/assets",
    maxBpPerChr: {
        1: 249250621,
        2: 243199373,
        3: 198022430,
        4: 191154276,
        5: 180915260,
        6: 171115067,
        7: 159138663,
        8: 146364022,
        9: 141213431,
        10: 135534747,
        11: 135006516,
        12: 133851895,
        13: 115169878,
        14: 107349540,
        15: 102531392,
        16: 90354753,
        17: 81195210,
        18: 78077248,
        19: 59128983,
        20: 63025520,
        21: 48129895,
        22: 51304566,
    },
    colors: {
        palette: ["#d5a7d6", "#7eb0d5", "#fd7f6f", "#b2e061", "#ffb55a", "#beb9db", "#fdcce5", "#8bd3c7"],
        dataTypes: {
            common: "#1976d2",
            rare: "red",
            highlighted: "black",
        },
    },
    tableColors: ["antiquewhite", "#fffff5", "lavenderblush", "honeydew", "aliceblue", "oldlace", "mintcream"],
    variantTypes: [
        "missense_variant",
        "synonymous_variant",
        "intron_variant",
        "regulatory_region_variant",
        "upstream_gene_variant",
        "downstream_gene_variant",
        "intergenic_variant",
        "non_coding_transcript_variant",
    ],
    orderedDataTypes: ["Splice Variant", "Gene Expression", "Methylation", "Protein", "Phenotype"],
    maxSNPGroupsToDisplay: 100,
    findMinAndMaxValues: function (data) {
        const idFrequencies = data.reduce((acc, obj) => {
            if (obj.id) {
                acc[obj.id] = (acc[obj.id] || 0) + 1;
            }
            return acc;
        }, {});

        const frequencies = Object.values(idFrequencies);
        const minNumStudies = Math.min(...frequencies);
        const maxNumStudies = Math.max(...frequencies);

        return [idFrequencies, minNumStudies, maxNumStudies];
    },
    scaleStudySize: function (frequency, minNumStudies, maxNumStudies) {
        const [scaledMinNumStudies, scaledMaxNumStudies] = [2, 10];
        const scaledNumStudies =
            ((frequency - minNumStudies) / (maxNumStudies - minNumStudies)) *
                (scaledMaxNumStudies - scaledMinNumStudies) +
            scaledMinNumStudies;

        return scaledNumStudies;
    },
};
