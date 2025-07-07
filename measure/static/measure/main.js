// static/main.js

console.log("Sanity check!");

fetch("/stripe_config/")
  .then((result) => result.json())
  .then((data) => {
    const stripe = Stripe(data.publicKey);

    const redirectToCheckout = () => {
      fetch("/create-checkout-session/")
        .then((result) => result.json())
        .then((data) => {
          console.log(data);
          return stripe.redirectToCheckout({ sessionId: data.sessionId });
        })
        .catch((error) => {
          console.error("Error during checkout:", error);
        });
    };

    // --- CORRECTED CODE IS HERE ---

    // Define the button IDs you want to target
    const buttonIds = [
      "#submit-menu-button",
      "#submitBtn",
      "#submit-measure-button",
      "#submit-measure-edit-button"
    ];

    // Loop through the IDs and add a listener if the button exists
    buttonIds.forEach(id => {
      const button = document.querySelector(id);
      if (button) { // This check prevents the error
        button.addEventListener("click", redirectToCheckout);
      }
    });

  })
  .catch((error) => {
    console.error("Error fetching Stripe config:", error);
  });