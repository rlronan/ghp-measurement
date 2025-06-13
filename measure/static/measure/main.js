// static/main.js

console.log("Sanity check!");

// Get Stripe publishable key
fetch("/stripe_config/")
.then((result) => { return result.json(); })
.then((data) => {
  // Initialize Stripe.js
  const stripe = Stripe(data.publicKey);
  
// new
  // Event handler
  // document.querySelector("#submitBtn").addEventListener("click", () => {
  //   // Get Checkout Session ID
  //   fetch("/create-checkout-session/")
  //   .then((result) => { return result.json(); })
  //   .then((data) => {
  //     console.log(data);
  //     // Redirect to Stripe Checkout
  //     return stripe.redirectToCheckout({sessionId: data.sessionId})
  //   })
  //   .then((res) => {
  //     console.log(res);
  //   });
  // });
// Event handler for menu button
  document.querySelector("#submit-menu-button").addEventListener("click", () => {
    // Get Checkout Session ID
    fetch("/create-checkout-session/")
    .then((result) => { return result.json(); })
    .then((data) => {
      console.log(data);
      // Redirect to Stripe Checkout
      return stripe.redirectToCheckout({sessionId: data.sessionId})
    })
    .then((res) => {
      console.log(res);
    });
  });
});


fetch("/stripe_config/")
.then((result) => { return result.json(); })
.then((data) => {
  // Initialize Stripe.js
  const stripe = Stripe(data.publicKey);
  
// new
  // Event handler
  document.querySelector("#submitBtn").addEventListener("click", () => {
    // Get Checkout Session ID
    fetch("/create-checkout-session/")
    .then((result) => { return result.json(); })
    .then((data) => {
      console.log(data);
      // Redirect to Stripe Checkout
      return stripe.redirectToCheckout({sessionId: data.sessionId})
    })
    .then((res) => {
      console.log(res);
    });
  });
});


fetch("/stripe_config/")
.then((result) => { return result.json(); })
.then((data) => {
  // Initialize Stripe.js
  const stripe = Stripe(data.publicKey);
  
// new
  // Event handler
  document.querySelector("#submit-measure-button").addEventListener("click", () => {
    // Get Checkout Session ID
    fetch("/create-checkout-session/")
    .then((result) => { return result.json(); })
    .then((data) => {
      console.log(data);
      // Redirect to Stripe Checkout
      return stripe.redirectToCheckout({sessionId: data.sessionId})
    })
    .then((res) => {
      console.log(res);
    });
  });
});


fetch("/stripe_config/")
.then((result) => { return result.json(); })
.then((data) => {
  // Initialize Stripe.js
  const stripe = Stripe(data.publicKey);
  
// new
  // Event handler
  document.querySelector("#submit-measure-edit-button").addEventListener("click", () => {
    // Get Checkout Session ID
    fetch("/create-checkout-session/")
    .then((result) => { return result.json(); })
    .then((data) => {
      console.log(data);
      // Redirect to Stripe Checkout
      return stripe.redirectToCheckout({sessionId: data.sessionId})
    })
    .then((res) => {
      console.log(res);
    });
  });
});