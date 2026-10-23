/* =========================================================
   LenSight AI — Frontend Application
   ========================================================= */

(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const API = "/analyze";

  let selectedFile = null;
  let objectUrl = null;
  let reportText = "";
  let reportCount = 0;

  function toast(msg) {
    const t = $("toast");
    t.textContent = msg;
    t.style.display = "block";
    clearTimeout(toast._t);
    toast._t = setTimeout(() => (t.style.display = "none"), 4000);
  }

  function fmtBytes(n) {
    if (n < 1024) return n + " B";
    if (n < 1048576) return (n / 1024).toFixed(1) + " KB";
    return (n / 1048576).toFixed(2) + " MB";
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function mediaKind(file) {
    if (file.type.startsWith("image/")) return "image";
    if (file.type.startsWith("video/")) return "video";
    if (file.type.startsWith("audio/")) return "audio";
    // Fallback by extension
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    const audioExts = ["mp3", "wav", "ogg", "flac", "m4a", "aac", "webm"];
    if (audioExts.includes(ext)) return "audio";
    return "unknown";
  }

  // ── Progress Bar ─────────────────────────────────────────

  function showProgress(pct, text) {
    $("progressSection").classList.remove("hidden");
    $("progressBar").style.width = pct + "%";
    $("progressText").textContent = text;
  }

  function hideProgress() {
    $("progressSection").classList.add("hidden");
    $("progressBar").style.width = "0%";
  }

  // ── Preview ──────────────────────────────────────────────

  function resetPreview() {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = null;

    const img = $("imagePreview");
    img.style.display = "none";
    img.removeAttribute("src");

    const vid = $("videoPreview");
    vid.style.display = "none";
    vid.removeAttribute("src");
    vid.load();

    const aud = $("audioPreview");
    if (aud) {
      aud.style.display = "none";
      aud.removeAttribute("src");
      aud.load();
    }

    $("fileMeta").style.display = "none";
  }

  function showPreview(file, kind) {
    objectUrl = URL.createObjectURL(file);
    if (kind === "image") {
      $("imagePreview").src = objectUrl;
      $("imagePreview").style.display = "block";
    } else if (kind === "video") {
      $("videoPreview").src = objectUrl;
      $("videoPreview").style.display = "block";
    } else if (kind === "audio") {
      const aud = $("audioPreview");
      aud.src = objectUrl;
      aud.style.display = "block";
    }
  }

  // ── File Selection ───────────────────────────────────────

  function chooseFile(file) {
    if (!file) return;

    const kind = mediaKind(file);
    if (kind === "unknown") {
      toast("Unsupported file type. Please select an image, video, or audio file.");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      toast("File exceeds the 20 MB limit.");
      return;
    }

    selectedFile = file;
    resetPreview();
    showPreview(file, kind);

    $("fileMeta").style.display = "flex";
    $("fileName").textContent = file.name;
    $("fileSub").textContent =
      kind.toUpperCase() +
      " · " +
      fmtBytes(file.size) +
      " · " +
      (file.type || "unknown MIME");

    const badgeMap = { image: "IMG", video: "VID", audio: "AUD" };
    $("fileBadge").textContent = badgeMap[kind] || "FILE";

    const modeMap = {
      image: "Image Ready",
      video: "Video Ready",
      audio: "Audio Ready",
    };
    $("modeStat").textContent = modeMap[kind] || "Ready";

    $("analyzeBtn").textContent = "Run forensic analysis →";
    $("analyzeBtn").disabled = false;
    $("result").style.display = "none";
    hideProgress();

    const stageMsg = {
      image: "Image staged. Click 'Run forensic analysis' to send to Gemini.",
      video: "Video staged. 5 frames from the first 5s will be extracted and analyzed.",
      audio: "Audio staged. Gemini will analyze speech patterns to detect AI generation.",
    };
    toast(stageMsg[kind]);
  }

  function clearFile() {
    selectedFile = null;
    $("fileInput").value = "";
    resetPreview();
    hideProgress();
    $("modeStat").textContent = "Ready";
    $("analyzeBtn").textContent = "Run analysis →";
    $("analyzeBtn").disabled = false;
    $("result").style.display = "none";
  }

  // ── Drop Zone ────────────────────────────────────────────

  const dz = $("dropZone");
  dz.addEventListener("dragover", (e) => {
    e.preventDefault();
    dz.classList.add("drag");
  });
  dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
  dz.addEventListener("drop", (e) => {
    e.preventDefault();
    dz.classList.remove("drag");
    chooseFile(e.dataTransfer.files[0]);
  });

  $("browseBtn").onclick = () => $("fileInput").click();
  $("fileInput").onchange = (e) => chooseFile(e.target.files[0]);
  $("removeFile").onclick = clearFile;

  // ── Backend Analysis ─────────────────────────────────────

  $("analyzeBtn").onclick = () => {
    if (!selectedFile) {
      toast("Choose an image, video, or audio file first.");
      return;
    }
    runAnalysis(selectedFile);
  };

  async function runAnalysis(file) {
    const kind = mediaKind(file);
    $("analyzeBtn").disabled = true;

    try {
      showProgress(10, "Uploading file to backend...");

      const form = new FormData();
      form.append("file", file);

      const uploadMsg = {
        image: "Sending image to Gemini...",
        video: "Extracting frames and sending to Gemini...",
        audio: "Sending audio to Gemini multimodal analyzer...",
      };
      showProgress(30, uploadMsg[kind] || "Sending to Gemini...");

      const resp = await fetch(API, { method: "POST", body: form });
      showProgress(80, "Processing response...");

      let data;
      try {
        data = await resp.json();
      } catch (_) {
        throw new Error("Server returned non-JSON (status " + resp.status + ").");
      }

      if (!resp.ok) {
        const detail =
          typeof data.details === "string"
            ? data.details
            : data.details
            ? JSON.stringify(data.details)
            : "";
        throw new Error(
          (data.error || "Unknown error") + (detail ? ": " + detail : "")
        );
      }

      showProgress(100, "Complete!");

      // Update status pills
      setPill("geminiPill", "CONNECTED", true);
      if (kind === "video") setPill("videoPill", "ACTIVE", true);
      if (kind === "audio" && $("audioPill")) setPill("audioPill", "ACTIVE", true);

      renderResults(data, file);
    } catch (err) {
      console.error(err);
      toast("Analysis failed: " + err.message);
      hideProgress();
    } finally {
      $("analyzeBtn").disabled = false;
      $("analyzeBtn").textContent = "Run forensic analysis →";
    }
  }

  function setPill(id, text, ok) {
    const el = $(id);
    if (!el) return;
    el.textContent = text;
    el.className = ok ? "pill ok" : "pill";
  }

  // ── Result Rendering ─────────────────────────────────────

  function renderResults(data, file) {
    const kind = data.media_type || mediaKind(file);

    $("result").style.display = "block";
    $("resultSubtitle").textContent = file.name;

    const tagMap = {
      image: "IMAGE REPORT",
      video: "VIDEO REPORT",
      audio: "AUDIO REPORT",
    };
    $("resultTag").textContent = tagMap[kind] || "REPORT";

    $("verdictTitle").textContent = data.assessment || "Analysis complete";
    $("verdictDesc").textContent = data.summary || "";

    // Risk pill
    const pill = $("verdictPill");
    const risk = (data.risk_level || "MEDIUM").toUpperCase();
    pill.textContent = risk + " RISK";
    const riskColors = {
      HIGH: { border: "var(--red)", color: "var(--red)", bg: "#2b1319" },
      MEDIUM: { border: "var(--amber)", color: "var(--amber)", bg: "#282116" },
      LOW: { border: "var(--green)", color: "var(--green)", bg: "#14251f" },
    };
    const rc = riskColors[risk] || riskColors.MEDIUM;
    pill.style.borderColor = rc.border;
    pill.style.color = rc.color;
    pill.style.background = rc.bg;

    // Metrics
    const confidence =
      data.confidence !== undefined && data.confidence !== null
        ? data.confidence + "%"
        : "—";
    $("confidence").textContent = confidence;

    const indicators = Array.isArray(data.indicators) ? data.indicators : [];
    $("checksCount").textContent = indicators.length + " flagged";

    const typeLabel = { image: "Image", video: "Video", audio: "Audio" };
    $("mediaTypeBadge").textContent = typeLabel[kind] || "—";

    // Frames metric (video only)
    const framesMetric = $("framesMetric");
    if (data.frames_analyzed && data.frames_analyzed > 0) {
      framesMetric.style.display = "";
      let label = data.frames_analyzed + " frames";
      if (data.frame_timestamps) {
        label += " (" + data.frame_timestamps.map((t) => t + "s").join(", ") + ")";
      }
      $("framesCount").textContent = label;
    } else {
      framesMetric.style.display = "none";
    }

    renderIndicators(indicators);

    const limitations =
      Array.isArray(data.limitations) && data.limitations.length
        ? data.limitations
        : ["No limitations were returned."];
    const limHtml = limitations
      .map((l) => "<li>" + escapeHtml(l) + "</li>")
      .join("");

    $("reportNote").innerHTML =
      "<strong>Forensic Summary:</strong> " +
      escapeHtml(data.summary || "N/A") +
      "<strong>Limitations:</strong>" +
      '<ul style="margin:6px 0 0;padding-left:18px">' +
      limHtml +
      "</ul>";

    reportText = buildTextReport(data, file, kind, indicators, limitations, confidence);

    finishReport();
    setTimeout(() => {
      hideProgress();
      $("result").scrollIntoView({ behavior: "smooth", block: "start" });
    }, 400);
  }

  function renderIndicators(indicators) {
    if (!indicators.length) {
      $("checksList").innerHTML =
        '<div class="check"><span>No suspicious elements detected.</span></div>';
      return;
    }
    $("checksList").innerHTML = indicators
      .map((ind) => {
        let c = "var(--green)";
        if (ind.severity === "HIGH") c = "var(--red)";
        else if (ind.severity === "MEDIUM") c = "var(--amber)";
        return (
          '<div class="check" style="flex-direction:column;align-items:flex-start;gap:4px;padding:12px 0">' +
          '<div style="display:flex;justify-content:space-between;width:100%">' +
          '<span style="color:var(--text);font-weight:bold">' +
          escapeHtml(ind.name) +
          "</span>" +
          '<b style="color:' +
          c +
          ';font-size:11px">' +
          escapeHtml(ind.severity) +
          " SEVERITY</b></div>" +
          '<span style="font-size:12px;color:var(--muted)">' +
          escapeHtml(ind.explanation) +
          "</span></div>"
        );
      })
      .join("");
  }

  function buildTextReport(data, file, kind, indicators, limitations, confidence) {
    let t = "LENSIGHT AI - MEDIA FORENSIC REPORT\n";
    t += "=========================================\n";
    t += "FILE: " + file.name + "\n";
    t += "TYPE: " + kind.toUpperCase() + "\n";
    t += "DATE: " + new Date().toUTCString() + "\n";
    t += "ASSESSMENT: " + (data.assessment || "N/A") + "\n";
    t += "RISK LEVEL: " + (data.risk_level || "N/A") + "\n";
    t += "CONFIDENCE: " + confidence + "\n";
    if (data.frames_analyzed) {
      t += "FRAMES ANALYZED: " + data.frames_analyzed + "\n";
      if (data.frame_timestamps) {
        t +=
          "FRAME TIMESTAMPS: " +
          data.frame_timestamps.map((ts) => ts + "s").join(", ") +
          "\n";
      }
    }
    t += "=========================================\n\n";
    t += "SUMMARY:\n" + (data.summary || "N/A") + "\n\n";
    t += "INDICATORS DETECTED:\n";
    if (!indicators.length) {
      t += "  (none)\n";
    } else {
      indicators.forEach((ind, i) => {
        t += "[" + (i + 1) + "] " + ind.name + " (Severity: " + ind.severity + ")\n";
        t += "    " + ind.explanation + "\n";
      });
    }
    t += "\nLIMITATIONS:\n";
    limitations.forEach((l) => {
      t += "- " + l + "\n";
    });
    t += "\n=========================================\n";
    t += "REPORT CYBERCRIME IN INDIA:\n";
    t += "- National Helpline: 1930 (Toll-free, 24/7)\n";
    t += "- Online Portal: https://cybercrime.gov.in\n";
    t += "- Emergency: 112\n";
    return t;
  }

  // ── Report Management ────────────────────────────────────

  function finishReport() {
    reportCount++;
    $("reportStat").textContent =
      reportCount + " report" + (reportCount === 1 ? "" : "s");
    $("reportHistory").innerHTML =
      '<div style="padding:14px;border:1px solid var(--line);border-radius:10px;background:#0b121e">' +
      '<b style="color:var(--text)">Latest report · ' +
      new Date().toLocaleTimeString() +
      "</b>" +
      '<p style="margin:5px 0 0">Report available in the Media analysis workspace. Use Export to save.</p>' +
      "</div>";
  }

  $("downloadReport").onclick = () => {
    if (!reportText) {
      toast("Run an analysis first.");
      return;
    }
    const blob = new Blob([reportText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "LenSight-report.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  $("newCase").onclick = () => {
    clearFile();
    $("result").style.display = "none";
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // ── Navigation ───────────────────────────────────────────

  document.querySelectorAll(".nav").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll(".nav").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      const v = btn.dataset.view;

      $("analysisView").classList.toggle("hidden", v !== "analysis");
      $("reportView").classList.toggle("hidden", v !== "report");
      $("guideView").classList.toggle("hidden", v !== "guide");
      $("cybercrimeView").classList.toggle("hidden", v !== "cybercrime");

      window.scrollTo({ top: 0, behavior: "smooth" });
    };
  });

  // ── Clock ────────────────────────────────────────────────

  function tick() {
    const d = new Date();
    $("clock").textContent =
      d.toLocaleDateString() +
      " · " +
      d.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
  }
  tick();
  setInterval(tick, 1000);

  $("caseId").textContent =
    "DFS-" +
    new Date().toISOString().slice(0, 10).replaceAll("-", "") +
    "-01";
})();