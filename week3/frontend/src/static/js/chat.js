// frontend/src/static/js/chat.js
pdfjsLib.GlobalWorkerOptions.workerSrc =
  "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

const chatHistory = document.getElementById("chat-history");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const statusLine = document.getElementById("status-line");

const uploadBtn = document.getElementById("upload-btn");
const pdfInput = document.getElementById("pdf-input");
const fileChipArea = document.getElementById("file-chip-area");
const fileChipName = document.getElementById("file-chip-name");
const fileChipRemove = document.getElementById("file-chip-remove");

let attachedPdfText = null;
let attachedPdfName = null;

// Markdown rendering function
function renderMarkdown(text) {
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            sanitize: false,
        });
        return marked.parse(text);
    }
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
}

function appendBubble(text, role) {
    const bubble = document.createElement("div");
    bubble.classList.add("chat-bubble", role);
    
    if (role === 'bot' || role === 'system') {
        bubble.innerHTML = renderMarkdown(text);
    } else {
        bubble.textContent = text;
    }
    
    chatHistory.appendChild(bubble);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return bubble;
}

function setStatus(text, isError = false) {
    statusLine.textContent = text;
    statusLine.classList.toggle("text-danger", isError);
}

function clearAttachment() {
    attachedPdfText = null;
    attachedPdfName = null;
    pdfInput.value = "";
    fileChipArea.classList.add("d-none");
}

uploadBtn.addEventListener("click", () => pdfInput.click());
fileChipRemove.addEventListener("click", clearAttachment);

pdfInput.addEventListener("change", async () => {
    const file = pdfInput.files[0];
    if (!file) return;

    setStatus(`Reading ${file.name}...`);
    try {
        attachedPdfText = await extractTextFromPdf(file);
        attachedPdfName = file.name;
        fileChipName.textContent = file.name;
        fileChipArea.classList.remove("d-none");
        setStatus(`Attached ${file.name} (${attachedPdfText.length} characters extracted).`);
    } catch (err) {
        console.error(err);
        setStatus(`Could not read ${file.name}: ${err.message}`, true);
        clearAttachment();
    }
});

async function extractTextFromPdf(file) {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

    let fullText = "";
    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
        const page = await pdf.getPage(pageNum);
        const textContent = await page.getTextContent();
        const pageText = textContent.items.map((item) => item.str).join(" ");
        fullText += pageText + "\n\n";
    }
    return fullText.trim();
}

chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = messageInput.value.trim();
    if (!message && !attachedPdfText) {
        setStatus("Type a message or attach a PDF first.", true);
        return;
    }

    const userDisplay = attachedPdfText
        ? `${message ? message + "\n\n" : ""}[Attached: ${attachedPdfName}]`
        : message;
    appendBubble(userDisplay, "user");

    const payload = {
        message: message || "Please analyze my resume",
        pdf_content: attachedPdfText,
        pdf_name: attachedPdfName,
    };

    messageInput.value = "";
    clearAttachment();
    setStatus("Sending to backend...");

    try {
        const response = await fetch('/api/chat', {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Backend returned ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        const replyText = data.response || "No response from backend";
        
        appendBubble(replyText, "bot");
        
        if (data.skill_gaps && data.skill_gaps.length > 0) {
            const gapsText = "### Skills to work on:\n\n" + 
                data.skill_gaps.map(gap => `- ${gap}`).join("\n");
            const gapBubble = document.createElement("div");
            gapBubble.classList.add("chat-bubble", "bot");
            gapBubble.style.fontSize = "0.9em";
            gapBubble.style.opacity = "0.9";
            gapBubble.style.backgroundColor = "#f0f0f0";
            gapBubble.innerHTML = renderMarkdown(gapsText);
            chatHistory.appendChild(gapBubble);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
        
        setStatus("");

    } catch (err) {
        console.error("Error:", err);
        appendBubble(`Error: ${err.message}`, "error");
        setStatus("Failed to send. Is the backend running?", true);
    }
});