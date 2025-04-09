import pipeline from '../assets/images/pipeline.png'

export default function about() {
    return {
        pipeline,
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