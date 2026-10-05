# docs/

The seed of your documentation, which is served at `docs.<zone>` from
a bucket of its own. How you write and build it is yours to choose:

- **Raw HTML:** sync this folder as it stands. `index.html` is the
  seed page.
- **Markdown, built by your CI or by hand:** pandoc, MkDocs, Hugo,
  md-preview, or anything else that writes a folder of static files.
  Sync that output folder instead of this one.

The box gives you one thing for it: your project's UI maintainer may
write to the `docs` bucket, as to `www`. A release is a sync of
whichever folder holds the built pages, for example:

    aws s3 sync <your built folder>/ "s3://docs.<zone>/" --delete --profile <your UI maintainer's profile>

The box's own expectations are few:
- **the pages are static files;**
- **the index is `index.html`;**
- **the pages are public, with no sign-in.** Nothing secret belongs
  here.

The project's probes check that `docs.<zone>/index.html` answers
`200`. Leave this README out of the release, or keep it; it is
harmless either way.
