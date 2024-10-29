import studies from '../sample_data/studies.json'

export default function search() {
  return {
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
  }
}