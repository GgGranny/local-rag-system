let currentThreadId = null;

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

function isChatPage() {
    return Boolean(byId("chat-messages"));
}

async function loadDocuments() {
    const list = byId("document-list");
    if (!list) return;
    const response = await fetch("/documents/mine");
    const documents = await response.json();
    if (!response.ok) throw new Error(documents.error || "Failed to load documents.");
    list.replaceChildren();
    if (!documents.length) {
        list.innerHTML = '<p class="empty-state">No documents yet.</p>';
        return;
    }
    documents.forEach((item) => {
        const element = document.createElement("div");
        element.className = "document-item";
        element.innerHTML = `<div class="document-info"><div class="document-name">📄 ${escapeHtml(item.filename)}</div><div class="document-status status-${escapeHtml(item.status.toLowerCase())}">${escapeHtml(item.status)}</div></div>`;
        list.appendChild(element);
    });
}

async function uploadDocument() {
    const input = byId("file-input");
    const button = byId("upload-button");
    if (!input.files[0]) return;
    const formData = new FormData();
    formData.append("file", input.files[0]);
    button.disabled = true;
    button.textContent = "Uploading…";
    try {
        const response = await fetch("/documents/upload", { method: "POST", headers: { Accept: "application/json" }, body: formData });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Upload failed.");
        await loadDocuments();
    } catch (error) {
        alert(error.message || "Failed to upload document.");
    } finally {
        input.value = "";
        button.disabled = false;
        button.textContent = "+ Upload";
    }
}

function clearChat() {
    byId("chat-messages").innerHTML = '<div id="chat-empty" class="chat-empty"><h1>Document Assistant</h1><p>Ask questions about your uploaded documents.</p></div>';
    byId("source-list").innerHTML = '<p class="empty-state">Sources will appear here.</p>';
}

function showSource(source) {
    byId(`source-${source.citation.replaceAll(/[^0-9]/g, "")}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function addMessage(role, content, sources = []) {
    byId("chat-empty")?.remove();
    const message = document.createElement("div");
    message.className = `message message-${role}`;
    const body = document.createElement("div");
    body.className = "message-content";
    const pattern = /\[(\d+)\]/g;
    let cursor = 0;
    let match;
    while ((match = pattern.exec(content)) !== null) {
        body.append(document.createTextNode(content.slice(cursor, match.index)));
        const citation = `[${match[1]}]`;
        const source = sources.find((item) => item.citation === citation);
        if (source) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "citation-link";
            button.textContent = citation;
            button.addEventListener("click", () => showSource(source));
            body.append(button);
        } else body.append(document.createTextNode(citation));
        cursor = match.index + citation.length;
    }
    body.append(document.createTextNode(content.slice(cursor)));
    message.appendChild(body);
    byId("chat-messages").appendChild(message);
    byId("chat-messages").scrollTop = byId("chat-messages").scrollHeight;
}

function displaySources(sources) {
    const list = byId("source-list");
    list.replaceChildren();
    if (!sources.length) {
        list.innerHTML = '<p class="empty-state">No sources found.</p>';
        return;
    }
    sources.forEach((source) => {
        const item = document.createElement("article");
        item.className = "source-item";
        item.id = `source-${source.citation.replaceAll(/[^0-9]/g, "")}`;
        item.innerHTML = `<strong>${escapeHtml(source.citation)} ${escapeHtml(source.filename)}</strong><small>Page ${escapeHtml(source.page_number ?? "not available")} · ${escapeHtml(source.extraction_method || "native extraction")}</small><pre></pre>`;
        item.querySelector("pre").textContent = source.content || "Source text is unavailable.";
        list.appendChild(item);
    });
}

async function loadConversations() {
    const response = await fetch("/chat/conversations");
    if (!response.ok) return;
    const conversations = await response.json();
    const list = byId("conversation-list");
    list.replaceChildren();
    if (!conversations.length) {
        list.innerHTML = '<p class="empty-state">No conversations yet.</p>';
        return;
    }
    conversations.forEach((conversation) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "conversation-item";
        item.textContent = conversation.title;
        item.dataset.threadId = conversation.thread_id;
        item.addEventListener("click", () => loadConversation(conversation.thread_id));
        list.appendChild(item);
    });
}

function highlightActiveConversation(threadId) {
    document.querySelectorAll(".conversation-item").forEach((item) => item.classList.toggle("active", item.dataset.threadId === threadId));
}

async function createConversation() {
    const response = await fetch("/chat/conversations", { method: "POST" });
    if (!response.ok) throw new Error("Failed to create conversation.");
    const conversation = await response.json();
    currentThreadId = conversation.thread_id;
    clearChat();
    await loadConversations();
    highlightActiveConversation(currentThreadId);
}

async function loadConversation(threadId) {
    const response = await fetch(`/chat/conversations/${encodeURIComponent(threadId)}`);
    if (!response.ok) return;
    const conversation = await response.json();
    currentThreadId = conversation.thread_id;
    clearChat();
    conversation.messages.forEach((message) => addMessage(message.role, message.content));
    highlightActiveConversation(threadId);
}

async function sendMessage() {
    const input = byId("chat-input");
    const question = input.value.trim();
    if (!question) return;
    if (!currentThreadId) await createConversation();
    addMessage("user", question);
    input.value = "";
    byId("send-button").disabled = true;
    try {
        const response = await fetch("/chat/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ thread_id: currentThreadId, question }) });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Failed to generate an answer.");
        addMessage("assistant", result.answer, result.sources || []);
        displaySources(result.sources || []);
        await loadConversations();
        highlightActiveConversation(currentThreadId);
    } catch (error) {
        addMessage("assistant", error.message || "Failed to contact the server.");
    } finally {
        byId("send-button").disabled = false;
        input.focus();
    }
}

function initialiseChat() {
    byId("upload-button").addEventListener("click", () => byId("file-input").click());
    byId("file-input").addEventListener("change", uploadDocument);
    byId("new-chat-button").addEventListener("click", () => createConversation().catch((error) => alert(error.message)));
    byId("send-button").addEventListener("click", sendMessage);
    byId("chat-input").addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); }
    });
    loadConversations();
    loadDocuments().catch(() => {});
}

if (isChatPage()) initialiseChat();
