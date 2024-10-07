import 'bulma/css/bulma.css'
// import * as be from 'bulma-extensions';
import logo from './images/logo.png'
import colocs from './images/colocs.png'
import smallLogo from './images/small_logo.svg'
import coloc from './sample_data/coloc.json'
import studies from './sample_data/studies.json'

import * as d3 from 'd3';
import Alpine from 'alpinejs';

/* TODO: look into using alpine with reusable web components here: https://stackoverflow.com/questions/65710987/reusable-alpine-js-components */

window.Alpine = Alpine;
Alpine.data('homepage', () => ({
  d3,
  logo,
  smallLogo,
  count: 0,
}))

Alpine.data('phenotype', (param) => ({
  dataReceived: true,
  colocs: colocs,
  studyData: studies,
  colocData: coloc,

  get getStudyToDisplay() {
    let studyId = (new URLSearchParams(location.search).get('id'))
    const study = this.studyData.find((item) => {
        return item.id == studyId
    })
    return study.name
  },

  get getDataForColocResults() {
    this.dataReceived = true 
    return this.colocData
  }
}))

Alpine.data('searchInput', () => ({
  isOpen: false,
  search: '',
  dummyData: studies,

  goToItem(item) {
    window.location.href = 'phenotype.html?id=' + item.id;
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
