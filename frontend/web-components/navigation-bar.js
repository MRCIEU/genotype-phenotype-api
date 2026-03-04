export class NavigationBar extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        fetch("web-components/navigation-bar.html")
            .then(stream => stream.text())
            .then(text => {
                this.innerHTML = text;
                this.setupBurgerMenu();
            });
    }
    setupBurgerMenu() {
        const burger = this.querySelector(".navbar-burger");
        const menu = this.querySelector("#navbarBasicExample");
        if (burger && menu) {
            burger.addEventListener("click", () => {
                burger.classList.toggle("is-active");
                menu.classList.toggle("is-active");
                burger.setAttribute("aria-expanded", burger.classList.contains("is-active"));
            });
        }
    }
}
