const userId = document.body.dataset.userId;
const patientId = document.body.dataset.patientId;
const toast = document.querySelector("#toast");

function notify(message, isError = false) {
  toast.textContent = message;
  toast.className = isError ? "show error" : "show";
  window.setTimeout(() => { toast.className = ""; }, 3200);
}

async function api(path, method, payload) {
  const response = await fetch(path, {
    method,
    headers: {"Content-Type": "application/json", "X-User-ID": userId},
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "Request failed");
  return result;
}

document.querySelectorAll("[data-highlight-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await api(`/api/highlights/${button.dataset.highlightId}/action`, "POST", {action: button.dataset.highlightAction});
      window.location.reload();
    } catch (error) { notify(error.message, true); }
  });
});

document.querySelectorAll("[data-comment-id]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await api(`/api/comments/${button.dataset.commentId}`, "PATCH", {resolved: button.dataset.resolved === "true"});
      window.location.reload();
    } catch (error) { notify(error.message, true); }
  });
});

document.querySelectorAll(".comment-form").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const assignee = data.get("assigned_to_id");
    try {
      await api(`/api/entries/${form.dataset.entryId}/comments`, "POST", {
        body: data.get("body"),
        assigned_to_id: assignee ? Number(assignee) : null,
        mention_user_id: assignee ? Number(assignee) : null,
      });
      window.location.reload();
    } catch (error) { notify(error.message, true); }
  });
});

const entryForm = document.querySelector("#entry-form");
if (entryForm) entryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(entryForm);
  try {
    await api(`/api/patients/${patientId}/entries`, "POST", {
      entry_type: entryForm.dataset.entryType,
      section_key: data.get("section_key"),
      title: data.get("title"),
      content: data.get("content"),
      visibility: data.get("patient_visible") ? "patient" : "internal",
    });
    window.location.reload();
  } catch (error) { notify(error.message, true); }
});

const scribeForm = document.querySelector("#scribe-form");
if (scribeForm) scribeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(scribeForm);
  try {
    const result = await api(`/api/patients/${patientId}/ai-scribe`, "POST", {
      interaction_type: scribeForm.dataset.interactionType,
      session_id: data.get("session_id"),
      raw_text: data.get("raw_text"),
    });
    notify(`Draft created. Redacted ${Object.values(result.redaction_counts).reduce((a, b) => a + b, 0)} identifiers.`);
    window.setTimeout(() => window.location.reload(), 900);
  } catch (error) { notify(error.message, true); }
});

