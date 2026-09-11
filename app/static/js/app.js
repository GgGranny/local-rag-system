let currentThreadId = null;


/* =========================================
   DOM ELEMENTS
   ========================================= */

const conversationList =
    document.getElementById(
        "conversation-list"
    );

const newChatButton =
    document.getElementById(
        "new-chat-button"
    );

const chatMessages =
    document.getElementById(
        "chat-messages"
    );

const chatInput =
    document.getElementById(
        "chat-input"
    );

const sendButton =
    document.getElementById(
        "send-button"
    );

const sourceList =
    document.getElementById(
        "source-list"
    );

const uploadButton =
    document.getElementById("upload-button");
const fileInput =
    document.getElementById("file-input");
if (uploadButton && fileInput) {
    uploadButton.addEventListener(
        "click",
        () => {
            fileInput.click();
        }
    );
    fileInput.addEventListener(
        "change",
        uploadDocument
    );
}

// upload documents
async function uploadDocument() {

    const file =
        fileInput.files[0];

    if (!file) {
        return;
    }

    const formData =
        new FormData();

    formData.append(
        "file",
        file
    );

    uploadButton.disabled = true;

    uploadButton.textContent =
        "Uploading...";

    try {

        /*
         * IMPORTANT:
         *
         * Replace "/documents/upload"
         * below ONLY if your existing
         * upload route uses a different URL.
         */
        const response = await fetch(
            "/documents/upload",
            {
                method: "POST",
                body: formData
            }
        );

        const data =
            await response.json();

        if (!response.ok) {

            throw new Error(
                data.error ||
                "Upload failed."
            );
        }

        console.log(
            "Upload successful:",
            data
        );

        await loadDocuments();

    } catch (error) {

        console.error(
            "Upload failed:",
            error
        );

        alert(
            error.message ||
            "Failed to upload document."
        );

    } finally {

        uploadButton.disabled = false;

        uploadButton.textContent =
            "+ Upload";

        fileInput.value = "";
    }
}

/* =========================================
   LOAD CONVERSATIONS
   ========================================= */

async function loadConversations() {

    const response = await fetch(
        "/chat/conversations"
    );

    if (!response.ok) {
        console.error(
            "Failed to load conversations."
        );
        return;
    }

    const conversations =
        await response.json();

    conversationList.innerHTML = "";

    if (conversations.length === 0) {

        conversationList.innerHTML =
            `<p class="empty-state">
                No conversations yet.
            </p>`;

        return;
    }

    conversations.forEach(
        conversation => {

            const item =
                document.createElement(
                    "div"
                );

            item.className =
                "conversation-item";

            item.textContent =
                conversation.title;

            item.dataset.threadId =
                conversation.thread_id;

            item.addEventListener(
                "click",
                () => {
                    loadConversation(
                        conversation.thread_id
                    );
                }
            );

            conversationList.appendChild(
                item
            );
        }
    );
}


/* =========================================
   CREATE CONVERSATION
   ========================================= */

async function createConversation() {

    const response = await fetch(
        "/chat/conversations",
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json"
            }
        }
    );

    if (!response.ok) {

        alert(
            "Failed to create conversation."
        );

        return null;
    }

    const conversation =
        await response.json();

    currentThreadId =
        conversation.thread_id;

    clearChat();

    await loadConversations();

    return conversation;
}


/* =========================================
   LOAD EXISTING CONVERSATION
   ========================================= */

async function loadConversation(
    threadId
) {

    const response = await fetch(
        `/chat/conversations/${threadId}`
    );

    if (!response.ok) {

        alert(
            "Failed to load conversation."
        );

        return;
    }

    const conversation =
        await response.json();

    currentThreadId =
        conversation.thread_id;

    clearChat();

    conversation.messages.forEach(
        message => {

            addMessage(
                message.role,
                message.content
            );
        }
    );

    highlightActiveConversation(
        threadId
    );
}


/* =========================================
   SEND MESSAGE
   ========================================= */

async function sendMessage() {

    const question =
        chatInput.value.trim();

    if (!question) {
        return;
    }

    if (!currentThreadId) {

        const conversation =
            await createConversation();

        if (!conversation) {
            return;
        }
    }

    addMessage(
        "user",
        question
    );

    chatInput.value = "";

    sendButton.disabled = true;

    try {

        const response =
            await fetch(
                "/chat/ask",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        thread_id:
                            currentThreadId,

                        question:
                            question
                    })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            addMessage(
                "assistant",
                data.error ||
                "Something went wrong."
            );

            return;
        }

        addMessage(
            "assistant",
            data.answer
        );

        displaySources(
            data.sources || []
        );

        await loadConversations();

        highlightActiveConversation(
            currentThreadId
        );

    } catch (error) {

        console.error(error);

        addMessage(
            "assistant",
            "Failed to contact the server."
        );

    } finally {

        sendButton.disabled = false;

        chatInput.focus();
    }
}


/* =========================================
   ADD MESSAGE TO UI
   ========================================= */

function addMessage(
    role,
    content
) {

    const empty =
        document.getElementById(
            "chat-empty"
        );

    if (empty) {
        empty.remove();
    }

    const message =
        document.createElement(
            "div"
        );

    message.className =
        `message message-${role}`;

    const messageContent =
        document.createElement(
            "div"
        );

    messageContent.className =
        "message-content";

    messageContent.textContent =
        content;

    message.appendChild(
        messageContent
    );

    chatMessages.appendChild(
        message
    );

    chatMessages.scrollTop =
        chatMessages.scrollHeight;
}


/* =========================================
   DISPLAY SOURCES
   ========================================= */

function displaySources(
    sources
) {

    sourceList.innerHTML = "";

    if (!sources.length) {

        sourceList.innerHTML =
            `<p class="empty-state">
                No sources found.
            </p>`;

        return;
    }

    sources.forEach(
        source => {

            const item =
                document.createElement(
                    "div"
                );

            item.className =
                "source-item";

            const title =
                document.createElement(
                    "strong"
                );

            title.textContent =
                `${source.citation} ${source.filename
                }`;

            const page =
                document.createElement(
                    "small"
                );

            if (source.page_number) {

                page.textContent =
                    `Page ${source.page_number
                    }`;

            } else {

                page.textContent =
                    "Document source";
            }

            item.appendChild(title);
            item.appendChild(page);

            sourceList.appendChild(
                item
            );
        }
    );
}

// load the documents
async function loadDocuments() {

    const documentList =
        document.getElementById("document-list");

    if (!documentList) {
        return;
    }

    try {

        const response = await fetch(
            "/documents/mine"
        );

        const documents = await response.json();

        if (!response.ok) {
            throw new Error(
                documents.error ||
                "Failed to load documents."
            );
        }

        documentList.innerHTML = "";

        if (documents.length === 0) {

            documentList.innerHTML = `
                <p class="empty-state">
                    No documents yet.
                </p>
            `;

            return;
        }

        documents.forEach(document => {

            const item =
                document.createElement("div");

            item.className =
                "document-item";

            item.innerHTML = `
                <div class="document-info">

                    <div class="document-name">
                        📄 ${escapeHtml(
                document.filename
            )}
                    </div>

                    <div class="document-status status-${document.status.toLowerCase()}">
                        ${document.status}
                    </div>

                </div>
            `;

            documentList.appendChild(item);
        });

    } catch (error) {

        console.error(
            "Failed to load documents:",
            error
        );

        documentList.innerHTML = `
            <p class="empty-state">
                Failed to load documents.
            </p>
        `;
    }
}

/* =========================================
   CLEAR CHAT
   ========================================= */

function clearChat() {

    chatMessages.innerHTML =
        `<div
            id="chat-empty"
            class="chat-empty"
        >
            <h1>Document Assistant</h1>

            <p>
                Ask questions about your
                uploaded documents.
            </p>
        </div>`;

    sourceList.innerHTML =
        `<p class="empty-state">
            Sources will appear here.
        </p>`;
}


/* =========================================
   ACTIVE CONVERSATION
   ========================================= */

function highlightActiveConversation(
    threadId
) {

    document
        .querySelectorAll(
            ".conversation-item"
        )
        .forEach(item => {

            item.classList.toggle(
                "active",
                item.dataset.threadId ===
                threadId
            );
        });
}


/* =========================================
   EVENT LISTENERS
   ========================================= */

newChatButton.addEventListener(
    "click",
    createConversation
);

sendButton.addEventListener(
    "click",
    sendMessage
);

chatInput.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();
        }
    }
);


/* =========================================
   INITIAL LOAD
   ========================================= */

loadConversations();
loadDocuments();