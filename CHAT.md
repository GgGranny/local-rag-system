# Chat lifecycle and source viewer

`POST /chat/conversations` creates a UUID-backed conversation with the authenticated session user as its owner. The browser records the active conversation in `?conversation=<thread_id>`; refresh and browser navigation reload only that thread's checkpointed messages.

Regular users can list, load, ask in, and delete only their own conversations. Administrators can list and manage conversations for monitoring. `DELETE /chat/conversations/<thread_id>` removes the conversation row and its LangGraph SQLite checkpoint records; it never deletes uploaded documents, vectors, chunks, or shared source assets.

The source viewer is available only for completed shared documents, matching retrieval access. It returns canonical extracted page text, chunks, and safe image-route URLs rather than filesystem paths. PDF embedded images and OCR page renders are persisted under `data/source_images`; `/documents/images/<image_id>` validates the image and its completed document before serving it. Citations include document and chunk IDs and, when their source page has a visual, an image ID. OCR-backed sources are labeled as OCR and display the page image without pretending to pixel-highlight text.

If a chat does not appear after creating it, check the `POST /chat/conversations` response and the browser's network panel. If an image is unavailable, the source panel retains source text and reports the error; reprocess the document to regenerate missing source assets. Switching chats clears messages, sources, citations, and selection state before loading the requested conversation.
