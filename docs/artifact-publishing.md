# OMP artifact publishing: working agreement

Status: design in progress. This records the Owner's answers from 2026-09-26.
It is not an approved implementation contract or evidence that Hermesbox is
deployed. The existing pilot publisher remains separate until this design is
settled.

## Goal

Publish review artifacts from either the Owner's Mac or Hermesbox through one
CLI. An OMP agent may use that CLI when the Owner asks or when a workflow gate
requires an update. The Owner wants a growing collection without a fixed
artifact count or automatic expiry, and can remove an individual artifact when
it should no longer be served.

## Decisions already made

- Both the Owner and OMP agents may publish and delete. No distinct roles or
  elaborate permission model is requested. Anyone able to use the authorized
  CLI can delete.
- Publishing is deliberate, not scheduled or automatic. A direct Owner request
  or an explicit workflow gate can prompt an agent to publish.
- The CLI must work from the Mac and from Hermesbox.
- Artifacts may be static sites, individual files, or directories. HTML, CSS,
  JavaScript, images and other static assets must work. Client-side application
  deep links need an `index.html` fallback. JavaScript may call external APIs
  and CDNs.
- Artifact JavaScript must be isolated from the catalog and other artifacts.
- Source-directory symlinks may point within that directory; escaping links
  must be rejected. Expected artifact sizes range from megabytes to hundreds
  of megabytes.
- HTTPS is preferred. Today all tailnet devices belong to the Owner, so a
  tailnet-only audience is acceptable. Cloudflare is an open hosting option.
- A readable URL slug is acceptable, subject to the hosting choice. Hash-based
  deduplication is not required for the first working version.
- Keep only the latest published content for a logical artifact. Publishing is
  immediate, with no draft state or retained public version history.
- Metadata should be minimal. There is no requirement to record Git revision,
  OMP candidate, creator, or detailed provenance.
- Do not add a mandatory link/asset checker. The publishing agent can review
  and repair its own mistakes.
- Cleanup is manual per artifact. Removal should stop serving it and return
  ordinary HTTP 404. No recovery window, backup policy, automatic retention,
  artifact-count limit, disk warning, or quota is requested for now.
- The content may be of any kind, including sensitive material. Access policy
  is a hosting decision; the publisher does not classify artifact contents.

## High-level shape under consideration

The CLI submits a file or directory as one artifact. A directory is snapshotted
as a tree, preserving relative paths. Internal symlinks are resolved into that
snapshot; links that escape the chosen root fail. For a site, `index.html` is
the entry point and sibling assets retain their paths. An individual file is
served or downloaded with its appropriate content type. A directory without
`index.html` needs a chosen presentation rule (see open questions).

The server stores each logical artifact separately, for example:

```text
artifact-store/
  incoming/<temporary-upload>/       not served
  artifacts/<artifact-id>/
    content/                          published file tree
    metadata.json                     minimal title/URL mapping
```

The example is a storage sketch, not an approved path or URL scheme. The CLI
can stage an upload and switch the logical artifact to new content only after
the upload completes. Deletion removes its served entry; whether to retain a
brief internal previous copy during a failed replacement remains open.

A catalog would be a small page listing artifact links. It would be separate
from each artifact's own page, so it would not wrap or modify a self-contained
site. An artifact site with absolute `/assets/...` paths may fail if mounted
under a shared URL prefix; a distinct hostname/origin per artifact avoids that
base-path problem and supports browser isolation, but needs DNS/TLS/routing
design. This is a proposal, not yet a decision.

## Hosting paths to evaluate

1. **Tailscale Serve:** stable HTTPS URL restricted to the tailnet, with no
   additional domain. Tailscale Serve can proxy a local web service and handles
   HTTPS for its tailnet hostname. A single device hostname does not by itself
   give every artifact a distinct browser origin. See
   [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).
2. **Cloudflare Tunnel plus Access:** use one of the Owner's domains for HTTPS,
   a stable hostname and login policy. A hostname or subdomain per artifact
   appears more compatible with strong isolation and root-relative site assets.
   The exact wildcard routing and access setup require a small proof before
   selection. See [Cloudflare Access self-hosted applications](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/).

Cloudflare Quick Tunnels can provide a random `trycloudflare.com` URL without a
domain, but Cloudflare calls them a development/testing feature rather than a
persistent publishing route. See [Quick Tunnels](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/).

## Draft acceptance outcomes, before implementation

These are proposed checks derived from the decisions above. They need review
after the open choices are resolved; no PASS or Owner approval is claimed.

1. From both authorized machines, publish a static directory containing HTML,
   JS, CSS, images and a nested route. Its entry page, assets, JS behavior and
   direct nested-route refresh work over the selected HTTPS URL.
2. Publish an individual binary file and a directory of files. Their content
   is retrievable byte-for-byte, with appropriate browser behavior once the
   directory presentation rule is chosen.
3. Publish two artifacts containing JavaScript. Code running in one artifact
   cannot read the other artifact or the catalog through same-origin browser
   access.
4. Republish one logical artifact. Its current URL serves the new content and
   does not expose the prior content; another artifact remains unchanged.
5. Delete one artifact through the CLI. Its URLs return 404, other artifacts
   remain available, and no time-based cleanup runs.
6. A symlink to content within the source root is included correctly; a
   symlink outside that root is rejected before publication.
7. A failed or incomplete upload does not expose a partial artifact. The
   behavior after a failed replacement still needs a decision.
8. Publication requires an explicit CLI invocation; merely creating files or
   finishing an OMP task does not publish them.

## Open questions

1. Does "anything" mean any **static bytes** (files, directories and browser
   apps), or must it also run backend servers/processes? The latter changes
   this from file publishing to application deployment.
2. For a directory without `index.html`, generate a file listing, serve it as
   a downloadable archive, or require a chosen entry file?
3. Is strong isolation required even for a direct artifact URL, or is a
   sandboxed catalog preview sufficient? Direct-URL isolation strongly favors
   separate origins.
4. Choose Tailscale-only hosting or a Cloudflare domain with Access. If using
   Cloudflare, which domain/subdomain and login identity should be used?
5. Should the homepage list all artifact links, or should discovery happen
   through `artifact list` in the CLI only?
6. What minimal metadata should be required: a name/slug alone, or also a
   display title? A local source path need not be published.
7. On a failed replacement, should the previous working artifact stay served
   until the new one is verified? This requires temporary staging, not public
   version history.
8. For names and deletion, should the CLI use a stable logical name such as
   `omp-pilot`, with `publish omp-pilot ./site` replacing it and
   `delete omp-pilot` removing it? A content hash can verify bytes without
   becoming the deletion key.
9. Should a rename be implemented as delete and republish, as the Owner
   suggested?
10. Should the existing OMP pilot page become the first artifact in the new
    system, or remain on its current route during migration?

## Current implementation and known gaps

`make artifact-publish` currently packages only the OMP pilot Markdown and
generated HTML. The external Hetzner playbook publishes one root document and
keeps five release directories. It is not the generic publisher described
here. The immediate release-ID and deployment verification fixes are local
changes; no live publication has been confirmed. Some links in the current
pilot HTML target files absent from this checkout, including the referenced
PR #48 UAT candidate files. A generic publisher should not silently invent
those files or claim that the links work.
