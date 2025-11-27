export class GraphOptions extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        const showIncludeTrans = this.getAttribute("show-include-trans");
        const showPhenotype = this.getAttribute("show-phenotype");

        fetch("web-components/graph-options.html")
            .then(stream => stream.text())
            .then(text => {
                this.innerHTML = text;
                const root = this.querySelector("#graphOptions");
                if (root) {
                    root.dataset.showIncludeTrans = showIncludeTrans !== null ? showIncludeTrans : "true";
                    root.dataset.showPhenotype = showPhenotype !== null ? showPhenotype : "true";
                }
            });
    }
}
