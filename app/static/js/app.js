let currentThreadId = null;
let documents = [];
let selectedDocumentIds = new Set();
let statusPoll = null;

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

function clearChat() { byId("chat-messages").innerHTML = '<div id="chat-empty" class="chat-empty"><p class="eyebrow">Shared knowledge assistant</p><h1>Ask your documents</h1><p>Select documents to narrow the search, or search all completed documents in the shared knowledge base.</p><div class="suggestion-list"><span>“What is this document about?”</span><span>“Summarize the selected documents.”</span></div></div>'; byId("source-list").innerHTML = '<p class="empty-state">Select a citation in an answer to inspect its source.</p>'; }

function addMessage(role, content, sources = []) {
    byId("chat-empty")?.remove(); const message = document.createElement("article"); message.className = `message message-${role}`; const body = document.createElement("div"); body.className = "message-content";
    let cursor = 0; const pattern = /\[(\d+)\]/g; let match;
    while ((match = pattern.exec(content)) !== null) { body.append(document.createTextNode(content.slice(cursor, match.index))); const citation = `[${match[1]}]`; const source = sources.find((item) => item.citation === citation); if (source) { const button = document.createElement("button"); button.type = "button"; button.className = "citation-link"; button.textContent = citation; button.addEventListener("click", () => showSource(source)); body.append(button); } else body.append(document.createTextNode(citation)); cursor = match.index + citation.length; }
    body.append(document.createTextNode(content.slice(cursor))); message.appendChild(body); byId("chat-messages").appendChild(message); byId("chat-messages").scrollTop = byId("chat-messages").scrollHeight;
}
function setGenerating(active, message = "Searching shared documents…") { const status = byId("generation-status"); status.hidden = !active; status.textContent = active ? message : ""; byId("send-button").disabled = active; }
function renderSources(sources) { const list = byId("source-list"); list.replaceChildren(); if (!sources.length) { list.innerHTML = '<p class="empty-state">No sources were used for this answer.</p>'; return; } sources.forEach((source) => { const item = document.createElement("article"); item.className = "source-item"; item.id = `source-${source.citation.replace(/[^0-9]/g, "")}`; item.innerHTML = `<p class="eyebrow">Source ${escapeHtml(source.citation)}</p><strong>${escapeHtml(source.filename)}</strong><small>Page ${escapeHtml(source.page_number ?? "not available")}</small><p class="source-passage"></p>`; item.querySelector(".source-passage").textContent = source.content || "Source text is unavailable."; list.appendChild(item); }); }
function showSource(source) { renderSources([source]); byId(`source-${source.citation.replace(/[^0-9]/g, "")}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }

async function loadConversations() { const response = await fetch("/chat/conversations"); if (!response.ok) return; const entries = await response.json(); const list = byId("conversation-list"); list.replaceChildren(); if (!entries.length) { list.innerHTML = '<p class="empty-state">No conversations yet.</p>'; return; } entries.forEach((entry) => { const item = document.createElement("button"); item.type = "button"; item.className = "conversation-item"; item.textContent = entry.title; item.dataset.threadId = entry.thread_id; item.addEventListener("click", () => loadConversation(entry.thread_id)); list.appendChild(item); }); }
function highlightActiveConversation(threadId) { document.querySelectorAll(".conversation-item").forEach((item) => item.classList.toggle("active", item.dataset.threadId === threadId)); }
async function createConversation() { const response = await fetch("/chat/conversations", { method: "POST" }); if (!response.ok) throw new Error("Failed to create conversation."); const entry = await response.json(); currentThreadId = entry.thread_id; clearChat(); await loadConversations(); highlightActiveConversation(currentThreadId); }
async function loadConversation(threadId) { const response = await fetch(`/chat/conversations/${encodeURIComponent(threadId)}`); if (!response.ok) return; const entry = await response.json(); currentThreadId = entry.thread_id; clearChat(); entry.messages.forEach((message) => addMessage(message.role, message.content)); highlightActiveConversation(threadId); }
async function sendMessage() { const input = byId("chat-input"); const question = input.value.trim(); if (!question || byId("send-button").disabled) return; try { if (!currentThreadId) await createConversation(); addMessage("user", question); input.value = ""; setGenerating(true); const response = await fetch("/chat/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ thread_id: currentThreadId, question, document_ids: selectedIds() }) }); const result = await response.json(); if (!response.ok) throw new Error(result.error || "Something went wrong while generating the answer."); setGenerating(true, "Generating answer…"); addMessage("assistant", result.answer, result.sources || []); renderSources(result.sources || []); await loadConversations(); highlightActiveConversation(currentThreadId); } catch (error) { addMessage("assistant", error.message || "Something went wrong while generating the answer."); } finally { setGenerating(false); input.focus(); } }

function initialiseChat() { byId("upload-button").addEventListener("click", () => byId("file-input").click()); byId("file-input").addEventListener("change", () => { if (byId("file-input").files[0]) { showUploadPreview(byId("file-input").files[0]); uploadDocument(); } }); byId("new-chat-button").addEventListener("click", () => createConversation().catch((error) => alert(error.message))); byId("send-button").addEventListener("click", sendMessage); byId("chat-input").addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } }); byId("close-progress-modal").addEventListener("click", () => byId("document-progress-modal").close()); loadConversations(); loadDocuments().catch(() => {}); }
function initialiseLogin() { const form = byId("login-form"); if (!form) return; byId("password-toggle").addEventListener("click", () => { const input = byId("password"); const visible = input.type === "text"; input.type = visible ? "password" : "text"; byId("password-toggle").textContent = visible ? "Show" : "Hide"; }); form.addEventListener("submit", () => { const button = form.querySelector("button[type=submit]"); button.disabled = true; button.querySelector(".button-label").textContent = "Signing in…"; }); }
if (isChatPage()) initialiseChat(); else initialiseLogin();
