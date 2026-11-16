const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("message");
const student = document.getElementById("student");
const sessionEl = document.getElementById("session-id");
const toolsEl = document.getElementById("last-tools");

function add(text, cls, tools) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.textContent = text;
  if (tools && tools.length) {
    const t = document.createElement("div");
    t.className = "tools";
    t.textContent = "Tools used: " + tools.map(x => `${x.name} (${x.status})`).join(", ");
    div.appendChild(t);
  }
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  add(message, "you");
  input.value = "";
  const btn = form.querySelector("button");
  btn.disabled = true;
  add("CampusMate is thinking...", "bot");
  const thinking = chat.lastChild;
  try {
    const res = await fetch("/api/chat", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message, student_id: student.value}),
    });
    const data = await res.json();
    thinking.remove();
    if (!res.ok || data.error) { add(data.error || `Error ${res.status}`, "err"); return; }
    add(data.result, "bot", data.tools_used);
    sessionEl.textContent = data.session_id || "";
    toolsEl.textContent = JSON.stringify({tools_used: data.tools_used, usage: data.usage, model: data.model}, null, 2);
  } catch (err) {
    thinking.remove();
    add("Could not reach the CampusMate server. Is `python projects/web/app.py` still running?", "err");
  } finally {
    btn.disabled = false;
    input.focus();
  }
});

async function newSession() {
  await fetch("/api/new-session", {method: "POST", headers: {"Content-Type": "application/json"},
                                   body: JSON.stringify({student_id: student.value})});
  chat.innerHTML = "";
  add(`New session for ${student.value}. Short-term memory is empty; long-term memory still knows you.`, "bot");
  sessionEl.textContent = "(new session starts with your next message)";
}
document.getElementById("new-session").addEventListener("click", newSession);
student.addEventListener("change", () => {
  chat.innerHTML = "";
  add(`Now chatting as ${student.value}.`, "bot");
});
