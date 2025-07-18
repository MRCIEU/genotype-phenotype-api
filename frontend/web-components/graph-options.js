export class GraphOptions extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        fetch("web-components/graph-options.html")
            .then(stream => stream.text())
            .then(text => this.innerHTML = text);
    }
}
