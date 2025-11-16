# API v1

Minimal API surface for local network clients (e.g., iOS) to interact with the vocabulary storage and review scheduler. All endpoints return JSON.

Base URL when running locally: `http://<host>:5000/api/v1`

## Authentication

None. Intended for trusted local network usage.

## Endpoints

### GET `/lookup`
Check translation suggestions for a word.

**Query params**
- `word` (string, required)

**Responses**
- `200 OK` with `{ "word": "hi", "translations": ["嗨"], "examples": [] }`
- `400 Bad Request` when `word` is empty or has invalid characters: `{ "error": "invalid", "message": "word format is invalid" }`
- `404 Not Found` when no translation is available: `{ "error": "not_found", "message": "no translation found" }`

### GET `/vocab`
List stored vocabulary entries.

**Responses**
- `200 OK` with `{ "entries": [...], "due_count": 3, "total_count": 12 }`

Entries include: `id`, `word`, `definition`, `context`, `created_at`, `next_review`, `interval_days`, `success_streak`, `review_count`.

### POST `/vocab`
Add a vocabulary entry.

**Body (JSON)**
- `word` (string, required)
- `definition` (string, required)
- `context` (string, optional)

**Responses**
- `201 Created` with `{ "entry": { ... }, "due_count": <int>, "total_count": <int> }`
- `400 Bad Request` when fields are missing or invalid, e.g. `{ "error": "missing_fields", "message": "word and definition are required" }`

### DELETE `/vocab/<entry_id>`
Remove an entry by ID.

**Responses**
- `200 OK` with `{ "deleted": "<entry_id>", "due_count": <int>, "total_count": <int> }`
- `404 Not Found` when the entry is missing: `{ "error": "not_found", "message": "entry does not exist" }`

### GET `/review`
Return review queue metadata and the next due item, if any.

**Responses**
- `200 OK` with `{ "next": { ... } | null, "due_entries": [ ... ], "due_count": <int>, "total_count": <int> }`

### POST `/review/<entry_id>`
Record the result of a review.

**Body (JSON)**
- `result` (`"remembered"` | `"forgot"`, required)
- `mode` (`"word-first"` | `"definition-first"`, optional, default `"word-first"`)
- `answer` (string, optional; when `mode=definition-first` this is compared with the stored `word`)

**Responses**
- `200 OK` with `{ "entry": { ...updated fields... }, "due_count": <int>, "total_count": <int> }`
- `400 Bad Request` for invalid mode or result values.
- `404 Not Found` when the entry ID does not exist.

## Error format

Errors follow `{ "error": <code>, "message": <human-readable> }` and use HTTP status codes appropriate to the failure (400 for validation, 404 for missing resources).
