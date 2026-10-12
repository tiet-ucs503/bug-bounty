# Big Bounty UI Conduct

Mobile first, Tailwind, Svelte, and a visual language of our own

## Abstract

Big Bounty is an anonymous peer-testing platform with a student portal and a faculty portal. Two things shape these rules: students are on phones, and anonymity is the product.

## U1 Mobile First

Design for a phone, then add for wider screens. Never the other way.

- Start at 360 px wide, one column, read top to bottom. Sketch every page at this width first.
- A wider screen adds, never repairs. A class with no prefix is the phone's; `md:` and `lg:` add columns and room. If the phone needs a prefix to undo something, the order was wrong.
- Fingers, not pointers. A button or a tick is at least 44 px each way. Nothing appears on hover alone.
- Text in a field is 16 px or more (`text-base`), or a phone's browser zooms the page on touch.
- The faculty Sidebar becomes a top bar or a drawer on a phone. It is a wide-screen addition, not the default layout.
- `app.html` sets the viewport:

&#91;embedded content: phone layout vs wide layout\]

The phone layout is the base; the accent shows what md: and lg: add.

```html
<meta name="viewport" content="width=device-width, initial-scale=1" />
```

## U2 Functional CSS: Tailwind

Style in the markup, by Tailwind's utility classes. One class does one thing, and its name says what.

```html
<div class="flex flex-col gap-3 md:flex-row md:items-center">
  <input class="rounded-box border border-ink px-3 py-2 text-base" aria-label="Project title" />
  <button class="rounded-box border-2 border-ink px-4 py-2 font-semibold">Submit</button>
</div>
```

- No class names of your own. No `.card`, no `.row`. A part that repeats becomes a component (U3), not a class.
- No `<style>` block and no `style=`, except for a value computed at run time, such as a progress bar's width.
- No values of your own in brackets: `p-[13px]` and `text-[#333]` are out. A step you miss is a step to add to the visual language (U4), once, for everyone.
- `@apply` only in the one stylesheet, and only for what no component can hold: the page's body, a link inside rendered Markdown.
- Class order: layout, box, type, colour, then the prefixed ones. Use `prettier-plugin-tailwindcss` to sort them.

Why utilities: a change to one part cannot break another, since nothing is shared but the scale.

## U3 Svelte

Every page is Svelte, built by Vite into a folder of static files. The host serves files and runs nothing of ours.

- Keep SvelteKit only as a static single-page app: `adapter-static` with a fallback page, `ssr = false` at the root. No `hooks.server.js`, no `+server.js`, no form actions. An API is a service's, not the UI's.
- One component a file, one thing a component. A component over about 150 lines holds two things.
- State by runes: `$state`, `$derived`, `$props`. No store until two distant components need the same thing. Today's stores are `auth`, `theme`, and `appState`, and that is the limit until a fourth is argued for.
- Data comes down, events go up. A component is given what it shows and tells its parent what happened. Components never call `fetch`. One module in `src/lib/api` talks to the backend.
- Shared parts live in `src/lib/components`: Navbar, Sidebar, Footer, DashboardCard, FilterableEntityList, MarkdownEditor, FileUpload, SuccessModal, ProfileContent. Add to that list rather than copying a part into a page.
- Tested by Vitest with Testing Library in jsdom, finding each part as a person would: by its role, its label, or its words, never by a class.

&#91;embedded content: data flow · 4 layers\]

Data flows down from the service to the component; events flow up, and only the api module touches the network.

## U4 A Visual Language of Our Own

The project defines its look once, as tokens, and every part uses the tokens alone. Choose, and write down:

- **Colours by their job, not their hue:** ground, ink, muted ink, one accent, one for danger, one for success. A light and a dark value each.
- **Type:** one family, and a scale of four or five sizes.
- **Space:** one scale, used for every gap and padding.
- **Shape:** one radius, one border width, and whether anything casts a shadow.
- **Emphasis:** what the one main action of a part looks like, and that a part has only one.
- **Words:** how the UI speaks. Plain, short, and kind. Writing holds for a button as for a page.
- **Roles:** students and faculty share one look. A role changes what is shown, never how it looks.

Because the project has a dark-mode toggle, tokens are CSS variables that change under a `.dark` class, and Tailwind names them. In `src/app.css`:

```css
:root {
  --ground: 255 255 255;
  --ink: 17 17 17;
  --muted: 107 107 107;
  --accent: 17 17 17;
  --danger: 176 0 32;
  --success: 14 107 58;
}
.dark {
  --ground: 17 17 17;
  --ink: 245 245 245;
  --muted: 170 170 170;
  --accent: 245 245 245;
  --danger: 255 107 107;
  --success: 98 214 143;
}
```

In `tailwind.config.js`, replace the theme's colours so no other colour can appear:

```js
colors: {
  ground: 'rgb(var(--ground) / <alpha-value>)',
  ink: 'rgb(var(--ink) / <alpha-value>)',
  muted: 'rgb(var(--muted) / <alpha-value>)',
  accent: 'rgb(var(--accent) / <alpha-value>)',
  danger: 'rgb(var(--danger) / <alpha-value>)',
  success: 'rgb(var(--success) / <alpha-value>)',
  transparent: 'transparent'
},
borderRadius: { none: '0', box: '4px' },
fontFamily: { sans: ['system-ui', 'sans-serif'] }
```

From it, `bg-ground`, `text-ink`, `text-muted`, `border-danger`, and `rounded-box` exist, and no other colour appears in the markup. This is an example, not the final look. If the project moves to Tailwind 4, the same tokens go in an `@theme` block.

Keep a page at `/design` that shows each token, its job, and one part drawn with it, in both themes.

## U5 Every State Drawn Before It Is Built

A part has more states than the one in the designer's head. Draw each before building:

- **Waiting:** before the answer arrives.
- **Empty:** the answer is nothing (no teams yet, no submissions to test).
- **Refused:** signed out, or not allowed. A student on a faculty page lands here, with words.
- **Failed:** the service did not answer. Say so and offer a retry.
- **Full:** the one everybody draws.

&#91;embedded content: the five states of a part\]

The five states side by side, as the wireframe should draw them.

Each state has a test. Lists, dashboards, and the submit and testing flows are the parts most likely to be missing four of the five.

## U6 Usable by Everyone

- The right element: a `button` for an action, an `a` for a place, a `label` for every field, headings in order. A `div` with a click handler is none of these.
- The keyboard reaches everything, in the order it is read, and the focus can be seen. Modals (SuccessModal) trap focus, close on Escape, and return focus to what opened them.
- Contrast of 4.5 to 1 for text, in both themes. Colour is never the only sign: an error has words, a status has a label.
- Motion stops for whoever asks (`motion-reduce:`).
- The Markdown editor and file upload work without a mouse, and say what they accept and what went wrong.
- A test finds a part by its element or its label (U3). A part a test cannot find that way, a screen reader cannot either.

## U7 Honest About the Sign-In, Careful with Anonymity

The UI shows what a person may do. The backend decides.

- **The mock sign-in is a demo, and must say so.** Until a real backend exists, `auth.js` is a stand-in. Nothing in the UI may hold or imply real security, and nothing sensitive is stored.
- A hidden button is a kindness, not a guard. Whoever calls the API by hand meets the same refusal once it exists.
- What to show comes from a permissions object in the session (`/users/me` when it exists), never from a role's name or an e-mail address scattered through components. One helper answers "may this person do this?"
- Session data goes in `sessionStorage`, not `localStorage`, and never anything longer-lived. No secret is ever in the UI: its files are public.
- **Anonymity is a rule of the UI, not a feature.** A tester's identity is never shown to the team being tested, nor in a URL, a page title, an image name, or a log line. Show what the person needs and no more. If a part could reveal who wrote a review, it is a bug.
- Every call can be refused, and the part says so in words.

## U8 Preferably Self-Delivered

What the page loads comes from its own origin, where that is reasonable. A font, script, or style from another site is a third party who learns of every visit, and a way for the page to break.

- Fonts and icons are files of the UI, or the system's.
- If something must come from elsewhere: by its exact version, never `latest` or a range; with its hash, `integrity="sha384-..."`; and named in the merge request with what it is, who delivers it, and why not from our own files.
- Never anything that handles a person's data. A script from elsewhere runs with the page's rights.
- A new dependency is a decision, written in the merge request: what it is for, and what was tried without it.
- Environment settings (the API address) are read at run time from a config file, never baked into the build, so one build serves any deployment.

## Before You Open a Merge Request

1. Does it work at 360 px with nothing prefixed to undo?
2. Any custom class, `style=`, or bracketed value? Remove it.
3. Any colour not from the tokens? Add the token or use one.
4. Are all five states drawn and tested?
5. Can I use it with a keyboard alone, in both themes?
6. Could this reveal who a tester is?
7. Does it load anything from outside our origin?
