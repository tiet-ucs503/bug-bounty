---
abstract: |
  The project's conduct in git: git-flow's branches by
  its tool, one change a commit, messages that say why,
  nothing secret staged. And the e-mail address in your
  commits, which is your choice: the forge's no-reply
  address is advised, to keep yours private, never
  required. Commits signed by a key the forge has
  verified, whichever address you use.
date: 2026-10-07
keywords:
- conduct
- git
- git-flow
- identity
- workflow
kind: how-to
sources:
- .github/workflows/ci.yml
status: draft
subtitle: Branches, commits, and who wrote them
title: Git and git-flow
version: v0.1.0
---

## 1 Before You Start

- `git` 2.34 or later, for commits signed by SSH keys
- The [git-flow
  tool](https://github.com/petervanderdoes/gitflow-avh),
  or [git-flow-next](https://git-flow.sh/); on Arch and
  Debian, `gitflow-avh` or `git-flow`
- An account on the forge, GitHub or GitLab, and an SSH
  key, `~/.ssh/id_ed25519`

## 2 The Branches

  ----------------------------------------------------------------------
  Branch                      Holds          Made by
  --------------------------- -------------- ---------------------------
  `master`                    What is        `git flow release finish`
                              released, each 
                              release tagged 
                              `vX.Y.Z`       

  `develop`                   The next       `git flow init`, once
                              release        

  `feature/<issue>- <slug>`   One feature,   `git flow feature start`
                              its turns      

  `release/vX.Y.Z`            A release      `git flow release start`
                              being made     
                              ready          

  `hotfix/vX.Y.Z`             A fix to what  `git flow hotfix start`
                              is released    
  ----------------------------------------------------------------------

- **By the tool, never by hand.**
  `git flow feature start`, not `git checkout -b`: the
  tool names the branch, starts it from the right
  place, and merges it back to both places a release or
  a hotfix must reach
- **Nobody commits to `master` or `develop` directly.**
  Every change arrives by a merge. Protect both
  branches on the forge
- **Never rewrite what is pushed.** A pushed commit is
  someone else's history too. The one exception is a
  scrub of something that should never have been
  committed, agreed by everyone first (§6)

## 3 The Commits

- **One change a commit,** that passes `make check` on
  its own. A commit that mixes a fix with a tidy hides
  the fix

- **The message says why.** The diff says what. A
  subject of one line, up to 72 characters, then a
  blank line and the reason:

  ``` text
  Refuse a revoke of the last users.grant

  Without it the project can lock itself out: nobody
  left may grant, and only the database's owner can
  repair it. T2.12.
  ```

- **Name the test or the issue** the commit answers,
  `T2.8`, `#12`, so the history leads back to the
  concept

- **Nothing generated,** nothing secret: no `.env`, no
  key, no `node_modules`, no `dev/out/`. Scan what is
  staged before every commit, [the conduct](README.md)
  §4.2

## 4 Your Identity, and Your Address

Every commit carries an author's name and e-mail
address, and the forge publishes both, to anyone who
clones the repository, for good.

> [!NOTE]
> **Which address you commit with is yours to choose.**
> The project requires none in particular: any address
> your forge account has verified links your commits to
> your profile. A no-reply address is optional. It is
> advised, and preferred, only because it keeps your
> own address out of public history.

Each forge gives you a no-reply address, tied to your
account, so your commits still link to your profile
without your own address in them. If you are content
for your address to be public, use it, and skip §4.1.

### 4.1 If You Choose a No-reply Address

- **GitHub:** Settings, Emails, under "Keep my email
  addresses private". It is
  `ID+USERNAME@users.noreply.github.com`, `ID` a
  number. Tick that box; and, if you want the forge to
  guard you, "Block command line pushes that expose my
  email", which refuses a push whose latest commit
  carries your private address
- **GitLab:** Preferences, Profile, "Commit email",
  "Use a private email". It is
  `ID-USERNAME@users.noreply.gitlab.com`

Read 2026-10-07: GitHub's [e-mail
addresses](https://docs.github.com/en/account-and-profile/concepts/email-addresses)
and [blocking
pushes](https://docs.github.com/en/github/setting-up-and-managing-your-github-user-account/managing-email-preferences/blocking-command-line-pushes-that-expose-your-personal-email-address);
GitLab's [signed
commits](https://docs.gitlab.com/user/project/repository/signed_commits/).

### 4.2 Set It for This Repository

The address you chose, no-reply or your own, in the
repository, not globally, so another forge's repository
keeps its own. Expect no output:

``` sh
NAME='Your Name'
EMAIL='12345678+your-username@users.noreply.github.com'
git config --local user.name "${NAME}"
git config --local user.email "${EMAIL}"
```

For every repository under one folder at once, in
`~/.gitconfig`:

``` ini
[includeIf "gitdir:~/src/github/"]
  path = ~/.gitconfig-github
```

with `user.email` in `~/.gitconfig-github`.

### 4.3 Sign Your Commits

An address proves nothing, whichever you use: anyone
can type any address into a commit. A signature does.
Signing is advised too; sign with the SSH key you
already have:

``` sh
git config --local gpg.format ssh
git config --local user.signingkey "${HOME}/.ssh/id_ed25519.pub"
git config --local commit.gpgsign true
git config --local tag.gpgsign true
```

So that git can check signatures itself, tell it which
key is whose. Expect no output:

``` sh
mkdir -p "${HOME}/.config/git"
printf '%s %s\n' "${EMAIL}" "$(cat "${HOME}/.ssh/id_ed25519.pub")" >> "${HOME}/.config/git/allowed_signers"
git config --global gpg.ssh.allowedSignersFile "${HOME}/.config/git/allowed_signers"
```

Then add the same public key to the forge **as a
signing key**: GitHub, Settings, SSH and GPG keys, "New
SSH key", type "Signing Key"; GitLab, Preferences, SSH
Keys, usage "Signing" or "Authentication & Signing".

The forge marks a commit **Verified** when the key is
one of yours and the commit's address is one your
account has verified. Push one commit and look for the
mark before relying on it.

### 4.4 Check Before a Push

Expect only the address you chose, twice on each line,
author and committer, and `G`, a good signature:

``` sh
git log --format='%ae %ce %G?' develop | sort | uniq -c
```

`N` is unsigned, or `gpg.ssh.allowedSignersFile` is not
set; any other address means a commit made before §4.2.

## 5 What Can Go Wrong

- **The forge shows a commit as someone else's, or as
  nobody's.** Its address is not one your account
  knows. §4.1 again, and check `git config user.email`
  in that repository
- **`Unverified`.** The key is added for authentication
  only, or the commit's address is not verified on the
  account
- **A push refused for exposing your e-mail,** if you
  ticked GitHub's box. The latest commit carries your
  private address. Amend it, if it is not yet pushed
  anywhere:
  `git commit --amend --reset-author --no-edit`

## 6 Commits Already Made

> [!CAUTION]
> A rewrite changes every commit's hash from the first
> it touches. Everyone with a clone must clone afresh,
> and a pushed history rewritten is a force-push. Do it
> before the first push, or agree it with everyone
> first.

If you change address after committing, say to a
no-reply one before a repository's first push, the
commits' old address can be replaced with
[git-filter-repo](https://github.com/newren/git-filter-repo)
and a mailmap, `NEW-NAME <NEW-ADDRESS> <OLD-ADDRESS>` a
line. In a fresh clone, never the original:

``` sh
printf '%s\n' 'Your Name <12345678+your-username@users.noreply.github.com> <you@old.example>' > ../mailmap
git filter-repo --mailmap ../mailmap
git log --format='%ae' --all | sort -u
```

Expect only the new address. Signatures do not survive
the rewrite; old commits stay unsigned.

## 7 See Also

- [From an issue to a merge](workflow.md): the branches
  in use
- [How these pages are written](README.md) §5.2: what
  never goes into a commit
