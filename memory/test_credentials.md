# Test Credentials
# Agent writes here when creating/modifying auth credentials (admin accounts, test users).
# Testing agent reads this before auth tests. Fork/continuation agents read on startup.

- Demo operator email: `operator@orbis.local`
- Demo operator passphrase: `ORBIS-DEMO-2026`
- Registration is local prototype auth; newly registered users receive an HTTP-only session cookie and their actual name appears in the profile/settings UI.
- Upgrade: operator accounts now persist in MongoDB with individual random salts and PBKDF2 hashes. Demo credentials are unchanged. Existing signed cookies remain valid. No external authentication is used.
- Workstation browser-verification account (created through registration in the upgrade verification): name `SIH Verification Operator`, email `sih-verification-2026@orbis.local`, password `ORBIS-VERIFY-2026`.
