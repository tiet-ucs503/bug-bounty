// The dev stack's config (docs/onboarding/local-dev.md): copy to
// config.js for local work. The mock sign-in on localhost:9000, and the
// services through the dev stack's nginx at http://<service>.localhost:8080,
// which browsers resolve to this machine. Nothing here is a secret.
export default {
  authDomain: "http://localhost:9000",
  clientId: "dev-ui",
  zone: "localhost",
  apis: ["js-api", "py-api"],
  apiUrl: (service) => `http://${service}.localhost:8080`,
  staticUrl: "http://static.localhost:8080",
};
