# Google Drive intake and developer submission contract

**Version:** 1.0 — 20 November 2026.
**Status:** Proposed contract to implement and qualify.
**Parent:** [Complete implementation plan](IMPLEMENTATION-PLAN.md).

## 1. Drive layout and access

```text
Documentary Production/
  Incoming/
    episode_008_example/
      v001/
        production_package.zip
        READY.json
  Source Archive/
  Delivery Reports/
  Finished Videos/
```

These are proposed labels. Provisioning records the actual folder IDs and account identities. IDs are authoritative; display names can change or be duplicated.

Give approved developers contributor access to Incoming. Keep archive, delivery receipts and finished masters under owner-controlled permissions. Give the runtime the account permissions needed for those areas. Do not expose public edit links, share the owner's login, or grant the runtime Drive administration unnecessarily. A dedicated runtime identity can limit visible files through sharing ACLs where the account arrangement supports it.

## 2. Whose storage is used

First establish whether the configured storage allowance belongs to Google One/personal My Drive or a Workspace organization. Record actual available space and test upload ownership.

| Situation | Required treatment |
| --- | --- |
| Supported Workspace Shared drive | Verify organization ownership, contributor permissions and organization storage usage |
| Personal folder shared with developer | Treat submissions as potentially developer-owned and charged to their allowance |
| Personal retention in owner's allowance | Use owner-authorized copies/uploads to Source Archive; verify ownership and bytes |

For a personal account, the default proposal is temporary developer-owned incoming files, followed by a verified archive copy created under the owner's authorization. That arrangement needs temporary developer capacity. Source and copied Drive IDs must map to the same episode/version/hash, so copying cannot trigger another episode. Remove neither original automatically. Ownership-transfer constraints must be checked before considering a transfer instead of a copy. [Google's storage rule](https://support.google.com/drive/answer/2424368).

Do not silently upgrade the subscription, create an organization, or assume service accounts have personal storage. If using service accounts in a Workspace branch, qualify their actual access and the destination storage model. [Drive error and storage guidance](https://developers.google.com/workspace/drive/api/guides/handle-errors).

## 3. Package requirements

Use an ordinary ZIP containing the episode folder and original files. Do not convert manifest, scripts, Markdown, or assets into native Google Docs. A ZIP gives a single byte identity and avoids a moving tree of partially synchronized assets.

Required contents:

- One declared manifest entry point.
- All locally referenced assets, acts and storyboard, or explicit declarations that an optional category is absent.
- The publishing package with title, description, tags and branding instructions.
- Provenance and rights information for supplied third-party media and music.
- The original supplied documents needed to interpret the story.

Remote research sources may be listed, but missing required assets cannot be hidden by a broad fallback. A declared asset must be obtainable and usable under the selected production contract.

## 4. READY.json

Upload this record only after the ZIP finishes uploading and can be read through the authorized API. The planned developer helper handles ZIP upload and record creation together; it should not require manually editing IDs or hashes for every episode.

Illustrative envelope; the IDs, size and digest below are placeholders, not a valid submission:

```json
{
  "schema_version": 1,
  "episode_id": "episode_008_example",
  "version": 1,
  "ready": true,
  "submitted_at": "2026-11-20T15:00:00+05:00",
  "package_file_id": "DRIVE_FILE_ID_FROM_COMPLETED_UPLOAD",
  "package_name": "production_package.zip",
  "package_size_bytes": 1000000,
  "package_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "manifest_path": "episode_008_example/manifest.json",
  "publishing_package_path": "episode_008_example/YOUTUBE_PUBLISHING_PACKAGE.md"
}
```

Contract rules:

- `schema_version` is exactly 1; reject unknown versions and unexpected executable/control fields.
- `episode_id` is a safe lowercase identifier of at most 64 characters, using letters, digits, underscore and hyphen; it is not a filesystem path.
- `version` is a positive integer; `ready` must be true.
- The timestamp is informational; it cannot override admission order, version identity, or trust.
- File ID, filename, actual parent folder and positive byte count must agree with the actual ZIP.
- SHA-256 is 64 lowercase hexadecimal characters and must match downloaded bytes.
- Entry-point paths are relative to the extracted ZIP root, with no absolute paths or parent traversal.
- The package cannot request a channel, OAuth scope, shell command, visibility override, deletion, or public publication through this envelope.

The checksum proves consistency with the submission, not the safety or truth of its content. Authorized folder membership and the configured submission policy establish admission; a self-declared sender string does not.

## 5. Discovery and races

1. List all pages of the configured Incoming tree and eligible version folders.
2. Select complete ready records; ignore temporary upload names and folders without readiness.
3. Reject ambiguous duplicate ready filenames, duplicated identities with different hashes, trashed files, and shortcuts leading outside the allowed area.
4. Confirm the referenced package is a direct member of the declared approved version folder, with download permission.
5. Save the ready bytes, file IDs, current metadata/version information, size and expected digest locally.
6. Download to a `.part` file; verify complete bytes and recheck source metadata before accepting.
7. If content changed, stop acquisition and require a new immutable version. Rename to the accepted local ZIP atomically only after verification.

A Drive file ID is stable identity, not proof that its content never changes. A modification timestamp or ETag must not be treated as the package's SHA-256.

Use startup folder scans as the correctness baseline. Save a Drive change cursor only after the corresponding changes have been recorded durably. After missing/invalid cursors, account changes, or suspected inconsistency, reconcile the allowed folders again. New packages arriving during a paginated scan must be caught by the next scan/change pass. [Drive change tracking](https://developers.google.com/workspace/drive/api/guides/manage-changes), [file search](https://developers.google.com/workspace/drive/api/guides/search-files).

## 6. Download and extraction

Use authenticated Drive downloads by file ID; do not scrape browser download pages. Persist a partial byte count and the identity to which it belongs. Range-resume only when the source identity still agrees; hash the complete final file after recovery. [Drive download API](https://developers.google.com/workspace/drive/api/guides/manage-downloads).

Before extraction, inspect the archive directory. Reject absolute paths, `..`, drive-letter and UNC paths, symlinks, hardlinks, device entries, path collisions and entries that escape the destination. Extract into a new quarantine directory outside executable workflow configuration. Never overwrite engine code or a completed project's originals.

Provisional admission limits for the pilot are 20 GiB compressed, 100 GiB expanded, 20,000 entries, and a 200:1 expansion ratio. These are proposed local limits, not Google limits; record and adjust them during qualification. Check required free space before download and extraction. An oversized package is held with a reason rather than unpacked without bounds.

Create a source manifest containing original paths, sizes and digests. Only a validated copy enters production. Bundled `AGENTS.md`, `.codex`, MCP configuration, scripts and binaries are preserved as data where necessary but never loaded or executed as workflow configuration.

## 7. Identity, versions and withdrawal

The delivery key is `(episode_id, version, package_sha256)` within the configured channel/policy context. Record the source Drive IDs as additional references.

| Input event | Behaviour |
| --- | --- |
| Same ID/version/hash again | Return the saved progress or receipt; do not create work twice |
| Same ID/version, different bytes | Hold as a conflict; require a new version |
| Different filename or archive copy, same delivery key | Recognize the existing work |
| New version before upload begins | Supersede the earlier pending version at a safe stage boundary, retaining its evidence |
| New version after a YouTube upload has started or completed | Hold for replacement policy; do not silently create, delete or replace a video |
| Ready record removed before admission | Do not start production |
| Submission withdrawn during production | Stop new external delivery at the next safe check; preserve local work |
| Source removed after delivery | Preserve the delivery receipt and archived originals; never infer permission to delete the YouTube video |

Freeze the selected package and canonical manifest before upload. Recheck pending supersession/withdrawal immediately before creating an external upload session.

## 8. Authorization and scope qualification

Use initial owner consent and protected refresh credentials on Spark. A chat-connected Drive plugin is a separate integration and is not sufficient for an unattended Linux process.

Prefer narrow per-file access where the actual upload and selection flow supports it. Do not assume selecting a parent folder under `drive.file` grants perpetual access to every file another user later uploads. Test listing and downloading newly created developer files. If a broader read scope is necessary, document that it is account-wide and enforce the production-folder allowlist in the adapter; do not describe that allowlist as an OAuth-enforced folder scope. Qualify separate permissions for owner archive copies and app-created receipts. [Drive OAuth scope definitions](https://developers.google.com/workspace/drive/api/guides/api-specific-auth).

## 9. Output records and capacity

Each delivery report records episode/version, input and master hashes, runtime, accepted review identities, upload status, video URL, measured timing, and remaining limitations. Write reports through a temporary file followed by a completed marker or atomic rename/update pattern. Reports must contain no access tokens, refresh credentials, upload-session secrets, or unrestricted agent logs.

Finished-video backup is a separate resumable Drive operation tied to the master hash. If required archival/report writes fail, retain `DELIVERY_PENDING` and retry those writes against the existing video. Never trigger another YouTube upload because Drive reporting failed.

Monitor actual remaining Drive and local capacity. A configured archive target failure must be visible. The selected storage plan does not imply unlimited transfer quota, indefinite version retention, a second independent backup, or enough local Spark disk for every file.
