(function () {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }

  function openModal(id) {
    const modal = document.getElementById(id || "pageModal") || document.getElementById("patientModal");
    if (!modal) return;
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
  }

  function closeModal(id) {
    const modal = document.getElementById(id || "pageModal") || document.getElementById("patientModal");
    if (!modal) return;
    modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
  }

  async function fetchRecord(url) {
    const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    const payload = await response.json();
    if (!response.ok || payload.ok === false) throw payload;
    return payload;
  }

  function showToast(message, type) {
    let wrap = document.getElementById("dashboardToastWrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.id = "dashboardToastWrap";
      wrap.className = "fixed right-4 top-4 z-[70] space-y-2";
      document.body.appendChild(wrap);
    }
    const toast = document.createElement("div");
    toast.className = `rounded-2xl border px-4 py-3 text-sm font-semibold shadow-xl ${type === "error" ? "border-red-200 bg-red-50 text-red-700" : "border-green-200 bg-green-50 text-green-700"}`;
    toast.textContent = message;
    wrap.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
  }

  function fillForm(form, data) {
    Object.entries(data || {}).forEach(([name, value]) => {
      const fields = form.elements[name];
      if (!fields) return;
      if (fields.length && fields[0] && fields[0].type === "checkbox") {
        const selected = Array.isArray(value) ? value.map(String) : String(value || "").split(",").map((item) => item.trim());
        Array.from(fields).forEach((field) => { field.checked = selected.includes(field.value); });
      } else if (fields.type === "checkbox") {
        fields.checked = Boolean(value);
      } else {
        fields.value = value == null ? "" : value;
      }
    });
  }

  function clearErrors(form) {
    form.querySelectorAll("[data-field-error]").forEach((node) => { node.textContent = ""; });
    const nonField = form.querySelector("[data-non-field-errors]");
    if (nonField) nonField.textContent = "";
  }

  function renderErrors(form, errors) {
    clearErrors(form);
    Object.entries(errors || {}).forEach(([field, messages]) => {
      const text = Array.isArray(messages) ? messages.join(" ") : String(messages);
      const target = field === "__all__" ? form.querySelector("[data-non-field-errors]") : form.querySelector(`[data-field-error="${field}"]`);
      if (target) target.textContent = text;
    });
  }

  async function submitModalForm(formId, url) {
    const form = document.getElementById(formId);
    const submit = form?.querySelector("button[type='submit']");
    if (!form) return;
    if (submit) {
      submit.disabled = true;
      submit.dataset.originalText = submit.textContent;
      submit.textContent = "Saving...";
    }
    try {
      const response = await fetch(url || form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-CSRFToken": getCookie("csrftoken"), "X-Requested-With": "XMLHttpRequest" },
      });
      const payload = await response.json();
      if (!response.ok || payload.ok === false) {
        renderErrors(form, payload.errors || {});
        showToast(payload.message || "Please correct the form errors.", "error");
        return payload;
      }
      showToast(payload.message || "Saved successfully.", "success");
      if (payload.reload !== false) window.location.reload();
      return payload;
    } finally {
      if (submit) {
        submit.disabled = false;
        submit.textContent = submit.dataset.originalText || "Save";
      }
    }
  }

  function updateTableRow(recordId, data) {
    const row = document.querySelector(`[data-record-id="${recordId}"]`);
    if (!row) return;
    Object.entries(data || {}).forEach(([key, value]) => {
      row.querySelectorAll(`[data-field="${key}"]`).forEach((node) => { node.textContent = value == null ? "" : value; });
    });
  }

  async function confirmDelete(url) {
    if (!window.confirm("Are you sure you want to delete this record?")) return;
    const response = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken"), "X-Requested-With": "XMLHttpRequest" },
    });
    const payload = await response.json();
    if (!response.ok || payload.ok === false) {
      showToast(payload.message || "Could not delete record.", "error");
      return;
    }
    showToast(payload.message || "Deleted successfully.", "success");
    if (payload.reload !== false) window.location.reload();
  }

  window.openModal = openModal;
  window.closeModal = closeModal;
  window.fetchRecord = fetchRecord;
  window.submitModalForm = submitModalForm;
  window.showToast = showToast;
  window.updateTableRow = updateTableRow;
  window.confirmDelete = confirmDelete;
  window.fillCrudForm = fillForm;
  window.renderCrudErrors = renderErrors;
})();
