fetch("navigation-bar.html")
    .then(stream => stream.text())
    .then(text => define(text));

class NavigationBar extends HTMLElement {
    // component implementation goes here
}

customElements.define('navigation-bar', MyComponent);

