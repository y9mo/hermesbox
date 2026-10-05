# OMP artifact publishing: working agreement

Status: design in progress. This records the Owner's answers and use cases
from 2026-09-26.
It is not an approved implementation contract or evidence that Hermesbox is
deployed. The existing pilot publisher remains separate until this design is
settled.

## Goal

First publish and manage artifacts from Hermesbox through a local CLI.
The later Mac CLI should use the same artifact semantics. An OMP agent may use
the CLI when the Owner asks or when a workflow gate requires an update.
The Owner wants a growing collection without a fixed artifact count or
automatic expiry, and can remove an individual artifact when it should no
longer be served.

## Use cases

| Case | Owner's purpose | Initial delivery shape | Additional requirements to settle |
| --- | --- | --- | --- |
| 1. Review document | Read rendered HTML output, sometimes at length | Static HTML with its CSS, JS and assets | Readable persistent URL and comfortable long-form review; no running backend |
| 2. Mock UI experiment | Test and play with an interface using mock data | Static browser app when mocks run in the browser | A mock API or live development server would instead need the runtime path; decide whether hot reload is needed |
| 3. Full app experiment | Try a frontend and backend together, commonly with SQLite | Running app, with frontend and API reachable under one app origin | Process lifecycle, routing, health, logs, writable SQLite storage, replacement and teardown |
| 4. Personal/family app | Run a small, production-ready app for the Owner, friends and family | Durable running app | Audience and login, availability, restart, upgrades, data durability and recovery; low request volume does not remove these needs |

Cases 1 and a client-only form of case 2 fit file publishing. Cases 3 and 4
require application deployment: Hermesbox must start and supervise a backend,
route browser requests to it, and preserve any writable data separately from
the replaceable app build. SQLite avoids a separate database service, but its
files still need an ownership, migration, backup and deletion policy. The
earlier decision to skip backups applies to review artifacts; it does not yet
decide the policy for a personal/family application's data.

One CLI and catalog may present both types, but a static bundle and a running
service need distinct operations and acceptance checks. For a full app, a
single app hostname with frontend and `/api` routed to its backend is a
simple initial pattern; the app can then make same-origin requests. Each app
should remain isolated from the catalog and other apps. This is a design
proposal, not an approved runtime interface.

## Decisions already made

- Both the Owner and OMP agents may publish and delete. No distinct roles or
  elaborate permission model is requested. Anyone able to use the authorized
  CLI can delete.
- Publishing is deliberate, not scheduled or automatic. A direct Owner request
  or an explicit workflow gate can prompt an agent to publish.
- The end-state CLI should work from the Mac and Hermesbox; the first
  milestone is Hermesbox only.
- Artifacts may be static sites, individual files, or directories. HTML, CSS,
  JavaScript, images and other static assets must work. Client-side application
  deep links need an `index.html` fallback. JavaScript may call external APIs
  and CDNs.
- Artifact JavaScript must be isolated from the catalog and other artifacts.
- Source-directory symlinks may point within that directory; escaping links
  must be rejected. Expected artifact sizes range from megabytes to hundreds
  of megabytes.
- HTTPS is preferred. Today all tailnet devices belong to the Owner, so a
  tailnet-only audience is acceptable for private review artifacts. Access
  for friends and family in case 4 remains open.
- A readable URL slug is acceptable, subject to the hosting choice. Hash-based
  deduplication is not required for the first working version.
- Keep only the latest published content for a logical review artifact.
  Publishing is immediate, with no draft state or retained public version
  history. Running-app code and writable data need separate update rules.
- Metadata should be minimal. There is no requirement to record Git revision,
  OMP candidate, creator, or detailed provenance.
- Do not add a mandatory link/asset checker for review artifacts. The
  publishing agent can review and repair its own mistakes. Running apps still
  need an agreed health and restart check.
- Cleanup of review artifacts is manual. Removal should stop serving one
  and return ordinary HTTP 404. No recovery window, backup policy, automatic
  retention, artifact-count limit, disk warning, or quota is requested for
  those review artifacts. Running apps and their writable data need separate
  teardown decisions.
- The content may be of any kind, including sensitive material. Access policy
  is a hosting decision; the publisher does not classify artifact contents.

## High-level shape under consideration

For static publishing, the CLI submits a file or directory as one artifact.
A directory is snapshotted as a tree, preserving relative paths. Internal symlinks are resolved into that
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

The [Cloudflare Pages local-preview guide](https://developers.cloudflare.com/pages/how-to/preview-with-cloudflare-tunnel/) uses `cloudflared tunnel --url` to expose an already-running local server at a randomly generated `trycloudflare.com` URL. It is a Quick Tunnel with a public URL, not a Cloudflare Pages deployment
or an artifact store. The guide calls the tunnel long-running, but Cloudflare's more specific [Quick Tunnels documentation](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/) says this route is for testing/development, with no uptime SLA, a random URL, a 200-concurrent-request limit, and no SSE. It is suitable for a temporary Hermesbox proof, not the stable collection.

Cloudflare Pages Direct Upload is a different service: it stores and serves uploaded assets on Cloudflare instead of Hermesbox. It gives sites their own `pages.dev` hostnames, but [Pages limits](https://developers.cloudflare.com/pages/platform/limits/) include 25 MiB per file, up to 20,000 files per site on Free, and 100 projects per account. Those limits conflict with the desired hundreds-of-megabytes files and unbounded artifact count. Its [preview deployments](https://developers.cloudflare.com/pages/configuration/preview-deployments/) are public by default and retain hash-addressed older deployments, so they do not directly match the requested latest-only removal behavior.

For running apps, [Cloudflare Tunnel published applications](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/) can forward a stable public hostname to a service on Hermesbox; [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/) can restrict who reaches it. Alternatively, [Tailscale machine sharing](https://tailscale.com/kb/1084/sharing) can grant invited people access without making an app public, but those visitors need Tailscale. The choice for case 4 depends on the intended visitor experience and per-app access policy.

## Hermesbox-first sequence

1. Build the file/directory snapshot, naming, replacement and deletion semantics on Hermesbox, with a local CLI and a server bound to localhost. Keep artifact storage and the CLI independent of the eventual HTTPS ingress.
2. Prove one JavaScript site and one large file on Hermesbox. A Quick
   Tunnel may provide a temporary external smoke URL using harmless test
   content; do not make that random, public URL the artifact identity.
3. Choose a durable ingress before accepting the multi-artifact collection. Tailscale Serve supplies private HTTPS simply, but its one device hostname does not provide strong direct-URL origin isolation. A named Cloudflare Tunnel plus a domain, per-artifact hostnames and Access may satisfy isolation while keeping bytes on Hermesbox; DNS, wildcard routing and Access need a small real proof.
4. Add a supervised app runtime for case 3 only after the static path is
   exercised. Case 4 then adds explicit durable-data, access and availability
   checks before it can be called production-ready.
5. Add the Mac CLI after the Hermesbox workflow is validated. It should submit
   to the same operations rather than introduce a second storage model.

## Draft acceptance outcomes, before implementation

These are proposed checks derived from the decisions above. They need review
after the open choices are resolved; no PASS or Owner approval is claimed.

1. From Hermesbox first, publish a static directory containing HTML,
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
9. Deploy a full experimental app with a frontend, backend and SQLite file.
   Browser/API requests work under its app URL, a process restart preserves
   the database, and replacing code does not replace writable data.
10. Stop and remove an experimental app. Its routes cease serving, its process
    stops, and its data follows the separately agreed deletion rule. A second
    app remains running.
11. Before calling a family app production-ready, demonstrate the chosen
    audience/login rule, restart after host reboot, a safe update, and the
    agreed data recovery behavior. These are proposed cases, not PASS claims.

## Open questions

1. For a directory without `index.html`, generate a file listing, serve it as
   a downloadable archive, or require a chosen entry file?
2. Is strong isolation required even for a direct artifact URL, or is a
   sandboxed catalog preview sufficient? Direct-URL isolation strongly favors
   separate origins.
3. Choose Tailscale-only hosting or a named Cloudflare Tunnel with Access. If using
   Cloudflare, which domain/subdomain and login identity should be used?
4. Should the homepage list all artifact links, or should discovery happen
   through `artifact list` in the CLI only?
5. What minimal metadata should be required: a name/slug alone, or also a
   display title? A local source path need not be published.
6. On a failed replacement, should the previous working artifact stay served
   until the new one is verified? This requires temporary staging, not public
   version history.
7. For names and deletion, should the CLI use a stable logical name such as
   `omp-pilot`, with `publish omp-pilot ./site` replacing it and
   `delete omp-pilot` removing it? A content hash can verify bytes without
   becoming the deletion key.
8. Should a rename be implemented as delete and republish, as the Owner
   suggested?
9. Should the existing OMP pilot page become the first artifact in the new
    system, or remain on its current route during migration?

## New runtime questions

1. Is case 2 a published, self-contained mock build, or must the system keep
   a development server running with hot reload?
2. What form should case 3 accept: a container image/Dockerfile, a command
   plus working directory, or a repository with a build command? The first
   Hermesbox runtime needs one explicit contract, not automatic guessing.
3. Must a case 3 experiment restart after a Hermesbox reboot, or is it
   intentionally temporary? When replacing or deleting one, should its
   SQLite file be kept, exported, or erased?
4. For case 4, will friends/family install Tailscale, or should they use a
   normal HTTPS link with a browser login? Which people may access each app?
5. What data recovery expectation makes case 4 production-ready for you?
   The earlier no-backup decision concerned disposable review artifacts.
6. Is brief downtime during updates acceptable for case 4, or should the
   previous version remain available until a replacement is healthy?

## Current implementation and known gaps

`make artifact-publish` currently packages only the OMP pilot Markdown and
generated HTML. The external Hetzner playbook publishes one root document and
keeps five release directories. It is not the generic publisher described
here. The immediate release-ID and deployment verification fixes are local
changes; no live publication has been confirmed. Some links in the current
pilot HTML target files absent from this checkout, including the referenced
PR #48 UAT candidate files. A generic publisher should not silently invent
those files or claim that the links work.
