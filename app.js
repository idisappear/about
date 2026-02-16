(function () {
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

  setYear();
  loadMarkdownBlocks();
})();
