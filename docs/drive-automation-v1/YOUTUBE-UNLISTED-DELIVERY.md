# YouTube Unlisted delivery contract

**Version:** 1.0 — 20 November 2026.
**Status:** Proposed API integration; current authorization and capability testing pending.
**Parent:** [Complete implementation plan](IMPLEMENTATION-PLAN.md).

## 1. Target and authorization

Seed the target from existing [Goldsboro upload records (historical evidence excluded)](../PROVENANCE.md#excluded-evidence): the approved target channel, channel ID `<configured-channel-id>`. Read the authorized account/channel through the API during setup and before admitting uploads. A matching browser session or historical receipt is not proof that the Spark API identity controls this channel now.

Use user-authorized OAuth for the intended channel with protected offline credentials. Drive and YouTube can have separate grants and accounts. Do not use a service account as a substitute for an ordinary channel owner's YouTube OAuth consent. Resolve Brand Account/delegated-access details through a real safe account check.

Select permissions for all intended actions. Caption insertion specifically requires a suitable scope such as `youtube.force-ssl`; `youtube.upload` alone is not sufficient for that endpoint. [Caption authorization reference](https://developers.google.com/youtube/data/reference/rest/v3/captions/insert).

Account consent and applicable application verification are initial setup activities. Renew access if the provider revokes it. Keep upload credentials in the adapter's protected context rather than exposing them to incoming files or model prompts.

## 2. Hard delivery settings

The fixed adapter constructs the request from trusted policy and accepted metadata. Package text cannot change the allowed operation.

| Property | Required setting or rule |
| --- | --- |
| Channel | Exact configured channel ID, verified through the authorized identity |
| `status.privacyStatus` | Explicit `unlisted` on automated delivery |
| `status.publishAt` | Absent; public scheduling is not allowed |
| `status.containsSyntheticMedia` | `true` for this AI-assisted documentary format |
| `paidProductPlacementDetails.hasPaidProductPlacement` | Explicit `false` when the accepted episode has no paid promotion; hold contradictory submissions |
| Audience classification | Reviewed setting appropriate to the episode; retain the established adult/general documentary classification where applicable |
| Title/description/tags/language/category | Accepted values validated against current API constraints |
| Subscriber notification | Explicitly disabled for the automated review upload |

The current insert reference warns that omitted visibility can default to Public. Validate the constructed request before any HTTP write. [Video upload API](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert).

Google's revision history records removal of the old unverified-project private-only upload restriction on 2 November 2026. It also records that a no-paid-placement declaration now requires an explicit false value. These do not remove OAuth, quota, channel or other policy requirements. [Current revision history](https://developers.google.com/youtube/data/revision_history).

The API token is not provider-enforced Unlisted-only permission. The adapter, credentials boundary, allowed operations and tests enforce this narrower behaviour. Do not describe an application guard as a Google permission restriction.

## 3. Upload admission

Require `LOCAL_ACCEPTED` with the exact package, canonical, master, thumbnail and caption identities. Recompute delivery-artifact hashes before opening the upload. Check source withdrawal/supersession, channel identity, policy version, quota and existing episode/video receipts.

The metadata derives from the reviewed publishing package and actual film. Use measured chapter times. Preserve truthful AI/reconstruction/source disclosures and required credits. Do not invent links, licenses, rights clearance, quotes, dates, or claims of being an official archive.

Include confirmed previous-video URLs from the owner's delivery ledger after verification. The new video's description may link previous films. Reciprocal edits to earlier videos require an explicit approved metadata policy; version 1 does not automatically rewrite the back catalogue or override the owner's edits.

## 4. Resumable upload and duplicate prevention

Persist a planned upload operation before creating a session. Bind it to episode/version, accepted master hash, metadata digest and channel. Persist the returned resumable session reference immediately in protected state. Save acknowledged byte progress, then query the provider when recovering a transfer. [Official resumable upload protocol](https://developers.google.com/youtube/data/guides/using_resumable_upload_protocol).

Persist the video ID as soon as known, before caption, thumbnail, archive or report work. Those later failures must never cause another `videos.insert` call.

On a lost final response or expired session, query the saved operation/provider state and reconcile any candidate existing video against authoritative records. Matching a title alone is insufficient. If success cannot be determined, hold the upload as ambiguous. Do not promise provider-level exact-once creation or blindly upload another copy.

Treat invalid metadata and authorization errors as actionable states. Back off for transient failures, respect channel/project upload quotas, and retain the existing operation. Do not rotate accounts or projects to bypass limits.

## 5. Thumbnail, captions and branding

Attach the accepted branded thumbnail using `thumbnails.set`; record its digest and returned URLs/metadata, and retrieve enough evidence to confirm the intended image is attached. Keep a high-resolution local master plus a qualified upload derivative conforming to the current endpoint and channel capabilities. [Thumbnail endpoint](https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set).

Upload the accepted timed caption file with an explicit language/name and non-draft status. Save the track ID and verify its status. On recovery, list/reconcile the expected track before inserting another. Do not rely on the deprecated auto-sync parameter to repair an untimed transcript. Correct existing tracks using a scoped, recorded operation when needed.

The logo embedded in the approved film/thumbnail is part of the existing media design. Do not modify the channel's global branding, banner or watermark as a side effect of uploading an episode.

## 6. Provider verification and completion

Read the owned video's resource and required attachment states after upload. Record:

- Correct video/channel identity and intended visibility.
- AI and paid-promotion declarations and audience classification where exposed.
- Accepted title, description, tags, language and measured chapter metadata.
- Successful processing, observable duration/format and failed/rejected states.
- Caption track identity/status and thumbnail attachment evidence.
- Accepted artifact hashes, upload and verification timestamps, and final watch URL.

Processing success is not proof of every playback resolution. During the pilot compare API evidence with Studio and actual playback for the required presentation. Document which rendition/readiness checks the ordinary API can establish. [Video resource fields](https://developers.google.com/youtube/data/reference/rest/v3/videos).

Write the local receipt first, then the sanitized Drive delivery report. Use `DELIVERY_PENDING` if required reporting or archive writes remain; retry them without reuploading the film. Mark `DELIVERED_UNLISTED` only after all configured delivery checks pass. Report unresolved items explicitly.

## 7. Copyright checks and owner publication

An ordinary Data API upload is not a full Studio copyright-check report. Content ID API access is restricted to eligible Content Manager accounts; do not claim the channel has it. [Content ID access requirements](https://developers.google.com/youtube/partner).

Version 1's report distinguishes local rights review, API processing, observable restrictions and Studio copyright status. If the latter was not retrieved through a qualified interface, record `not verified by automation`. The owner reviews Studio notices and the film before publishing. API acceptance, Unlisted status and AI disclosure do not guarantee absence of later claims or monetization eligibility.

Routine production does not wait for an owner publication decision. It can continue preparing other accepted episodes. Completed deliveries are left alone: if the owner later changes visibility or metadata, the automation must not undo that action. No public scheduling, automatic publishing, deletion, or replacement endpoint is part of this adapter's permitted surface.
