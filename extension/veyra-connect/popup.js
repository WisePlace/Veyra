const GOOGLE_URLS = [
  "https://accounts.google.com",
  "https://www.google.com",
  "https://photos.google.com",
  "https://mail.google.com",
];
const VEYRA_INGEST = "http://127.0.0.1:5000/api/ingest";

const msg = document.getElementById("msg");
const sendBtn = document.getElementById("send");
const copyBtn = document.getElementById("copy");
const statusEl = document.getElementById("status");

function say(text, cls = "") { msg.textContent = text; msg.className = cls; }

async function collect() {
  const jar = {};
  for (const url of GOOGLE_URLS) {
    const cookies = await chrome.cookies.getAll({ url });
    for (const c of cookies) jar[c.name] = c.value;
  }
  return jar;
}

async function refreshStatus() {
  try {
    const jar = await collect();
    if (!jar.SAPISID) {
      statusEl.textContent = "Not connected. Log into Google in this browser.";
      statusEl.className = "";
      return;
    }
    let email = null;
    try {
      const r = await fetch(
        "https://accounts.google.com/ListAccounts?gpsia=1&source=ChromiumBrowser&json=standard",
        { credentials: "include" }
      );
      const m = (await r.text()).match(/[\w.+-]+@[\w.-]+\.\w+/);
      if (m) email = m[0];
    } catch (e) {}
    statusEl.textContent = email ? ("Connected as " + email) : "Connected to Google.";
    statusEl.className = "ok";
  } catch (e) {
    statusEl.textContent = "Not connected.";
    statusEl.className = "";
  }
}
document.addEventListener("DOMContentLoaded", refreshStatus);

sendBtn.addEventListener("click", async () => {
  sendBtn.disabled = true;
  say("Collecting cookies…");
  try {
    const jar = await collect();
    if (!jar.SAPISID) {
      say("No Google session found. Are you logged in in this browser?", "err");
      sendBtn.disabled = false;
      return;
    }
    const res = await fetch(VEYRA_INGEST, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cookies: jar }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.ok) {
      say("Sent. Switch back to the Veyra tab.", "ok");
    } else {
      say(data.error || "Veyra rejected the session.", "err");
      sendBtn.disabled = false;
    }
  } catch (e) {
    say("Couldn't reach Veyra at 127.0.0.1:5000. Is it running?", "err");
    sendBtn.disabled = false;
  }
});

copyBtn.addEventListener("click", async () => {
  say("Collecting cookies…");
  try {
    const jar = await collect();
    if (!jar.SAPISID) {
      say("No Google session found. Are you logged in in this browser?", "err");
      return;
    }
    const cookieString = Object.entries(jar).map(([k, v]) => `${k}=${v}`).join("; ");
    await navigator.clipboard.writeText(cookieString);
    say("Session cookie copied to clipboard.", "ok");
  } catch (e) {
    say("Couldn't copy the cookie.", "err");
  }
});
