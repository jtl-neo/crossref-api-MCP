---
name: crossref-api
description: Search and retrieve scholarly metadata from the Crossref REST API (DOIs, papers, journals, publishers, funders, author affiliations). Use when the user asks for academic literature, citation data, DOI lookup/verification, or publisher/funder info. Requires the agent to be able to make HTTP GET requests.
---

# Skill: Crossref API Metadata Search & Retrieval

## Description
This skill allows the LLM to interact with the Crossref REST API to search, filter, and retrieve scholarly metadata, including DOIs, academic papers, journals, publishers, funders, and author affiliations. Use this skill when the user asks for academic literature, citation data, DOI verification, or publisher information.

## Base URL
`https://api.crossref.org`

## Guidelines for LLM Usage
- **Etiquette / Polite Request**: Always append your email to the query string as `mailto=your-email@example.com` to join the Crossref "polite pool", ensuring faster and more reliable responses.
- **Pagination**: Use `rows` (max 1000) and `offset` for basic pagination, or `cursor=*` for deep paging through large result sets.
- **Standard Filters**: Many endpoints support `filter`. Filters are comma-separated pairs, e.g., `filter=has-orcid:true,from-pub-date:2023-01-01`.

---

## Core Functions

### 1. Search Works (Articles, Books, Conference Papers, etc.)
Retrieves metadata for scholarly articles or searches across all Crossref records.

- **Endpoint:** `GET /works`
- **Key Parameters:**
  - `query` (string, optional): Free-text search query (e.g., keywords, title, authors).
  - `filter` (string, optional): Filter results (e.g., `has-references:true`, `type:journal-article`, `is-update:true`).
  - `rows` (integer, optional): Number of results per page (default: 20).
  - `sort` (string, optional): Field to sort by (e.g., `published`, `is-referenced-by-count`, `relevance`).
  - `order` (string, optional): `asc` or `desc`.

### 2. Get Work by DOI
Retrieves full metadata for a specific academic work using its unique DOI.

- **Endpoint:** `GET /works/{doi}`
- **Key Parameters:**
  - `doi` (string, required): The DOI of the work (e.g., `10.1038/nature12345`).

### 3. Search Funders
Searches for research funding organizations registered with Crossref.

- **Endpoint:** `GET /funders`
- **Key Parameters:**
  - `query` (string, optional): Name of the funding body (e.g., `National Science Foundation`).

### 4. Get Funder Works
Retrieves all academic works funded by a specific funder ID.

- **Endpoint:** `GET /funders/{funder_id}/works`
- **Key Parameters:**
  - `funder_id` (string, required): The unique Crossref Funder ID.

### 5. Search Members (Publishers)
Searches for publishers or organizations that register DOIs with Crossref.

- **Endpoint:** `GET /members`
- **Key Parameters:**
  - `query` (string, optional): Name of the publisher (e.g., `Elsevier`, `Springer`).

### 6. Search Journals
Searches for academic journals, magazines, or conference proceedings.

- **Endpoint:** `GET /journals`
- **Key Parameters:**
  - `query` (string, optional): Journal title or ISSN (e.g., `Nature`, `0028-0836`).

---

## Common Use Cases & Execution Examples

### Example 1: Search for recent papers about "Machine Learning" published in 2025
* **Target Endpoint:** `GET /works`
* **Constructed URL:** `https://api.crossref.org/works?query=machine+learning&filter=from-pub-date:2025-01-01&sort=published&order=desc&mailto=agent@example.com`

### Example 2: Fetch metadata for a known DOI
* **Target Endpoint:** `GET /works/{doi}`
* **Constructed URL:** `https://api.crossref.org/works/10.1145/3318464.3389700?mailto=agent@example.com`

## Response Interpretation
- **Status 200 OK**: The response body contains a JSON object. The actual data is always wrapped inside a `"message"` object (e.g., `response.message.items` for lists, or `response.message` for single objects).
- **Status 404 Not Found**: The DOI or ID provided does not exist in Crossref.
- **Status 429 Too Many Requests**: Rate limit hit. Slow down requests.