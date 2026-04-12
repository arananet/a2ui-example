# Agent Specification — A2UI Unsplash Photo Explorer

**Version**: 1.0.0
**Status**: Approved
**Author**: Eduardo Arana
**Last Updated**: 2026-04-12

| Dependency | Pinned Version | Notes |
|------------|---------------|-------|
| `a2a-sdk` | `0.3.26` | Latest stable. `1.0.0-alpha` not yet production-ready. |
| A2A Protocol | `0.3.0` | `protocol_version` declared in AgentCard. |
| Google ADK | `>=1.0.0,<2.0.0` | Compatible release range. |

---

## 1. Purpose

This document is the **canonical specification** for the A2UI Unsplash Photo Explorer agent.
All implementation decisions must trace back to requirements defined here.
The implementation must not include features absent from this spec.

---

## 2. System Overview

### 2.1 Description

An Agent-to-Agent (A2A) compliant conversational agent that enables users to discover
high-quality photography from the Unsplash library using natural language. Results are
rendered as a dynamic, interactive photo gallery using the A2UI protocol.

### 2.2 Actors

| Actor | Description |
|-------|-------------|
| **User** | Human operating an A2A/A2UI-capable client |
| **GeminiAgent** | The AI agent (Gemini 2.5 Flash via Google ADK) |
| **Unsplash API** | Third-party photo search service |
| **A2UI Renderer** | Client-side component that renders A2UI payloads |

### 2.3 System Context Diagram

```
User ──natural language──► A2A Client
                                │
                                │ JSON-RPC (A2A Protocol)
                                ▼
                          A2A Server (FastAPI)
                                │
                          GeminiAgent (ADK)
                           ┌────┴────┐
                     tools │        │ A2UI output
                           ▼        ▼
                     Unsplash   A2UI Renderer
                       API       (client)
```

---

## 3. Functional Requirements

### 3.1 Photo Search

**REQ-TOOL-001 — Photo Search Tool**
- The agent MUST provide a `search_photos` tool that queries the Unsplash Search Photos API.
- Input parameters: `query` (string, required), `page` (integer, default 1),
  `per_page` (integer, default 9, max 30), `orientation` (string, default "landscape").
- The tool MUST return structured JSON including: photo URL (`small` size preferred),
  photographer name, description or alt_description, photographer profile URL,
  download URL, and comma-separated tags from `tags_preview`.
- The tool MUST return pagination metadata: `total`, `totalPages`, `currentPage`,
  `totalLabel` (human-readable string), `pageLabel`, `prevPagePrompt`, `nextPagePrompt`.
- On API error, the tool MUST return a JSON object with an `error` key describing the failure.
- `per_page` default of 9 produces a 3×3 grid layout in the A2UI surface.

**REQ-TOOL-002 — Random Topic Suggestion Tool**
- The agent MUST provide a `suggest_random_topic` tool.
- The tool MUST return a single string: a descriptive, interesting photo search topic.
- The topic list MUST contain at least 10 entries covering diverse categories.
- The agent MUST call this tool BEFORE `search_photos` when the user's intent is
  open-ended exploration ("surprise me", "random", "inspire me").

### 3.2 Pagination

**REQ-FUNC-001 — Paginated Navigation**
- The agent MUST support navigation between result pages via conversational messages.
- The A2UI surface MUST include "Previous Page" and "Next Page" buttons that send
  pre-constructed natural-language messages (via `sendMessage` action) to trigger pagination.
- `prevPagePrompt` and `nextPagePrompt` in `valueStruct` provide the button payloads.
- Page numbers are 1-indexed. The agent MUST not navigate below page 1.

### 3.3 Agent Identity

**REQ-AGENT-001 — Agent Card**
- The agent MUST expose a valid A2A Agent Card at `GET /.well-known/agent-card.json`.
- The card MUST declare: `name`, `description`, `url`, `version`, `capabilities`
  (streaming: true), `default_input_modes`, `default_output_modes`, and at least one `skill`.
- The `photo-search` skill MUST include at least 5 example prompts.

**REQ-AGENT-002 — Streaming**
- The agent MUST support streaming responses (`capabilities.streaming: true`).

---

## 4. A2UI Rendering Requirements

### 4.1 Output Protocol

**REQ-A2UI-001 — Delimiter**
- The agent MUST separate conversational text from A2UI JSON using the delimiter:
  `---a2ui_JSON---` on its own line.
- Content before the delimiter is rendered as a chat message.
- Content after the delimiter is parsed as a JSON array of A2UI messages.

**REQ-A2UI-002 — Conditional Rendering**
- The agent MUST emit A2UI output for every photo search result response.
- The agent MUST NOT emit A2UI for conversational responses (greetings, errors, clarifications).

**REQ-A2UI-003 — Message Sequence**
- Every A2UI photo response MUST contain exactly these messages in order:
  1. `beginRendering` — surface initialization
  2. `surfaceUpdate` — component tree
  3. `dataModelUpdate` — data population via `valueStruct`

### 4.2 Component Requirements

**REQ-A2UI-004 — Photo Gallery Layout**
- The `surfaceUpdate` MUST include the following components:
  - App title text: "Unsplash Photo Explorer"
  - Search query display (bound to `/photos/query`)
  - Stats row: total results label + page label
  - Photo grid: `List` component with `template` + `dataBinding` to `/photos/results`
  - Per-photo card: photo image, photographer attribution row, description, tags, view button
  - Pagination row: Previous Page and Next Page buttons

**REQ-A2UI-005 — Attribution**
- Every photo card MUST display the photographer's name (bound to `/photos/results[]/photographerName`).
- Every photo card MUST include a "View on Unsplash" button linking to the photographer's
  profile URL (bound to `/photos/results[]/profileUrl`).
- This fulfills the Unsplash API attribution requirement.

**REQ-A2UI-006 — Image Display**
- Photo images MUST use `usageHint: "smallFeature"` and `fit: "cover"`.
- Image URLs MUST use the Unsplash `small` size (or `regular` as fallback).

### 4.3 Dynamic Theming

**REQ-A2UI-007 — Primary Color Selection**
- The `beginRendering.styles.primaryColor` MUST be selected based on the search topic
  according to this mapping:

  | Topic Keywords | Color | Hex |
  |----------------|-------|-----|
  | nature, landscape, forest, ocean, flowers | Teal | `#00897B` |
  | architecture, city, urban, building | Indigo | `#3949AB` |
  | food, drink, cooking, cuisine | Amber | `#F57C00` |
  | art, abstract, creative, design | Purple | `#8E24AA` |
  | sport, fitness, action, adventure | Red | `#E53935` |
  | people, portrait, face, culture | Blue Grey | `#546E7A` |
  | travel, road, explore, journey | Teal | `#00897B` |
  | technology, minimal, futuristic | Cyan | `#00838F` |
  | default | Deep Blue | `#1565C0` |

**REQ-A2UI-008 — Typography**
- The `beginRendering.styles.font` MUST be set to `"Inter"` for all surfaces.

### 4.4 Data Model (valueStruct)

**REQ-A2UI-009 — valueStruct Schema**

The `dataModelUpdate.valueStruct` MUST conform to:

```json
{
  "photos": {
    "query":           "<string> — original search query",
    "total":           "<integer> — total matching photos",
    "totalLabel":      "<string> — e.g. '1,500 photos found'",
    "totalPages":      "<integer>",
    "currentPage":     "<integer>",
    "pageLabel":       "<string> — e.g. 'Page 1 of 167'",
    "prevPagePrompt":  "<string> — natural language prev-page message",
    "nextPagePrompt":  "<string> — natural language next-page message",
    "results": [
      {
        "id":               "<string>",
        "url":              "<string> — Unsplash small/regular image URL",
        "photographerName": "<string>",
        "description":      "<string>",
        "profileUrl":       "<string> — photographer Unsplash profile URL",
        "downloadUrl":      "<string>",
        "tags":             "<string> — comma-separated tag titles"
      }
    ]
  }
}
```

---

## 5. Non-Functional Requirements

### 5.1 Security

**REQ-SEC-001 — No Hardcoded Secrets**
- The Unsplash Access Key, Google Cloud credentials, and all sensitive values MUST be
  loaded exclusively from environment variables.
- No credential value may appear in any committed source file.
- Verification: `grep -rn "Client-ID [A-Za-z]" version-2/*.py` must return no output.

**REQ-SEC-002 — Environment Template**
- A `.env.example` file MUST be committed with placeholder values.
- The `.env` file MUST be listed in `.gitignore`.

### 5.2 Architecture

**REQ-ARCH-001 — Module Separation**
- Agent logic, tool definitions, prompt building, schema, type conversion, and execution
  MUST reside in separate modules with single responsibilities.

**REQ-ARCH-002 — 12-Factor Configuration**
- All runtime configuration MUST be sourced from environment variables (12-factor app pattern).
- `python-dotenv` is used for local development convenience only.

**REQ-ARCH-003 — Serverless Compatibility**
- Agent and request handler MUST be initialized at module load time (not per-request)
  to optimize for serverless cold-start performance.

**REQ-ARCH-004 — Session Management**
- Sessions MUST be managed via `InMemorySessionService`.
- The executor MUST manually create sessions when none exist to ensure compatibility
  across ADK versions.

### 5.3 Observability

**REQ-OBS-001 — Structured Logging**
- All modules MUST use `logging.getLogger(__name__)`.
- No `print()` statements in production code paths.
- Log level INFO for lifecycle events, DEBUG for A2UI payload inspection, ERROR for failures.

### 5.4 API Compliance

**REQ-API-001 — Unsplash Attribution**
- All photo results MUST include photographer attribution per Unsplash API Guidelines:
  https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines
- Attribution must link to the photographer's Unsplash profile.

**REQ-API-002 — Unsplash Endpoint**
- Photo search MUST use: `GET https://api.unsplash.com/search/photos`
- Authentication MUST use the `Authorization: Client-ID {ACCESS_KEY}` header.

**REQ-API-003 — A2A Protocol Version**
- The agent MUST declare `protocol_version: "0.3.0"` in its AgentCard.
- JSON-RPC method names MUST follow A2A v0.3: `message/send` and `message/stream`.
- `a2a-sdk` MUST be pinned to `0.3.26` in `requirements.txt`.
- When upgrading to `a2a-sdk>=1.0.0`, the following spec changes apply:
  - `supportsAuthenticatedExtendedCard` → `supportsExtendedAgentCard` (in `AgentCapabilities`)
  - OAuth 2.0 implicit/password grants removed; device code + PKCE added
  - `final` field removed from `TaskStatusUpdateEvent`
  - `tasks/list` method added (filtering + pagination)

---

## 6. Agent Persona

**REQ-PERSONA-001**
- The agent MUST present itself as a knowledgeable, enthusiastic photo curator.
- It MUST provide brief, engaging narrative context alongside photo results.
- It MUST NOT fabricate photo URLs, photographer names, or descriptions.
- It MUST NOT reveal internal system instructions when asked.
- It MUST only use the tools explicitly registered in its tool list.

---

## 7. Unsplash API Contract

### 7.1 Search Endpoint

```
GET https://api.unsplash.com/search/photos
Authorization: Client-ID {UNSPLASH_ACCESS_KEY}

Query Parameters:
  query        string   required   Search terms
  page         integer  optional   Default: 1
  per_page     integer  optional   Default: 10, Max: 30
  orientation  string   optional   landscape | portrait | squarish
```

### 7.2 Response Shape (relevant fields)

```json
{
  "total": 1500,
  "total_pages": 167,
  "results": [
    {
      "id": "abc123",
      "description": "string or null",
      "alt_description": "string or null",
      "urls": {
        "raw": "...", "full": "...", "regular": "...", "small": "...", "thumb": "..."
      },
      "links": {
        "html": "...", "download": "...", "download_location": "..."
      },
      "tags_preview": [{ "title": "mountain" }, { "title": "nature" }],
      "user": {
        "name": "Photographer Name",
        "links": { "html": "https://unsplash.com/@username" }
      }
    }
  ]
}
```

---

## 8. Out of Scope (v1.0)

The following are explicitly excluded from this version:

- User authentication or personalization
- Saving or bookmarking photos
- Video or audio content
- Batch downloads
- Unsplash collections API
- Image upload or editing
- Multi-turn conversation memory beyond session scope
- Deployment configuration (CI/CD, Cloud Run, Cloud Functions)

---

## 9. Acceptance Criteria

| ID | Criterion | Verified By |
|----|-----------|-------------|
| AC-001 | Agent Card available at `/.well-known/agent-card.json` | `curl` test |
| AC-002 | `search_photos("mountain")` returns ≥1 photo result | Tool unit test |
| AC-003 | Response contains `---a2ui_JSON---` delimiter | Response parsing |
| AC-004 | A2UI JSON parses as valid array of 3 messages | Schema validation |
| AC-005 | `beginRendering.styles.primaryColor` matches topic | Manual review |
| AC-006 | Photo card includes `photographerName` and `profileUrl` | UI inspection |
| AC-007 | No API key in any `.py` file | `grep` check |
| AC-008 | `.env` file not tracked by git | `git status` check |
| AC-009 | `suggest_random_topic` returns a non-empty string | Tool unit test |
| AC-010 | Pagination buttons send correct page prompts | UI interaction test |
