(function () {
  var CHAT_KEY_STORAGE = "site_openai_api_key";
  var CHAT_MODEL = "gpt-4o-mini";
  var chatConfig = window.CHAT_CONFIG || {};
  var CHAT_API_URL = typeof chatConfig.apiUrl === "string" ? chatConfig.apiUrl.trim() : "";
  var ALLOW_BROWSER_KEY = chatConfig.allowBrowserKey !== false;

  function setYear() {
    var yearEl = document.getElementById("year");
    if (yearEl) yearEl.textContent = String(new Date().getFullYear());
  }

  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  async function loadMarkdownBlocks() {
    var blocks = document.querySelectorAll("[data-md]");

    await Promise.all(
      Array.prototype.map.call(blocks, async function (block) {
        var path = block.getAttribute("data-md");
        if (!path) return;

        try {
          var response = await fetch(path, { cache: "no-cache" });
          if (!response.ok) throw new Error("Failed to fetch " + path);
          var markdown = await response.text();
          block.innerHTML = marked.parse(markdown);
        } catch (error) {
          block.innerHTML =
            "<p><strong>Content unavailable:</strong> " + escapeHtml(path) + "</p>";
          console.error(error);
        }
      })
    );
  }

  function appendChatMessage(messagesEl, role, text) {
    var msg = document.createElement("div");
    msg.className = "chat-msg " + role;
    msg.textContent = text;
    messagesEl.appendChild(msg);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function extractOutputText(payload) {
    if (payload && typeof payload.output_text === "string" && payload.output_text.trim()) {
      return payload.output_text.trim();
    }

    if (!payload || !Array.isArray(payload.output)) return "";

    var parts = [];
    payload.output.forEach(function (item) {
      if (!item || !Array.isArray(item.content)) return;
      item.content.forEach(function (chunk) {
        if (chunk && chunk.type === "output_text" && typeof chunk.text === "string") {
          parts.push(chunk.text);
        }
      });
    });

    return parts.join("\n").trim();
  }

  async function sendToOpenAI(apiKey, history) {
    var response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + apiKey,
      },
      body: JSON.stringify({
        model: CHAT_MODEL,
        input: [
          {
            role: "system",
            content:
              "You are the website owner's AI assistant. Keep responses concise and useful for site visitors.",
          },
        ].concat(
          history.map(function (entry) {
            return { role: entry.role, content: entry.content };
          })
        ),
      }),
    });

    if (!response.ok) {
      var errorText = await response.text();
      throw new Error("OpenAI request failed (" + response.status + "): " + errorText);
    }

    var data = await response.json();
    return extractOutputText(data) || "I could not generate a response.";
  }

  async function sendToBackend(apiUrl, history) {
    var response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: CHAT_MODEL,
        messages: history,
      }),
    });

    if (!response.ok) {
      var errorText = await response.text();
      throw new Error("Backend request failed (" + response.status + "): " + errorText);
    }

    var data = await response.json();
    if (data && typeof data.reply === "string" && data.reply.trim()) {
      return data.reply.trim();
    }
    if (data && typeof data.output_text === "string" && data.output_text.trim()) {
      return data.output_text.trim();
    }
    return "I could not generate a response.";
  }

  function initChatWidget() {
    var toggleBtn = document.getElementById("chat-toggle");
    var popup = document.getElementById("chat-popup");
    var closeBtn = document.getElementById("chat-close");
    var messagesEl = document.getElementById("chat-messages");
    var form = document.getElementById("chat-form");
    var inputEl = document.getElementById("chat-input");
    var submitBtn = form ? form.querySelector("button[type='submit']") : null;
    var settingsEl = popup.querySelector(".chat-settings");
    var apiKeyInput = document.getElementById("chat-api-key");
    var saveKeyBtn = document.getElementById("chat-save-key");
    var clearKeyBtn = document.getElementById("chat-clear-key");
    var statusEl = document.getElementById("chat-status");

    if (!toggleBtn || !popup || !messagesEl || !form || !inputEl || !submitBtn) return;

    var isOpen = false;
    var isSending = false;
    var history = [];

    function readApiKey() {
      return localStorage.getItem(CHAT_KEY_STORAGE) || "";
    }

    function setStatus(text) {
      if (statusEl) statusEl.textContent = text;
    }

    function openPopup() {
      isOpen = true;
      popup.classList.add("is-open");
      popup.setAttribute("aria-hidden", "false");
      inputEl.focus();
    }

    function closePopup() {
      isOpen = false;
      popup.classList.remove("is-open");
      popup.setAttribute("aria-hidden", "true");
    }

    function updateAuthStatus() {
      if (CHAT_API_URL) {
        setStatus("Connected through backend endpoint.");
        return;
      }

      if (!ALLOW_BROWSER_KEY) {
        setStatus("Set CHAT_CONFIG.apiUrl in chat.config.js to enable chat.");
        return;
      }

      var key = readApiKey();
      if (key && key.indexOf("sk-") === 0) {
        setStatus("Connected to OpenAI API.");
      } else {
        setStatus("Paste your OpenAI API key, then click Connect.");
      }
    }

    toggleBtn.addEventListener("click", function () {
      if (isOpen) closePopup();
      else openPopup();
    });

    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        closePopup();
      });
    }

    if (saveKeyBtn && apiKeyInput) {
      saveKeyBtn.addEventListener("click", function () {
        var key = apiKeyInput.value.trim();
        if (!key || key.indexOf("sk-") !== 0) {
          setStatus("Enter a valid OpenAI key starting with sk-.");
          return;
        }
        localStorage.setItem(CHAT_KEY_STORAGE, key);
        apiKeyInput.value = "";
        updateAuthStatus();
      });
    }

    if (clearKeyBtn) {
      clearKeyBtn.addEventListener("click", function () {
        localStorage.removeItem(CHAT_KEY_STORAGE);
        updateAuthStatus();
      });
    }

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      if (isSending) return;

      var text = inputEl.value.trim();
      if (!text) return;

      var apiKey = readApiKey();
      if (!CHAT_API_URL && !ALLOW_BROWSER_KEY) {
        setStatus("Chat disabled: set CHAT_CONFIG.apiUrl in chat.config.js.");
        return;
      }

      if (!CHAT_API_URL && !apiKey) {
        setStatus("Connect your OpenAI API key before sending messages.");
        return;
      }

      inputEl.value = "";
      setStatus("Sending...");
      isSending = true;
      submitBtn.disabled = true;

      appendChatMessage(messagesEl, "user", text);
      history.push({ role: "user", content: text });
      history = history.slice(-10);

      try {
        var answer = CHAT_API_URL
          ? await sendToBackend(CHAT_API_URL, history)
          : await sendToOpenAI(apiKey, history);
        appendChatMessage(messagesEl, "ai", answer);
        history.push({ role: "assistant", content: answer });
        history = history.slice(-10);
        setStatus("Connected.");
      } catch (error) {
        appendChatMessage(
          messagesEl,
          "system",
          "Request failed. Check endpoint/CORS or OpenAI key, quota, and model access."
        );
        setStatus(error && error.message ? error.message : "Request failed.");
      } finally {
        isSending = false;
        submitBtn.disabled = false;
      }
    });

    if (CHAT_API_URL || !ALLOW_BROWSER_KEY) {
      if (settingsEl) settingsEl.style.display = "none";
    }

    appendChatMessage(messagesEl, "system", "Hi. I am your AI assistant.");
    updateAuthStatus();
  }

  setYear();
  loadMarkdownBlocks().finally(initChatWidget);
})();
