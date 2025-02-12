export class NavigationBar extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        fetch("web-components/navigation-bar.html")
            .then(stream => stream.text())
            .then(text => this.innerHTML = text)
    }
}
