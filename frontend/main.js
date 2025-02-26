import 'font-awesome/css/font-awesome.css'
import 'bulma/css/bulma.css'
import 'bulma-slider/dist/css/bulma-slider.min.css'
import 'bulma-divider/dist/css/bulma-divider.min.css'
import './assets/css/custom.css'

import Alpine from 'alpinejs';
import about from './alpine-components/about.js';
import gene from './alpine-components/gene.js';
import region from './alpine-components/region.js';
import phenotype from './alpine-components/phenotype.js';
import homepage from './alpine-components/homepage.js';
import snp from './alpine-components/snp.js';
window.Alpine = Alpine;

// Register Web Components
import { NavigationBar } from './web-components/navigation-bar.js';
import { GraphOptions } from './web-components/graph-options.js';

customElements.define('navigation-bar', NavigationBar);
customElements.define('graph-options', GraphOptions);

const graphOptions = {
    coloc: 0.8,
    pValue: 0.00000005,
    includeRareVariants: true,
    onlyMolecularTraits: false,
    includeTrans: false,
    pValueOptions: [
            0.00015,       // 1.5e-4
            0.00005,       // 5e-5
            0.00001,       // 1e-5
            0.000005,      // 5e-6
            0.000001,      // 1e-6
            0.0000005,     // 5e-7
            0.0000001,     // 1e-7
            0.00000005     // 5e-8
    ],
    pValueIndex: 7,
    updatePValue() {
            this.pValue = this.pValueOptions[this.pValueIndex];
            this.$store.graphOptionStore.pValue = this.pValue;
    }
}
Alpine.data('graphOptions', () => (Object.assign({}, graphOptions)))
Alpine.store('graphOptionStore', Object.assign({}, graphOptions))

Alpine.data('homepage', homepage)
Alpine.data('phenotype', phenotype)
Alpine.data('gene', gene)
Alpine.data('about', about)
Alpine.data('region', region)
Alpine.data('snp', snp)
Alpine.start();
