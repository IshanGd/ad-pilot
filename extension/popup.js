"use strict";

const { API_BASE, WEB_BASE } = window.ADPILOT_CONFIG;

const fileInput = document.getElementById("file");
const drop = document.getElementById("drop");
const dropText = document.getElementById("drop-text");
const phoneInput = document.getElementById("phone");
const goButton = document.getElementById("go");
const statusEl = document.getElementById("status");

let chosenFile = null;

function setStatus(message, isError = false) {
  statusEl.textContent = message || "";
  statusEl.hidden = !message;
  statusEl.classList.toggle("error", Boolean(isError));
}

function looksLikeCsv(name) {
  return /\.(csv|tsv|txt)$/i.test(name || "");
}

function chooseFile(file) {
  if (!file) return;
  if (!looksLikeCsv(file.name)) {
    setStatus("Please choose the .csv file you exported from Google Ads.", true);
    return;
  }
  chosenFile = file;
  dropText.textContent = file.name;
  drop.classList.add("has-file");
  goButton.disabled = false;
  setStatus("");
}

drop.addEventListener("click", () => fileInput.click());
drop.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener("change", () => chooseFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((evt) =>
  drop.addEventListener(evt, (e) => {
    e.preventDefault();
    drop.classList.add("dragover");
  }),
);
["dragleave", "drop"].forEach((evt) =>
  drop.addEventListener(evt, (e) => {
    e.preventDefault();
    drop.classList.remove("dragover");
  }),
);
drop.addEventListener("drop", (e) => chooseFile(e.dataTransfer.files[0]));

goButton.addEventListener("click", async () => {
  if (!chosenFile) return;
  goButton.disabled = true;
  setStatus("Analysing your report…");

  const form = new FormData();
  form.append("file", chosenFile);

  try {
    const res = await fetch(`${API_BASE}/api/campaign/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      let detail = `Upload failed (${res.status}).`;
      try {
        const body = await res.json();
        if (typeof body.detail === "string") detail = body.detail;
      } catch (_) {
        /* keep default */
      }
      throw new Error(detail);
    }
    const { account_id } = await res.json();

    let url = `${WEB_BASE}/audit/${account_id}`;
    const phone = phoneInput.value.trim();
    if (phone) url += `?phone=${encodeURIComponent(phone)}`;

    await chrome.tabs.create({ url });
    window.close();
  } catch (err) {
    setStatus(err.message || "Something went wrong. Try again.", true);
    goButton.disabled = false;
  }
});
