import 'font-awesome/css/font-awesome.css'
import 'bulma/css/bulma.css'
import 'bulma-slider/dist/css/bulma-slider.min.css'
import 'bulma-divider/dist/css/bulma-divider.min.css'
import './custom.css'

/* TODO: look into using alpine with reusable web components here: https://stackoverflow.com/questions/65710987/reusable-alpine-js-components */
import Alpine from 'alpinejs';
import about from './alpine-components/about.js';
import gene from './alpine-components/gene.js';
import region from './alpine-components/region.js';
import phenotype from './alpine-components/phenotype.js';
import homepage from './alpine-components/homepage.js';
window.Alpine = Alpine;

const graphOptions = {
  coloc: 0.8,
  pValue: 7.3,
  includeRareVariants: true,
  onlyMolecularTraits: false,
  includeTrans: false
}
Alpine.data('graphOptions', () => (Object.assign({}, graphOptions)))
Alpine.store('graphOptionStore', Object.assign({}, graphOptions))

Alpine.data('homepage', homepage)
Alpine.data('phenotype', phenotype)
Alpine.data('gene', gene)
Alpine.data('about', about)
Alpine.data('region', region)

Alpine.start();
