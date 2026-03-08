export class Footer extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        fetch("web-components/footer.html")
            .then(stream => stream.text())
            .then(text => {
                this.innerHTML = text;
                const yearEl = this.querySelector("#footer-year");
                if (yearEl) {
                    yearEl.textContent = new Date().getFullYear();
                }
            });
    }
}
