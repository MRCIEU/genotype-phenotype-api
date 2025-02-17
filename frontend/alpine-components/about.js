export default function about() {
  return {
    datasets: null,

    loadData() {
      fetch('../sample_data/datasets.json')
        .then(response => {
          return response.json()
        }).then(data => {
          this.datasets = data
        })
    },

    get getDatasetsForTable() {
      if (this.datasets === null) return []
      return this.datasets.datasets
    },

  }
}