import constants from "./constants.js";

export default function contact() {
    return {
        email: "",
        reason: "",
        message: "",
        submitting: false,
        successMessage: false,
        errorMessage: false,

        async submitForm() {
            this.submitting = true;
            this.successMessage = false;
            this.errorMessage = false;

            try {
                const response = await fetch(constants.apiUrl + "/info/contact", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        email: this.email,
                        reason: this.reason,
                        message: this.message,
                    }),
                });
                if (response.ok) {
                    this.successMessage = "Your message has been sent!";
                    this.email = "";
                    this.reason = "";
                    this.message = "";
                } else {
                    this.errorMessage = "There was a problem sending your message.";
                }
            } catch (e) {
                console.error(e);
                this.errorMessage = "There was a problem sending your message.";
            }
            this.submitting = false;
        },
    };
}
