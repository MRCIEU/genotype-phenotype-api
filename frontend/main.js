import 'bulma/css/bulma.css'
import logo from './images/logo.png'
import smallLogo from './images/small_logo.svg'

import * as d3 from 'd3';
import Alpine from 'alpinejs';

/* TODO: look into using alpine with reusable web components here: https://stackoverflow.com/questions/65710987/reusable-alpine-js-components */

window.Alpine = Alpine;
Alpine.data('app', () => ({
  d3,
  logo,
  smallLogo,
  count: 0,
}))

Alpine.data('searchInput', () => ({
  isOpen: false,
  search: '',
  dummyData: [
    {
      id: 1,
      type: 'phenotype',
      name: 'Mean corpuscular hemoglobin',
    },
    {
      id: 2,
      type: 'phenotype',
      name: 'Mean corpuscular hemoglobin concentration',
    },
    {
      id: 3,
      type: 'gene',
      name: 'D2 gene',
    }
  ],

  goToItem(item) {
    window.location.href = 'phenotype.html?' + item.id;
    this.search = ''
  },

  closeSearch() {
    this.search = ''
    this.isOpen = false
  },

  get getItemsForSearch() {
    const filterItems = this.dummyData.filter((item) => {
        return item.name.toLowerCase().includes(this.search.toLowerCase())
    })

    if(filterItems.length < this.dummyData.length && filterItems.length > 0) {
      this.isOpen = true
      return filterItems
    } else {
      this.isOpen = false
    }
  }
}))

Alpine.start();
