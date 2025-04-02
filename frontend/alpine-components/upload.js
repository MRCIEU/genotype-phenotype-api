import Alpine from 'alpinejs'
import constants from './constants.js'

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
        },

        get gwasName() {
            return this.gwasUpload ? `${this.gwasUpload.name}` : '...';
        }
        
    }
} 