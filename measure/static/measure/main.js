// static/main.js
console.log("Sanity check!");

// Fetch the Stripe publishable key once when the page loads
fetch("/stripe_config/")
  .then((result) => result.json())
  .then((data) => {
    // Initialize Stripe.js with the public key
    const stripe = Stripe(data.publicKey);

    // A reusable function to handle the checkout process
    const redirectToCheckout = () => {
      // Get a new Checkout Session ID from the server
      fetch("/create-checkout-session/")
        .then((result) => result.json())
        .then((data) => {
          console.log(data);
          // Redirect to Stripe Checkout
          return stripe.redirectToCheckout({ sessionId: data.sessionId });
        })
        .then((res) => {
          // This promise will only resolve if there's an error in the redirection
          console.log(res);
        })
        .catch((error) => {
          console.error("Error:", error);
        });
    };

    // Add event listeners to all your checkout buttons
    document.querySelector("#submit-menu-button").addEventListener("click", redirectToCheckout);
    document.querySelector("#submitBtn").addEventListener("click", redirectToCheckout);
    document.querySelector("#submit-measure-button").addEventListener("click", redirectToCheckout);
    document.querySelector("#submit-measure-edit-button").addEventListener("click", redirectToCheckout);
  })
  .catch((error) => {
    console.error("Error fetching Stripe config:", error);
  });