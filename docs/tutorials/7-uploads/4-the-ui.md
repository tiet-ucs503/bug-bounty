---
abstract: |
  Step 4 of tutorial 7, part 4. The dashboard's half of
  the uploads, a step at a time: a file selector on a
  note you are editing; each note's attachments shown,
  images as images; the type and size checked before
  anything is sent; then drag and drop onto the same
  place; and a way to take an attachment off. The
  finished component whole, and the dashboard driven
  through it.
date: 2026-10-06
keywords:
- tutorial
- uploads
- ui
- svelte
kind: tutorial
sources:
- ui/src/Notes.svelte
- ui/src/lib/box.js
status: draft
subtitle: From a file selector to drag and drop
title: "7.4 Uploads: the UI"
version: v0.1.0
---

## 1 Before You Start

- [What you need](../README.md) §2, installed and
  checked
- [The service](4-the-service.md), running
- [6 A Svelte UI](../6-a-svelte-ui/README.md), with
  `make ui` serving it
- `api()` in `ui/src/lib/box.js` already sends a file
  as itself, by `raw` (tutorial 6's
  [implementation](../6-a-svelte-ui/4-implementation.md)
  §3)
- [The UI's conduct](../../conduct/ui.md): the look is
  Tailwind's utilities and tutorial 6's six parts, no
  class and no `<style>` of your own

## 2 Step 1: a File Selector

A component for one note's attachments. Its first cut
does one thing: the files chosen go to py-api, one at a
time, then the note's list is saved.
`ui/src/Attach.svelte`:

``` svelte
<script>
  // One note's attachments, a first cut: files chosen, uploaded one at
  // a time to py-api, then the note's list saved
  import { api } from "./lib/box.js";

  let { note, onchange } = $props();
  let keys = $state(note.objects.map((o) => o.key));
  let status = $state("");

  async function upload(files) {
    for (const file of [...files]) {
      status = `${file.name}: uploading…`;
      const r = await api("py-api", "/objects/new", { method: "POST", raw: file });
      if (r.status !== 201) {
        status = `${file.name}: ${r.data.error ?? r.status}`;
        continue;
      }
      if (!keys.includes(r.data.key)) keys.push(r.data.key);
      status = `${file.name}: uploaded`;
    }
    const r = await api("py-api", `/notes/${note.id}/objects`, { method: "PUT", body: { keys } });
    if (r.status !== 200) status = r.data.error ?? `py-api: ${r.status}`;
    onchange();
  }
</script>

<label class="flex flex-wrap items-center gap-2">
  Attach files
  <input class="min-h-11 max-w-full text-base" type="file" multiple onchange={(e) => upload(e.currentTarget.files)} />
</label>
{#if status}<div class="text-muted" aria-live="polite">{status}</div>{/if}
```

`[...files]` copies the list first: the browser may
empty the input's own while the uploads run.

In `ui/src/Notes.svelte`, import it beside `api`:

``` svelte
  import Attach from "./Attach.svelte";
```

and put it under the Save and Cancel buttons, so it
shows only on a note you are editing, which is always
your own:

``` svelte
            <Attach {note} onchange={load} />
```

Edit a note of yours, choose a PNG, and expect
`blue.png: uploaded`.

## 3 Step 2: Show What a Note Has

Each note now brings its objects, key and type ([the
service](4-the-service.md) §3). In `Notes.svelte`,
`staticBase` from `box.js`, and tutorial 6's `Chip`:

``` svelte
  import { api, staticBase } from "./lib/box.js";
  import Chip from "./lib/Chip.svelte";
```

Under each note's body, when it is not being edited,
its attachments, an image as an image and anything else
as its type, each a link to the object:

``` svelte
            {#if note.objects.length}
              <div class="my-2 flex flex-wrap items-center gap-2">
                {#each note.objects as o (o.key)}
                  <a href={`${staticBase}/${o.key}`} target="_blank" rel="noopener">
                    {#if o.type.startsWith("image/")}
                      <img class="max-h-24 max-w-40 rounded-box border border-line" src={`${staticBase}/${o.key}`}
                           alt="An attachment" loading="lazy" />
                    {:else}
                      <Chip>{o.type}</Chip>
                    {/if}
                  </a>
                {/each}
              </div>
            {/if}
```

The image's size is in its classes, `max-h-24` and
`max-w-40`: no `<style>` block ([the UI's
conduct](../../conduct/ui.md), U2).

Save, cancel, and expect the image under the note.
Everyone who may read notes sees it: (u=rw, a=r).

## 4 Step 3: Check Before Sending

py-api refuses a wrong type or a large file, but only
after the bytes have crossed the network. Check first,
with what py-api allows:

``` js
  const TYPES = "image/png,image/jpeg,image/gif,image/webp,application/pdf,text/plain";
  const MAX = 1024 * 1024;
```

The input offers those alone, `accept={TYPES}`; and the
upload skips, with a reason, what slips through, at the
top of its loop:

``` js
      if (file.size > MAX) {
        status = `${file.name}: over 1 MiB`;
        continue;
      }
      if (!TYPES.split(",").includes(file.type)) {
        status = `${file.name}: ${file.type || "an unknown type"} is not allowed`;
        continue;
      }
```

`accept` is a hint to the picker, not a check: a
dropped file never meets it. Hence the loop's.

## 5 Step 4: Drag and Drop

The same upload, for files dropped on the component.
Three events: `dragover`, whose default must be
prevented or the browser will not allow a drop;
`dragleave`, to undo the highlight; and `drop`, whose
default must be prevented too, or the browser opens the
file:

``` js
  function drop(e) {
    e.preventDefault();
    over = false;
    upload(e.dataTransfer.files);
  }
```

Around the selector, a zone that says so:

``` svelte
<div class={["my-2 rounded-box border-2 border-dashed p-3", over ? "border-accent bg-accent/10" : "border-line"]}
     role="group" aria-label="Attachments"
     ondragover={(e) => { e.preventDefault(); over = true; }}
     ondragleave={() => (over = false)}
     ondrop={drop}>
```

`over`, a `$state`, lights the zone while a file is
held over it: the second half of the class list chooses
the accent's border and a tenth of its colour behind,
`bg-accent/10`.

## 6 Step 5: Take One Off

Each key listed, with tutorial 6's `Button` beside it,
which drops it from the list and saves. The object is let go, and the collector
takes it after the grace, if no other note of yours
refers to it.

## 7 The Component, Whole

`ui/src/Attach.svelte`, all five steps:

``` svelte
<script>
  // One note's attachments: files chosen, or dropped here, uploaded one
  // at a time to py-api, then the note's list saved. Each upload is an
  // object in the static bucket, read back from static.<zone>
  import { api } from "./lib/box.js";
  import Button from "./lib/Button.svelte";

  let { note, onchange } = $props();
  let keys = $state(note.objects.map((o) => o.key));
  let status = $state("");
  let over = $state(false);

  // As py-api allows; the browser's picker offers these alone
  const TYPES = "image/png,image/jpeg,image/gif,image/webp,application/pdf,text/plain";
  const MAX = 1024 * 1024;

  async function upload(files) {
    for (const file of [...files]) {
      if (file.size > MAX) {
        status = `${file.name}: over 1 MiB`;
        continue;
      }
      if (!TYPES.split(",").includes(file.type)) {
        status = `${file.name}: ${file.type || "an unknown type"} is not allowed`;
        continue;
      }
      status = `${file.name}: uploading…`;
      const r = await api("py-api", "/objects/new", { method: "POST", raw: file });
      if (r.status !== 201) {
        status = `${file.name}: ${r.data.error ?? r.status}`;
        continue;
      }
      if (!keys.includes(r.data.key)) keys.push(r.data.key);
      status = `${file.name}: uploaded`;
    }
    await save();
  }

  async function save() {
    const r = await api("py-api", `/notes/${note.id}/objects`, { method: "PUT", body: { keys } });
    if (r.status !== 200) status = r.data.error ?? `py-api: ${r.status}`;
    onchange();
  }

  function remove(key) {
    keys = keys.filter((k) => k !== key);
    save();
  }

  function drop(e) {
    e.preventDefault();
    over = false;
    upload(e.dataTransfer.files);
  }
</script>

<div class={["my-2 rounded-box border-2 border-dashed p-3", over ? "border-accent bg-accent/10" : "border-line"]}
     role="group" aria-label="Attachments"
     ondragover={(e) => { e.preventDefault(); over = true; }}
     ondragleave={() => (over = false)}
     ondrop={drop}>
  <label class="flex flex-wrap items-center gap-2">
    Attach files
    <input class="min-h-11 max-w-full text-base" type="file" multiple accept={TYPES}
           onchange={(e) => upload(e.currentTarget.files)} />
  </label>
  <span class="text-muted">or drop them here</span>
  {#if status}<div class="text-muted" aria-live="polite">{status}</div>{/if}
  {#each keys as key (key)}
    <div class="my-2 flex flex-wrap items-center gap-2">
      <code>{key.slice(-12)}</code><Button onclick={() => remove(key)}>Remove</Button>
    </div>
  {/each}
</div>
```

And `ui/src/Notes.svelte`, whole:

``` svelte
<script>
  // Every note, (u=rw, a=r): yours to change, the rest to read. The
  // buttons follow the permissions; the database decides regardless
  import { api, staticBase } from "./lib/box.js";
  import Attach from "./Attach.svelte";
  import Button from "./lib/Button.svelte";
  import Card from "./lib/Card.svelte";
  import Chip from "./lib/Chip.svelte";
  import Field from "./lib/Field.svelte";
  import Loaded from "./lib/Loaded.svelte";
  import Section from "./lib/Section.svelte";

  let { canWrite } = $props();
  // null until the first answer: waiting is not the same as none
  let notes = $state(null);
  let draft = $state("");
  let editing = $state(null);
  let error = $state("");
  let failed = $state("");

  async function load() {
    failed = "";
    try {
      const r = await api("py-api", "/notes");
      if (r.status === 200) notes = r.data;
      else failed = r.data.error ?? `py-api: ${r.status}`;
    } catch {
      failed = "py-api: no answer";
    }
  }

  async function call(path, opts) {
    error = "";
    const r = await api("py-api", path, opts);
    if (r.status >= 400) error = r.data.error ?? `py-api: ${r.status}`;
    await load();
    return r.status < 400;
  }

  async function add() {
    if (await call("/notes", { method: "POST", body: { body: draft } })) draft = "";
  }

  async function save() {
    if (await call(`/notes/${editing.id}`, { method: "PUT", body: { body: editing.body } })) editing = null;
  }

  load();
</script>

<Section title="Notes">
  <Loaded what="the notes" waiting={notes === null} {failed} retry={load}>
    {#if error}<p class="my-2 text-danger">{error}</p>{/if}
    {#if canWrite}
      <Field multiline label="A new note" bind:value={draft} />
      <div class="my-2"><Button primary onclick={add} disabled={!draft.trim()}>Add</Button></div>
    {/if}
    <ul class="flex flex-col gap-2">
      {#each notes as note (note.id)}
        <Card>
          {#if editing?.id === note.id}
            <Field multiline label="Edit the note" bind:value={editing.body} />
            <div class="mt-2 flex flex-wrap gap-2">
              <Button primary onclick={save}>Save</Button>
              <Button onclick={() => (editing = null)}>Cancel</Button>
            </div>
            <Attach {note} onchange={load} />
          {:else}
            <p class="break-words">{note.body}</p>
            {#if note.objects.length}
              <div class="my-2 flex flex-wrap items-center gap-2">
                {#each note.objects as o (o.key)}
                  <a href={`${staticBase}/${o.key}`} target="_blank" rel="noopener">
                    {#if o.type.startsWith("image/")}
                      <img class="max-h-24 max-w-40 rounded-box border border-line" src={`${staticBase}/${o.key}`}
                           alt="An attachment" loading="lazy" />
                    {:else}
                      <Chip>{o.type}</Chip>
                    {/if}
                  </a>
                {/each}
              </div>
            {/if}
            <p class="mt-1 text-sm text-muted">
              {note.mine ? "yours" : "another's"}, {new Date(note.created_at).toLocaleString()}
            </p>
            {#if note.mine && canWrite}
              <div class="mt-2 flex flex-wrap gap-2">
                <Button onclick={() => (editing = { id: note.id, body: note.body })}>Edit</Button>
                <Button onclick={() => call(`/notes/${note.id}`, { method: "DELETE" })}>Delete</Button>
              </div>
            {/if}
          {/if}
        </Card>
      {:else}
        <li class="text-muted">No notes yet.</li>
      {/each}
    </ul>
  </Loaded>
</Section>
```

## 8 Its Tests

`ui/test/attach.test.js`, from [the tests](3-tests.md)
§2, beside tutorial 6's. And one change to tutorial
6's: the notes it fakes now carry their objects, as
`GET /notes` answers them since [the
service](4-the-service.md) §3. In
`ui/test/dashboard.test.js`, `NOTES` becomes:

``` javascript
// Each with its objects, as GET /notes answers since tutorial 7
const NOTES = [
  { id: 2, body: "mine", mine: true, created_at: "2026-10-07T10:00:00Z", updated_at: null, objects: [] },
  { id: 1, body: "theirs", mine: false, created_at: "2026-10-07T09:00:00Z", updated_at: null, objects: [] },
];
```

Why, [the refinement](5-refinement.md) §5 tells. Expect
`13 passed`:

``` sh
cd ui && npm test && cd ..
```

## 9 Try It

As asha, a member: edit a note of yours; choose a PNG;
drop another on the dashed zone; drop an `.html` file
and expect `page.html: text/html is not allowed`; save;
and expect both images under the note. Then as bhanu, a
reader: the images, and no Edit.

Take one image off, keep its link, and wait out the
grace: the link answers `404`, unless another note of
yours still refers to it.

## 10 What Can Go Wrong

- **The browser opens the dropped file.** `drop`'s
  default was not prevented, or the drop missed the
  zone
- **The zone never lights.** `dragover`'s default was
  not prevented
- **`objects.write needed`, for a member.** [The
  database](4-the-database.md)'s migration has not run:
  the role lacks the cell
- **Images do not load, `404`.** The object was
  collected, or `staticUrl` in `config.js` names
  another host: `http://static.localhost:8080` here,
  your `static.<zone>` on the box
- **A large photo is refused.** 1 MiB is the box's
  limit on an API host ([the concept](1-concept.md) §2,
  O4). Shrink it in the browser before upload, or ask
  the box's owner

## 11 See Also

- [The refinement](5-refinement.md): next
- [The HTML Drag and Drop
  API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API)
  and [the file
  input](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/file),
  read 2026-10-06
- [The tutorials](../README.md): the whole path
