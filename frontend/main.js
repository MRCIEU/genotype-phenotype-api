import "font-awesome/css/font-awesome.css";
import "bulma/css/bulma.css";
import "bulma-slider/dist/css/bulma-slider.min.css";
import "bulma-divider/dist/css/bulma-divider.min.css";
import "./assets/css/custom.css";

import Alpine from "alpinejs";
import about from "./alpine-components/about.js";
import gene from "./alpine-components/gene.js";
import region from "./alpine-components/region.js";
import phenotype from "./alpine-components/phenotype.js";
import homepage from "./alpine-components/homepage.js";
import snp from "./alpine-components/snp.js";
import data from "./alpine-components/data.js";
import contact from "./alpine-components/contact.js";
window.Alpine = Alpine;

import { NavigationBar } from "./web-components/navigation-bar.js";
import { ResultsTable } from "./web-components/results-table.js";
import { GraphOptions } from "./web-components/graph-options.js";
import { PipelineSummary } from "./web-components/pipeline-summary.js";

customElements.define("navigation-bar", NavigationBar);
customElements.define("graph-options", GraphOptions);
customElements.define("pipeline-summary", PipelineSummary);
customElements.define("results-table", ResultsTable);

// import * as Sentry from "@sentry/browser";
// if (!import.meta.env.VITE_DEBUG === 'true') {
//     Sentry.init({
//         dsn: import.meta.env.VITE_SENTRY_DSN,
//         tracesSampleRate: 1.0,
//     });
// }

const graphOptions = {
    colocType: "strong",
    pValue: 0.00000005,
    traitType: "all",
    includeTrans: false,
    categories: {
        "Cell / Protein": {
            "Cell Trait": false,
            "Plasma Protein": false,
        },
        "Social / Behavioural": {
            "Environmental Measures": false,
            "Socioeconomic Measures": false,
            "Behavioural Measures": false,
        },
        "Health Trait / Disease Outcome": {
            Neoplasm: false,
            "Disease Of Eye And Adnexa": false,
            "Disease Of Ear And Mastoid Process": false,
            "Disease Of Circulatory System": false,
            "Disease Of Musculoskeletal System And Connective Tissue": false,
            "Nervous System Disorders": false,
            "Disease Of Blood And Blood-Forming Organs": false,
            "Disease Of Skin And Subcutaneous Tissue": false,
            "Disease Of Digestive System": false,
            "Metabolic Disease": false,
            "Disease Of Genitourinary System": false,
            "Infectious Disease": false,
        },
        "Anthropometric Measures": false,
        "Physiological Measures": false,
        "Mental Disorder": false,
        "Reproductive Measures": false,
        "Neurological Disease": false,
        "Psychiatric Measures": false,
    },
    pValueOptions: [
        0.00015, // 1.5e-4
        0.00005, // 5e-5
        0.00001, // 1e-5
        0.000005, // 5e-6
        0.000001, // 1e-6
        0.0000005, // 5e-7
        0.0000001, // 1e-7
        0.00000005, // 5e-8
    ],
    pValueIndex: 7,
    updatePValue() {
        this.pValue = this.pValueOptions[this.pValueIndex];
        this.$store.graphOptionStore.pValue = this.pValue;
    },
    hasAnyCategorySelected() {
        const categories = this.categories;
        for (const [_, value] of Object.entries(categories)) {
            if (typeof value === "object" && value !== null) {
                if (Object.values(value).some(v => v === true)) return true;
            } else if (value === true) {
                return true;
            }
        }
        return false;
    },
};
Alpine.data("graphOptions", () => Object.assign({}, graphOptions));
Alpine.store("graphOptionStore", Object.assign({}, graphOptions));

Alpine.data("homepage", homepage);
Alpine.data("phenotype", phenotype);
Alpine.data("gene", gene);
Alpine.data("about", about);
Alpine.data("data", data);
Alpine.data("region", region);
Alpine.data("snp", snp);
Alpine.data("contact", contact);
Alpine.start();
