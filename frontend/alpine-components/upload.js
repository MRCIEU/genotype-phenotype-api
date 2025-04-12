import constants from './constants'

export default function upload() {
    return {
        gwasUpload: {},

        async loadData() {
            let gwasId = (new URLSearchParams(location.search).get('id'))
            try {
                const response = await fetch(constants.apiUrl + '/gwas/' + gwasId);
                if (!response.ok) {
                    this.errorMessage = `Failed to load gwas: ${gwasId}. Please try again later.`
                    console.log(this.errorMessage)
                    return
                }
                this.gwasUpload = await response.json();
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }
    }
}