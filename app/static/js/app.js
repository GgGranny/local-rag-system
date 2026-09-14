let currentThreadId = null;
let documents = [];
let selectedDocumentIds = new Set();
let statusPoll = null;
let sourceRequestId = 0;

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const statusCopy = { PENDING: "Waiting for admin approval", APPROVED: "Approved — processing will begin", PROCESSING: "Processing document", COMPLETED: "Ready to chat", FAILED: "Processing failed", REJECTED: "Document rejected" };

function isChatPage() { return Boolean(byId("chat-messages")); }
function selectedIds() { return [...selectedDocumentIds]; }
function isAdmin() { return document.querySelector(".chat-layout")?.dataset.role === "ADMIN"; }

function renderDocuments() {
    const list = byId("document-list");
    list.replaceChildren();
    if (!documents.length) { list.innerHTML = '<p class="empty-state">No documents uploaded yet.</p>'; return; }
    documents.forEach((item) => {
        const selectable = item.status === "COMPLETED";
        const row = document.createElement("label");
        row.className = `document-item ${selectedDocumentIds.has(item.id) ? "selected" : ""} ${!selectable ? "unavailable" : ""}`;
        const uploader = item.uploader ? `<span class="document-uploader">Uploaded by ${escapeHtml(item.uploader)}</span>` : "";
        row.innerHTML = `<input type="checkbox" ${selectable ? "" : "disabled"} ${selectedDocumentIds.has(item.id) ? "checked" : ""} aria-label="Use ${escapeHtml(item.filename)} for retrieval"><span class="document-info"><span class="document-name">${escapeHtml(item.filename)}</span>${uploader}<span class="status-badge status-${item.status.toLowerCase()}">${escapeHtml(statusCopy[item.status] || item.status)}</span></span>`;
        row.querySelector("input").addEventListener("change", () => selectDocument(item.id));
        row.addEventListener("dblclick", () => showProcessingDetails(item));
        list.appendChild(row);
    });
    updateSelectionSummary();
}

function selectDocument(id) {
    selectedDocumentIds.has(id) ? selectedDocumentIds.delete(id) : selectedDocumentIds.add(id);
    renderDocuments();
}

function updateSelectionSummary() {
    const summary = byId("selection-summary");
    const chosen = documents.filter((item) => selectedDocumentIds.has(item.id));
    if (!chosen.length) summary.textContent = "Searching all completed documents";
    else summary.textContent = `Using ${chosen.length} selected document${chosen.length === 1 ? "" : "s"}`;
}

async function loadDocuments() {
    const response = await fetch("/documents/mine");
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Failed to load documents.");
    documents = result;
    const validIds = new Set(documents.filter((item) => item.status === "COMPLETED").map((item) => item.id));
    selectedDocumentIds = new Set(selectedIds().filter((id) => validIds.has(id)));
    renderDocuments();
    updatePolling();
}

function updatePolling() {
    const needsPolling = documents.some((item) => ["PENDING", "APPROVED", "PROCESSING"].includes(item.status));
    if (needsPolling && !statusPoll) statusPoll = window.setInterval(() => loadDocuments().catch(() => {}), 3000);
    if (!needsPolling && statusPoll) { window.clearInterval(statusPoll); statusPoll = null; }
}

function showUploadPreview(file) {
    const preview = byId("upload-preview");
    preview.hidden = false;
    preview.innerHTML = `<strong>${escapeHtml(file.name)}</strong><span>${escapeHtml(file.name.split(".").pop()?.toUpperCase() || "FILE")} · ${formatBytes(file.size)}</span>`;
}
function formatBytes(size) { return size < 1024 * 1024 ? `${Math.ceil(size / 1024)} KB` : `${(size / (1024 * 1024)).toFixed(1)} MB`; }

function showUploadStatus(item) {
    const card = byId("upload-status");
    card.hidden = false;
    card.dataset.documentId = item.id;
    card.innerHTML = `<strong>${escapeHtml(item.filename)}</strong><span class="status-badge status-${item.status.toLowerCase()}">${escapeHtml(statusCopy[item.status] || item.status)}</span><button type="button">View processing details →</button>`;
    card.querySelector("button").addEventListener("click", () => showProcessingDetails(item));
}

async function uploadDocument() {
    const input = byId("file-input"); const button = byId("upload-button"); const file = input.files[0];
    if (!file) return;
    showUploadPreview(file); button.disabled = true; button.textContent = "Uploading…";
    const formData = new FormData(); formData.append("file", file);
    try {
        const response = await fetch("/documents/upload", { method: "POST", headers: { Accept: "application/json" }, body: formData });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Could not upload the document.");
        showUploadStatus(result.document); await loadDocuments();
    } catch (error) { alert(error.message || "Could not upload the document."); }
    finally { input.value = ""; button.disabled = false; button.textContent = "Upload"; }
}

function showProcessingDetails(item) {
    const modal = byId("document-progress-modal");
    byId("progress-title").textContent = item.filename;
    const order = ["PENDING", "APPROVED", "PROCESSING", "COMPLETED"];
    const index = order.indexOf(item.status);
    const steps = item.status === "REJECTED" || item.status === "FAILED" ? ["File uploaded", statusCopy[item.status]] : order.map((step, position) => `${position <= index ? "✓" : "○"} ${step === "PENDING" ? "Waiting for approval" : statusCopy[step]}`);
    byId("progress-steps").innerHTML = steps.map((step) => `<p>${escapeHtml(step)}</p>`).join("");
    modal.showModal();
}

function resetSourcePanel(message = "Select a citation in an answer to inspect its source.") {
    sourceRequestId += 1;
    byId("source-title").textContent = "Sources";
    byId("source-meta").textContent = message;
    byId("source-list").replaceChildren();
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = message;
    byId("source-list").appendChild(empty);
}

function clearChat() { byId("chat-messages").innerHTML = '<div id="chat-empty" class="chat-empty"><p class="eyebrow">Shared knowledge assistant</p><h1>Ask your documents</h1><p>Select documents to narrow the search, or search all completed documents in the shared knowledge base.</p><div class="suggestion-list"><span>“What is this document about?”</span><span>“Summarize the selected documents.”</span></div></div>'; resetSourcePanel(); }

function addMessage(role, content, sources = []) {
    byId("chat-empty")?.remove(); const message = document.createElement("article"); message.className = `message message-${role}`; const body = document.createElement("div"); body.className = "message-content";
    let cursor = 0; const pattern = /\[(\d+)\]/g; let match;
    while ((match = pattern.exec(content)) !== null) { body.append(document.createTextNode(content.slice(cursor, match.index))); const citation = `[${match[1]}]`; const source = sources.find((item) => item.citation === citation); if (source) { const button = document.createElement("button"); button.type = "button"; button.className = "citation-link"; button.textContent = citation; button.addEventListener("click", () => showSource(source)); body.append(button); } else body.append(document.createTextNode(citation)); cursor = match.index + citation.length; }
    body.append(document.createTextNode(content.slice(cursor))); message.appendChild(body); byId("chat-messages").appendChild(message); byId("chat-messages").scrollTop = byId("chat-messages").scrollHeight;
}
function setGenerating(active, message = "Searching shared documents…") { const status = byId("generation-status"); status.hidden = !active; status.textContent = active ? message : ""; byId("send-button").disabled = active; }
function renderSources(sources) {
    if (!sources.length) { resetSourcePanel("No sources were used for this answer."); return; }
    byId("source-title").textContent = "Sources used";
    byId("source-meta").textContent = `${sources.length} source${sources.length === 1 ? "" : "s"} cited. Select an inline citation to open it.`;
    byId("source-list").replaceChildren();
    const note = document.createElement("p");
    note.className = "empty-state";
    note.textContent = "Citations open the complete source here.";
    byId("source-list").appendChild(note);
}

function appendSourceText(container, text) {
    const lines = String(text || "").split(/\n+/).map((line) => line.trim()).filter(Boolean);
    if (!lines.length) { const empty = document.createElement("p"); empty.textContent = "No readable text was extracted for this section."; container.appendChild(empty); return; }
    let list = null;
    lines.forEach((line) => {
        const bullet = line.match(/^[-*•]\s+(.+)/);
        const numbered = line.match(/^\d+[.)]\s+(.+)/);
        if (bullet || numbered) {
            if (!list || list.tagName !== (numbered ? "OL" : "UL")) { list = document.createElement(numbered ? "ol" : "ul"); container.appendChild(list); }
            const item = document.createElement("li"); item.textContent = (bullet || numbered)[1]; list.appendChild(item); return;
        }
        list = null;
        const paragraph = document.createElement(line.length < 100 && /[:.]$/.test(line) ? "h3" : "p");
        paragraph.textContent = line;
        container.appendChild(paragraph);
    });
}

function sourceLines(text) {
    return String(text || "").split(/\n+/).map((line) => line.trim()).filter(Boolean);
}

function appendSemanticLine(container, line) {
    const bullet = line.match(/^[-*•]\s+(.+)/);
    const numbered = line.match(/^\d+[.)]\s+(.+)/);
    if (bullet || numbered) {
        const list = document.createElement(numbered ? "ol" : "ul");
        const item = document.createElement("li");
        item.textContent = (bullet || numbered)[1];
        list.appendChild(item); container.appendChild(list); return item;
    }
    const element = document.createElement(line.length < 100 && /[:.]$/.test(line) ? "h3" : "p");
    element.textContent = line; container.appendChild(element); return element;
}

function appendSourceImages(container, images, citedImageId) {
    images.forEach((image) => {
        const figure = document.createElement("figure");
        figure.className = "source-image";
        figure.id = `source-image-${image.image_id}`;
        if (image.image_id === citedImageId) figure.classList.add("is-cited-image");
        const element = document.createElement("img");
        element.src = image.url;
        element.alt = image.source_kind === "ocr_page" ? "OCR source page" : "Source document figure";
        element.loading = "lazy";
        figure.appendChild(element);
        if (image.source_kind === "ocr_page") { const caption = document.createElement("figcaption"); caption.textContent = "Source page used for OCR"; figure.appendChild(caption); }
        container.appendChild(figure);
    });
}

function markCitedText(container, chunkId, chunkContent) {
    const firstLine = sourceLines(chunkContent).find((line) => line.length >= 16) || "";
    const candidate = firstLine.slice(0, 80).replace(/\s+/g, " ");
    const elements = container.querySelectorAll("p,h1,h2,h3,h4,h5,h6,li");
    const target = [...elements].find((element) => element.textContent.replace(/\s+/g, " ").includes(candidate));
    if (target) {
        target.id = `source-chunk-${chunkId}`;
        target.classList.add("is-cited");
        return target;
    }
    return null;
}

function renderSourcePage(container, page, images, citedChunk) {
    // This is a structural section only, never a visual PDF page/card.
    const pageContent = document.createElement("section");
    pageContent.className = "source-content";
    const lines = sourceLines(page.content);
    const positionedImages = [...images].sort((a, b) => (a.vertical_position ?? 1) - (b.vertical_position ?? 1));
    let imageCursor = 0;
    lines.forEach((line, index) => {
        while (
            imageCursor < positionedImages.length
            && (positionedImages[imageCursor].vertical_position ?? 1) <= index / Math.max(lines.length, 1)
        ) {
            appendSourceImages(pageContent, [positionedImages[imageCursor]], null);
            imageCursor += 1;
        }
        appendSemanticLine(pageContent, line);
    });
    while (imageCursor < positionedImages.length) {
        appendSourceImages(pageContent, [positionedImages[imageCursor]], null);
        imageCursor += 1;
    }
    if (!lines.length && !positionedImages.length) appendSourceText(pageContent, page.content);
    container.appendChild(pageContent);

    if (citedChunk) {
        const target = markCitedText(pageContent, citedChunk.chunk_id, citedChunk.content);
        if (!target) {
            pageContent.id = `source-chunk-${citedChunk.chunk_id}`;
            pageContent.classList.add("is-cited");
        }
    }
    if (["ocr", "paddleocr"].includes(page.extraction_method)) {
        const note = document.createElement("p"); note.className = "source-ocr-note";
        note.textContent = "Text extracted with OCR"; container.appendChild(note);
    }
}

function renderSourceDocument(sourceDocument, citedChunkId, citation, citedImageId = null) {
    const list = byId("source-list"); list.replaceChildren();
    byId("source-title").textContent = sourceDocument.filename || "Source document";
    const cited = sourceDocument.chunks.find((chunk) => chunk.chunk_id === citedChunkId);
    byId("source-meta").textContent = `${citation || "Source"}${cited?.page_number ? ` · page ${cited.page_number}` : ""}${cited?.extraction_method ? ` · ${cited.extraction_method}` : ""}`;
    const imagesByPage = new Map();
    (sourceDocument.images || []).forEach((image) => {
        const pageImages = imagesByPage.get(image.page_number) || [];
        pageImages.push(image); imagesByPage.set(image.page_number, pageImages);
    });
    // New ingestions retain canonical page text.  Unlike chunk rendering, it
    // has no splitter overlap and lets images sit near their source position.
    if (sourceDocument.pages?.length) {
        sourceDocument.pages.forEach((page) => {
            const block = document.createElement("article");
            block.className = "source-block";
            const citedOnPage = cited?.page_number === page.page_number ? cited : null;
            renderSourcePage(block, page, imagesByPage.get(page.page_number) || [], citedOnPage);
            list.appendChild(block);
        });
        if (citedImageId) {
            const imageTarget = byId(`source-image-${citedImageId}`);
            imageTarget?.classList.add("is-cited-image");
        }
        const targetId = citedImageId ? `source-image-${citedImageId}` : `source-chunk-${citedChunkId}`;
        byId(targetId)?.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
    }

    // Documents ingested before page-source preservation retain the legacy
    // chunk fallback; reprocess them to get image placement in reading order.
    sourceDocument.chunks.forEach((chunk, index) => {
        const block = document.createElement("article");
        block.className = "source-block"; block.id = `source-chunk-${chunk.chunk_id}`;
        if (chunk.chunk_id === citedChunkId) block.classList.add("is-cited");
        const content = document.createElement("div"); content.className = "source-content";
        appendSourceText(content, chunk.content); block.appendChild(content);
        if (["ocr", "paddleocr"].includes(chunk.extraction_method)) { const note = document.createElement("p"); note.className = "source-ocr-note"; note.textContent = "Extracted with OCR"; block.appendChild(note); }
        list.appendChild(block);
        const nextChunk = sourceDocument.chunks[index + 1];
        if (!nextChunk || nextChunk.page_number !== chunk.page_number) {
            appendSourceImages(list, imagesByPage.get(chunk.page_number) || [], citedImageId);
        }
    });
    const targetId = citedImageId ? `source-image-${citedImageId}` : `source-chunk-${citedChunkId}`;
    byId(targetId)?.scrollIntoView({ behavior: "smooth", block: "center" });
}

function showSourceLoading(source) {
    byId("source-title").textContent = source.filename || "Source";
    byId("source-meta").textContent = "Loading cited source…";
    byId("source-list").innerHTML = '<div class="source-loading" role="status"><span class="loading-dot"></span>Loading source content…</div>';
}

async function showSource(source) {
    const requestId = ++sourceRequestId; showSourceLoading(source);
    try {
        const response = await fetch(`/documents/${encodeURIComponent(source.document_id)}/source`);
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Unable to load this source.");
        if (requestId !== sourceRequestId) return;
        renderSourceDocument(result, source.chunk_id, source.citation, source.image_id || null);
    } catch (error) {
        if (requestId !== sourceRequestId) return;
        byId("source-meta").textContent = "Source unavailable"; byId("source-list").replaceChildren();
        const panel = document.createElement("div"); panel.className = "source-error";
        const message = document.createElement("p"); message.textContent = error.message || "Unable to load this source.";
        const retry = document.createElement("button"); retry.type = "button"; retry.textContent = "Try again"; retry.addEventListener("click", () => showSource(source));
        panel.append(message, retry); byId("source-list").appendChild(panel);
    }
}

function setActiveThread(threadId, replace = false) {
    currentThreadId = threadId || null;
    const url = new URL(window.location.href);
    if (threadId) url.searchParams.set("conversation", threadId); else url.searchParams.delete("conversation");
    window.history[replace ? "replaceState" : "pushState"]({}, "", url);
}

function displayTime(value) {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? "" : date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

async function loadConversations() {
    const response = await fetch("/chat/conversations");
    if (!response.ok) throw new Error("Could not load conversations.");
    const entries = await response.json(); const list = byId("conversation-list"); list.replaceChildren();
    if (!entries.length) { list.innerHTML = '<p class="empty-state">No conversations yet. Start a new chat.</p>'; return entries; }
    entries.forEach((entry) => {
        const row = document.createElement("div"); row.className = "conversation-row";
        const item = document.createElement("button"); item.type = "button"; item.className = "conversation-item"; item.dataset.threadId = entry.thread_id;
        const owner = isAdmin() && entry.owner ? `<span class="conversation-owner">${escapeHtml(entry.owner)}</span>` : "";
        item.innerHTML = `<span class="conversation-title">${escapeHtml(entry.title || "New conversation")}</span><span class="conversation-details">${owner}<time>${escapeHtml(displayTime(entry.updated_at))}</time></span>`;
        item.addEventListener("click", () => loadConversation(entry.thread_id));
        const remove = document.createElement("button"); remove.type = "button"; remove.className = "conversation-delete"; remove.title = "Delete chat"; remove.setAttribute("aria-label", `Delete ${entry.title || "chat"}`); remove.textContent = "×";
        remove.addEventListener("click", (event) => { event.stopPropagation(); deleteConversation(entry.thread_id, entry.title); });
        row.append(item, remove); list.appendChild(row);
    });
    highlightActiveConversation(currentThreadId); return entries;
}
function highlightActiveConversation(threadId) { document.querySelectorAll(".conversation-item").forEach((item) => item.classList.toggle("active", item.dataset.threadId === threadId)); }
async function createConversation() { const response = await fetch("/chat/conversations", { method: "POST" }); const entry = await response.json(); if (!response.ok) throw new Error(entry.error || "Failed to create conversation."); selectedDocumentIds.clear(); setActiveThread(entry.thread_id); clearChat(); byId("chat-input").value = ""; await loadConversations(); highlightActiveConversation(currentThreadId); byId("chat-input").focus(); }
async function loadConversation(threadId, replaceHistory = false) { clearChat(); const response = await fetch(`/chat/conversations/${encodeURIComponent(threadId)}`); const entry = await response.json(); if (!response.ok) { clearChat(); throw new Error(entry.error || "Could not load conversation."); } setActiveThread(entry.thread_id, replaceHistory); const lastAssistantIndex = [...entry.messages].map((item) => item.role).lastIndexOf("assistant"); entry.messages.forEach((message, index) => addMessage(message.role, message.content, index === lastAssistantIndex ? entry.sources || [] : [])); highlightActiveConversation(threadId); }
async function deleteConversation(threadId, title) { if (!window.confirm(`Delete ${title || "this chat"}?\nThis action cannot be undone.`)) return; const response = await fetch(`/chat/conversations/${encodeURIComponent(threadId)}`, { method: "DELETE" }); const result = await response.json(); if (!response.ok) { alert(result.error || "Could not delete this chat."); return; } const entries = await loadConversations(); if (currentThreadId === threadId) { const next = entries.find((entry) => entry.thread_id !== threadId); if (next) await loadConversation(next.thread_id, true); else { setActiveThread(null, true); clearChat(); } } }
async function sendMessage() { const input = byId("chat-input"); const question = input.value.trim(); if (!question || byId("send-button").disabled) return; try { if (!currentThreadId) await createConversation(); addMessage("user", question); input.value = ""; setGenerating(true); const response = await fetch("/chat/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ thread_id: currentThreadId, question, document_ids: selectedIds() }) }); const result = await response.json(); if (!response.ok) throw new Error(result.error || "Something went wrong while generating the answer."); setGenerating(true, "Generating answer…"); addMessage("assistant", result.answer, result.sources || []); renderSources(result.sources || []); await loadConversations(); highlightActiveConversation(currentThreadId); } catch (error) { addMessage("assistant", error.message || "Something went wrong while generating the answer."); } finally { setGenerating(false); input.focus(); } }

function initialiseChat() { byId("upload-button").addEventListener("click", () => byId("file-input").click()); byId("file-input").addEventListener("change", () => { if (byId("file-input").files[0]) { showUploadPreview(byId("file-input").files[0]); uploadDocument(); } }); byId("new-chat-button").addEventListener("click", () => createConversation().catch((error) => alert(error.message))); byId("send-button").addEventListener("click", sendMessage); byId("chat-input").addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } }); byId("close-progress-modal").addEventListener("click", () => byId("document-progress-modal").close()); window.addEventListener("popstate", () => { const threadId = new URL(window.location.href).searchParams.get("conversation"); if (threadId) loadConversation(threadId, true).catch(() => { setActiveThread(null, true); clearChat(); }); else { currentThreadId = null; clearChat(); } }); const requested = new URL(window.location.href).searchParams.get("conversation"); loadConversations().then(() => requested && loadConversation(requested, true)).catch(() => {}); loadDocuments().catch(() => {}); }
function initialiseLogin() { const form = byId("login-form"); if (!form) return; byId("password-toggle").addEventListener("click", () => { const input = byId("password"); const visible = input.type === "text"; input.type = visible ? "password" : "text"; byId("password-toggle").textContent = visible ? "Show" : "Hide"; }); form.addEventListener("submit", () => { const button = form.querySelector("button[type=submit]"); button.disabled = true; button.querySelector(".button-label").textContent = "Signing in…"; }); }
if (isChatPage()) initialiseChat(); else initialiseLogin();
