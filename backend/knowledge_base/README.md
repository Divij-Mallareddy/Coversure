# Backend Knowledge Base

This folder powers the RAG chatbot with developer-managed knowledge.

Add knowledge files under `content/`:

- `policies/` for policy wording and coverage documents
- `faqs/` for Q&A datasets
- `brochures/` for marketing or product brochures
- `manuals/` for internal support manuals
- `internal/` for private operating notes

Supported file types:

- `.txt`
- `.md` / `.markdown`
- `.json`
- `.pdf`

The generated vector index is stored in `index/` and ignored from git.

Run this after editing knowledge files:

```bash
cd backend
python scripts/rebuild_knowledge.py
```
