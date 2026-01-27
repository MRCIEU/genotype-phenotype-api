export class RPackageModal extends HTMLElement {
    constructor() {
        super();
        this.show = false;
        this.snippet = "";
    }

    static get observedAttributes() {
        return ["show", "snippet"];
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === "show") {
            this.show = newValue === "true";
        } else if (name === "snippet") {
            this.snippet = newValue;
        }
        this.render();
    }

    render() {
        this.innerHTML = `
            <div id="r-package-modal-internal" class="modal ${this.show ? "is-active" : ""}">
                <div class="modal-background" id="modal-bg"></div>
                <div class="modal-card">
                    <header class="modal-card-head">
                        <p class="modal-card-title">R Package Installation</p>
                        <button class="delete" aria-label="close" id="close-btn-header"></button>
                    </header>
                    <section class="modal-card-body pb-0 pt-0">
                        <div class="content">
                            <div class="box mt-4">
                                <pre><code>devtools::install_github('MRCIEU/gpmapr')\n${this.snippet}</code></pre>
                            </div>

                            <p class="mt-4">
                                <strong>Note:</strong> You'll need to have the <code>devtools</code> package
                                installed first.
                            </p>
                            <h4>Code and Documentation</h4>
                            <p>
                                <a
                                    href="https://github.com/MRCIEU/gpmapr"
                                    target="_blank"
                                    class="button is-success"
                                >
                                    <span>View on GitHub</span>
                                </a>
                                <br />
                                <br />
                                <a
                                    href="https://mrcieu.r-universe.dev/articles/gpmapr/gpmapr.html"
                                    target="_blank"
                                    class="button is-success"
                                    >View Vignettes</a
                                >
                            </p>
                        </div>
                    </section>
                    <footer class="modal-card-foot">
                        <button class="button" id="close-btn-footer">Close</button>
                    </footer>
                </div>
            </div>
        `;

        const closeBtnHeader = this.querySelector("#close-btn-header");
        const closeBtnFooter = this.querySelector("#close-btn-footer");
        const modalBg = this.querySelector("#modal-bg");

        const closeHandler = () => {
            this.dispatchEvent(new CustomEvent("close"));
        };

        if (closeBtnHeader) closeBtnHeader.addEventListener("click", closeHandler);
        if (closeBtnFooter) closeBtnFooter.addEventListener("click", closeHandler);
        if (modalBg) modalBg.addEventListener("click", closeHandler);
    }
}
