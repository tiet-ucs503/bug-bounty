---
abstract: |
  The rules every UI of the project keeps: designed for
  a phone first, styled by Tailwind's utilities, built
  in Svelte, in a visual language the project defines
  for itself. And four more: every state drawn, usable
  by everyone, a courtesy over the database, and
  nothing fetched from elsewhere.
date: 2026-10-07
keywords:
- conduct
- ui
- svelte
- tailwind
- mobile-first
- accessibility
kind: explanation
sources:
- ui/index.html
- ui/app.js
status: draft
subtitle: Mobile first, Tailwind, Svelte, and a visual
  language of your own
title: The UI's Conduct
version: v0.1.0
---

Eight rules, U1 to U8, for whoever writes a page of the
project's UI. The first four choose the tools and the
order of work. The last four are what the tools do not
give you.

## 1 U1 Mobile First

**Design for a phone, then add for wider screens.**
Never the other way.

- **Start at 360 px wide,** one column, read top to
  bottom. The wireframe of a concept is drawn at this
  width first

- **A wider screen adds, never repairs.** A style with
  no prefix is the phone's; `md:` and `lg:` add columns
  and room. If the phone needs a prefix to undo
  something, the order was wrong

- **Fingers, not pointers.** A button or a tick is at
  least 44 px each way. Nothing appears on hover alone

- **Text in a field is 16 px or more,** or a phone's
  browser zooms the page when the field is touched

- **`index.html` sets the viewport:**

  ``` html
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  ```

## 2 U2 Functional CSS: Tailwind

**Style in the markup, by Tailwind's utility classes.**
One class does one thing, and its name says what.

``` svelte
<div class="flex flex-col gap-3 md:flex-row md:items-center">
  <input class="rounded border border-ink px-3 py-2 text-base" aria-label="Display name" />
  <button class="rounded border-2 border-ink px-4 py-2 font-semibold">Save</button>
</div>
```

- **No class names of your own.** No `.card`, no
  `.row`. A part that repeats, a button or a card,
  becomes a component (U3), not a class
- **No `<style>` block and no `style=`,** but for a
  value computed at run time, such as a bar's width
- **No values of your own in brackets,** `p-[13px]` or
  `text-[#333]`. A step you miss is a step to add to
  the visual language (U4), once, for everyone
- **`@apply` only in the one stylesheet,** and only for
  what no component can hold: the page's `body`, a link
  in rendered text
- **The order of classes:** layout, box, type, colour,
  then the prefixed ones. Tailwind's own Prettier
  plugin sorts them, if the project formats by Prettier

Why utilities: a change to one part cannot break
another, since nothing is shared but the scale. And the
markup shows what a part looks like without a second
file open.

## 3 U3 Svelte

**Every page of the UI is Svelte, built by Vite into a
folder of static files.** The box serves files and runs
nothing of yours ([the UI](../ui/README.md) §5).

- **One component a file, one thing a component:** [the
  philosophy](philosophy.md). A component over about
  150 lines holds two things
- **State by runes:** `$state`, `$derived`, `$props`.
  No store until two distant components need the same
  thing
- **Data comes down, events go up.** A component is
  given what it shows, and tells its parent what
  happened. One module calls the services, with the
  token and the retries; no component calls `fetch`
- **No rendering on a server.** No SvelteKit server, no
  endpoint of the UI's own: an API is a service's
- **Tested by Vitest in jsdom,** finding each part as a
  person would: by its element, its label or its words,
  never by a class ([tutorial 6's
  tests](../tutorials/6-a-svelte-ui/3-tests.md))

## 4 U4 A Visual Language of Your Own

**The project defines its look once, as tokens, and
every part uses the tokens alone.** This page does not
choose the look. It says what must be chosen:

- **Colours by their job,** not their hue: the ground,
  the ink, a muted ink, one accent, one for danger. A
  light and a dark value each
- **Type:** one family, and a scale of four or five
  sizes
- **Space:** one scale, used for every gap and padding
- **Shape:** one radius, one border's width, and
  whether anything casts a shadow
- **Emphasis:** what the one main action of a part
  looks like, and that a part has only one
- **Words:** how the UI speaks. [Writing](writing.md)
  holds for a button as for a page

The tokens live in the one stylesheet, as Tailwind's
theme, so each becomes a utility. **An example, not the
project's:** a plain look, ink on paper.

``` css
@import "tailwindcss";

@theme {
  --color-ground: #ffffff;
  --color-ink: #111111;
  --color-muted: #6b6b6b;
  --color-accent: #111111;
  --color-danger: #b00020;
  --font-sans: system-ui, sans-serif;
  --radius-box: 4px;
}
```

From it, `bg-ground`, `text-ink`, `text-muted`,
`border-danger` and `rounded-box` exist, and no other
colour should appear in the markup. The example gives
the light values alone. A first line in the theme,
`--color-*: initial`, takes Tailwind's own colours
away, so that none other can.

[Tutorial 6's
implementation](../tutorials/6-a-svelte-ui/4-implementation.md)
§3 to §5 is all of this at work: a theme with its dark
values, five small parts, and a dashboard built of
them.

Write your own, and a page beside [the
UI's](../ui/README.md) that shows it: each token, its
job, and one part drawn with it.

## 5 U5 Every State Drawn Before It Is Built

A part has more states than the one in the designer's
head. The concept's wireframe draws each ([the
concept](the-cycle/concept.md) §3; [tutorial
6's](../tutorials/6-a-svelte-ui/1-concept.md) §3):

- **Waiting,** before the answer
- **Empty,** when the answer is nothing
- **Refused,** signed out or without the permission
- **Failed,** when the service did not answer
- **Full,** the one everybody draws

Each state has a test.

## 6 U6 Usable by Everyone

- **The right element:** a `button` for an action, an
  `a` for a place, a `label` for every field, headings
  in order. A `div` with a click handler is none of
  these
- **The keyboard reaches everything,** in the order it
  is read, and the focus can be seen
- **Contrast of 4.5 to 1** for text, in both themes.
  Colour is never the only sign: an error has words
- **Motion stops** for whoever asks,
  `prefers-reduced-motion`
- **A test finds a part by its element or its label**
  (U3). A part a test cannot find that way, a screen
  reader cannot either

## 7 U7 A Courtesy over the Database

**The UI shows what a person may do; the database
decides.** A button hidden is a kindness, not a guard:
whoever calls the API by hand meets the same refusal
([the database's conduct](database.md) §2).

- **What to show comes from `/users/me`,** its
  permissions, never from a role's name or an e-mail
- **Every call can be refused,** and the part says so
  in words
- **The access token stays in `sessionStorage`,** as
  the starter keeps it, and nowhere longer-lived. No
  secret is ever in the UI: its files are public

## 8 U8 Nothing from Elsewhere

**At run time, the page asks only its own origin and
the project's services.** No font, script, style or
image from another site: each is a third party who
learns of every visit, and a way for the page to break.

- **Fonts and icons are files of the UI,** or the
  system's
- **`config.js` is read at run time,** never bundled,
  so one build serves any zone ([Release the
  UI](../ui/release.md))
- **A new dependency is a decision,** written in the
  merge request: what it is for, and what was tried
  without it

## 9 See Also

- [The UI](../ui/README.md): what the box asks of any
  UI
- [The concept](the-cycle/concept.md): the artefact,
  for a page a wireframe
- [The philosophy](philosophy.md): one thing, done well
