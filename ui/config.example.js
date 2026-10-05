// Copy to config.js, which git ignores, and fill in from what the
// box's owner gives you after your project's onboarding. None is a
// secret: each is in every sign-in URL and every page load. config.js
// is what you release with the rest of ui/.
export default {
  // Cognito's hosted sign-in, the box's pool: <prefix>.auth.<region>.amazoncognito.com
  authDomain: "",
  // Your project's UI client, tu-rgb-sites-<project>-ui
  clientId: "",
  // Your zone: the APIs are <service>.<zone>
  zone: "",
  // Your services, as box/project.json names them
  apis: ["js-api", "py-api"],
};
