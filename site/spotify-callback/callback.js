"use strict";

const callbackUrl = window.location.href;
const parameters = new URLSearchParams(window.location.search);
const callbackSection = document.querySelector("#callback");
const callbackField = document.querySelector("#callback-url");
const copyButton = document.querySelector("#copy");
const copyStatus = document.querySelector("#copy-status");
const heading = document.querySelector("#heading");
const status = document.querySelector("#status");

const hasCode = parameters.has("code");
const hasError = parameters.has("error");

if (hasCode || hasError) {
  callbackField.value = callbackUrl;
  callbackSection.hidden = false;
  if (hasError) {
    heading.textContent = "Authorization was not completed";
    status.textContent = "Paste the URL into PlayQuick so it can report the Spotify error.";
    status.classList.add("error");
  } else {
    heading.textContent = "Authorization received";
    status.textContent = "Copy the full URL below and paste it into the waiting terminal.";
    status.classList.add("success");
  }
  window.history.replaceState(null, "", window.location.pathname);
} else {
  heading.textContent = "No authorization response found";
  status.textContent = "Start the login flow with `playquick spotify login` first.";
  status.classList.add("error");
}

async function copyCallback() {
  try {
    await navigator.clipboard.writeText(callbackField.value);
  } catch (_error) {
    callbackField.focus();
    callbackField.select();
    document.execCommand("copy");
  }
  copyStatus.textContent = "Copied. Return to the terminal and paste it into PlayQuick.";
}

copyButton.addEventListener("click", copyCallback);
