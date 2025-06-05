export class PipelineSummary extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        fetch("web-components/pipeline-summary.html")
            .then(stream => stream.text())
            .then(text => this.innerHTML = text)
    }
}
