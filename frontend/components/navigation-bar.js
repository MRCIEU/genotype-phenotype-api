class NavigationBar extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        fetch("components/navigation-bar.html")
            .then(stream => stream.text())
            .then(text => this.innerHTML = text)
    }
}

customElements.define('navigation-bar', NavigationBar);