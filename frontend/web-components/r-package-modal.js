const TEMPLATE_URL = "web-components/r-package-modal.html";

let templateCache = null;

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

async function getTemplate() {
    if (templateCache) return templateCache;
    const response = await fetch(TEMPLATE_URL);
    templateCache = await response.text();
    return templateCache;
}

export class RPackageModal extends HTMLElement {
    constructor() {
        super();
        this.show = false;
        this.snippet = "";
        this.pythonSnippet = "";
    }

    static get observedAttributes() {
        return ["show", "snippet", "python-snippet"];
    }

    connectedCallback() {
        this.render();
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === "show") {
            this.show = newValue === "true";
        } else if (name === "snippet") {
            this.snippet = newValue;
        } else if (name === "python-snippet") {
            this.pythonSnippet = newValue;
        }
        this.render();
    }

    async render() {
        const show = this.getAttribute("show") === "true";
        const snippet = this.getAttribute("snippet") ?? this.snippet ?? "";
        const pythonSnippet = this.getAttribute("python-snippet") ?? this.pythonSnippet ?? "";
        const template = await getTemplate();
        const html = template
            .replace("{{MODAL_ACTIVE_CLASS}}", show ? "is-active" : "")
            .replace("{{SNIPPET}}", escapeHtml(snippet))
            .replace("{{PYTHON_SNIPPET}}", escapeHtml(pythonSnippet));

        this.innerHTML = html;

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
