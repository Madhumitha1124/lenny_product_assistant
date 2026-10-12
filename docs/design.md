Get-LocationCREATE ROLE lenny WITH LOGIN PASSWORD 'change-me-local-only';
CREATE DATABASE lenny_assistant OWNER lenny;
\qCREATE ROLE lenny WITH LOGIN PASSWORD 'change-me-local-only';
CREATE DATABASE lenny_assistant OWNER lenny;
\q# Design Document

## UI/UX principles

- Minimal but premium SaaS look with strong information hierarchy
- Calm dark color palette with readable contrast ratios
- Simple, debt-free experience focused on research and writing outcomes
- Clear emphasis on evidence and source integrity

## Information architecture

- Left sidebar: sessions and model state
- Center pane: chat, prompts, and conversation flow
- Right pane: artifact preview, readable source/code, and source references
- Bottom composer: message entry and action controls

## Chat and artifact workflows

A candidate starts with a suggested prompt, writes a question, and receives a source-backed answer with citations. Then they can create or regenerate a Markdown artifact or Ship 30 essay without leaving the main conversation view.

The model selector shows the selected provider and model. When configured cloud requests fail and Ollama is reachable, the answer states that it used the local fallback. Unsupported topics show an explicit no-evidence disclosure. Source panels distinguish synthetic demo data from genuine user-supplied sources.

The artifact panel stays beside the conversation on wide screens and becomes a dismissible overlay on narrow screens. It supports Markdown preview, sanitized HTML/CSS preview, readable source code, copying, downloading, and Ship 30 essay output.

## Loading, error, and empty states

- Welcome screen when no conversation exists
- Loading indicator while the model or provider responds
- Clear fallback status when a model is offline
- Empty-state guidance when no knowledge sources match a question
- Explicit errors when a session, artifact, database, or provider request fails

## Responsive behavior

The interface collapses to a compact layout under tablet widths. On small screens, the artifact viewer opens as an overlay rather than disappearing; the main conversation remains available behind it.

## Accessibility decisions

- Sufficient contrast between text and surfaces
- Large touch targets for interaction buttons
- Form controls with understandable labels and clear focus states
- Semantic structure for headings and messages
- HTML previews use DOMPurify, a sandbox without same-origin or script access, and a restrictive Content Security Policy
