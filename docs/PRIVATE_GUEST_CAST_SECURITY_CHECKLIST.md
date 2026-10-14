# Parent-approved guest cast security checklist

This checklist is a prerequisite for cross-child co-starring; it does not itself enable sharing.

- Default deny: a child token must never enumerate, search, or fetch another child's private characters or equipment.
- Only a parent-authenticated server endpoint can create or revoke a narrowly scoped guest-cast grant.
- Grants bind the owner child, recipient child, specific canonical hero ID, allowed director use, and expiration.
- Every guest read is authorized server-side against the grant and canonical ownership; never trust client-supplied owner IDs.
- Revocation and expiration are checked on every read and render job, including after queued work resumes.
- Sharing a hero for a scene does not grant access to the owner's library, voice recordings, unrelated outfits, or metadata.
- Parent review is required before private MP4 export; no real child content in public CI artifacts or logs.
- Automated tests must cover cross-owner denial, forged grants, expiry, revocation, replay, and concurrent sessions.

This document is a security gate, not a substitute for implementation or tests.
