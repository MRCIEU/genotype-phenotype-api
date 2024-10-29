import 'bulma/css/bulma.css'
import 'bulma-slider/dist/css/bulma-slider.min.css'
import './custom.css'

import logo from './images/logo.png'
import smallLogo from './images/small_logo.svg'

/* TODO: look into using alpine with reusable web components here: https://stackoverflow.com/questions/65710987/reusable-alpine-js-components */
import Alpine from 'alpinejs';
import phenotype from './alpine-components/phenotype.js';
import search from './alpine-components/search.js';
window.Alpine = Alpine;

Alpine.data('homepage', () => ({
  logo,
  smallLogo,
  count: 0,
}))

Alpine.data('graphOptions', () => ({
  coloc: 0.8,
  pValue: 7.3,
  includeRareVariants: true,
  onlyMolecularTraits: false,
  cisTrans: 'cis'
}))
Alpine.store('graphOptionStore', {
  coloc: 0.8,
  pValue: 7.3,
  includeRareVariants: true,
  onlyMolecularTraits: false,
  cisTrans: 'cis'
})

Alpine.data('searchInput', search)
Alpine.data('phenotype', phenotype)

Alpine.start();
