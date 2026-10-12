const $ = (id) => document.getElementById(id);
const analyzeButton = $("analyze");

detectCurrentPage();

async function detectCurrentPage() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url) {
      $("videoUrl").value = tab.url;
      $("status").textContent = "Current page link detected. Ready to analyze.";
    }
  } catch (err) {
    $("status").textContent = "Enter a video link to analyze.";
  }
}

analyzeButton.addEventListener("click", async () => {
  const url = $("videoUrl").value.trim();
  if (!url) {
    $("status").textContent = "Paste a YouTube video URL first.";
    return;
  }
  analyzeButton.disabled = true;
  $("result").hidden = true;
  $("status").textContent = "Fetching captions and analyzing the transcript…";
  try {
    const response = await fetch("http://127.0.0.1:8765/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Analysis failed.");
    $("videoTitle").textContent = data.title || "Video analysis";
    $("notTutorial").hidden = data.is_tutorial !== false;
    fillList("technologies", data.technologies || []);
    fillList("topics", data.topics || []);
    $("project").textContent = data.project || "The transcript did not clearly identify a project.";
    $("notes").textContent = data.summary || "";
    $("transcript").textContent = data.transcript || "";
    $("result").hidden = false;
    $("status").textContent = `Analysis complete · ${data.transcript_words || 0} transcript words`;
  } catch (err) {
    $("status").textContent = err.message + " Make sure the local backend is running; see README.";
  } finally {
    analyzeButton.disabled = false;
  }
});

function fillList(id, values) {
  const list = $(id);
  list.replaceChildren();
  if (!values.length) {
    const li = document.createElement("li");
    li.textContent = "No clear items detected.";
    list.appendChild(li);
    return;
  }
  values.forEach(value => {
    const li = document.createElement("li");
    li.textContent = value;
    list.appendChild(li);
  });
}