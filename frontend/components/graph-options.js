class GraphOptions extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        fetch("components/graph-options.html")
            .then(stream => stream.text())
            .then(text => this.innerHTML = text)
    }
}

customElements.define('graph-options', GraphOptions);