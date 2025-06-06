import constants from './constants.js'

export default function data() {
    return {
        studySources: null,

        async loadData() {
            const response = await fetch(constants.apiUrl + '/info/study_sources');
            if (!response.ok) {
                this.errorMessage = `Failed to load study sources. Please try again later.`
                console.log(this.errorMessage)
                return
            }
            this.studySources = await response.json()
        },

        get getStudySources() {
            if (this.studySources === null) return []
            return this.studySources.sources
        },

    }
}