# SENTRA — Security & Privacy

## Threats
- unauthorized access
- credential leakage
- prompt injection
- malicious uploads
- PII logging
- model hallucination
- incorrect high-impact interpretation
- insecure storage
- excessive retention

## Authentication & Authorization
Design for roles such as operator, reviewer, administrator and auditor. Authorization must be enforced server-side where a backend exists.

## Input Security
Validate MIME type, extension, size, duration, text length and schemas.

## Prompt Injection
Complaint text is untrusted. It must not modify instructions, call tools, execute code, bypass validation or override safety rules.

## Logging
Never log raw complaints, raw audio, API keys, passwords or unnecessary PII.

## Storage
Store only required structured information. Use opaque case identifiers. Keep audio separate when persistent storage is necessary.

## Retention
Implement configurable retention/deletion rather than unlimited storage.

## Secrets
Use environment variables. Commit only `.env.example`.

## Failure Safety
AI failure must never become a reassuring classification. Mark unavailable modalities and route to human review when needed.

## Privacy by Design
Collect minimum necessary data and use synthetic/non-sensitive data during development.
