const API_BASE_URL = "http://localhost:5000";

const form = document.getElementById("crawl-form");
const urlInput = document.getElementById("seed-url");
const depthInput = document.getElementById("crawl-depth");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status-message");

const statsSection = document.getElementById("stats-section");
const graphSection = document.getElementById("graph-section");
const top10Section = document.getElementById("top10-section");
const top10Tbody = document.getElementById("top10-tbody");

let networkInstance = null;

function setStatus(message, type = "info") {
  statusEl.textContent = message;
  statusEl.className = `status-message status-${type}`;
  statusEl.classList.remove("hidden");
}

function hideStatus() {
  statusEl.classList.add("hidden");
}

function shortenLabel(url, maxLen = 28) {
  try {
    const parsed = new URL(url);
    const shortPath = parsed.pathname === "/" ? "" : parsed.pathname;
    const text = `${parsed.hostname}${shortPath}`;
    return text.length > maxLen ? `${text.slice(0, maxLen)}…` : text;
  } catch {
    return url.length > maxLen ? `${url.slice(0, maxLen)}…` : url;
  }
}

function renderStats(stats) {
  document.getElementById("stat-crawled").textContent = stats.crawled_pages ?? 0;
  document.getElementById("stat-nodes").textContent = stats.total_nodes ?? 0;
  document.getElementById("stat-edges").textContent = stats.total_edges ?? 0;
  document.getElementById("stat-errors").textContent = stats.error_count ?? 0;
  statsSection.classList.remove("hidden");
}

function renderGraph(graphData, seedUrl) {
  const container = document.getElementById("graph-container");
  const rawNodes = graphData.nodes || [];
  const rawEdges = graphData.edges || [];

  const nodes = new vis.DataSet(
    rawNodes.map((node) => {
      const isSeed = node.id === seedUrl;
      const isTop10 = Boolean(node.is_top_10);

      let bgColor = "#3b82f6";
      let borderColor = "#1d4ed8";
      if (isSeed) {
        bgColor = "#dc2626";
        borderColor = "#991b1b";
      } else if (isTop10) {
        bgColor = "#16a34a";
        borderColor = "#166534";
      }

      return {
        id: node.id,
        label: shortenLabel(node.label),
        title:
          `URL: ${node.id}\n` +
          `PageRank: ${node.pagerank}\n` +
          `Depth: ${node.depth}\n` +
          `In-Degree: ${node.in_degree} | Out-Degree: ${node.out_degree}`,
        value: node.size || 14,
        color: {
          background: bgColor,
          border: borderColor,
          highlight: {
            background: "#f59e0b",
            border: "#b45309",
          },
        },
        font: {
          size: 12,
          color: "#1f2937",
        },
      };
    })
  );

  const edges = new vis.DataSet(
    rawEdges.map((edge, idx) => ({
      id: `e_${idx}`,
      from: edge.from,
      to: edge.to,
      arrows: {
        to: { enabled: true, scaleFactor: 0.6 },
      },
      color: {
        color: "#94a3b8",
        highlight: "#2563eb",
      },
      smooth: {
        type: "continuous",
      },
    }))
  );

  // Sesuaikan stabilisasi fisika jika jumlah node cukup banyak agar tidak berat di browser
  const manyNodes = rawNodes.length > 120;

  const options = {
    nodes: {
      shape: "dot",
      scaling: {
        min: 10,
        max: 34,
      },
    },
    edges: {
      width: 1,
    },
    physics: {
      enabled: true,
      solver: "forceAtlas2Based",
      forceAtlas2Based: {
        gravitationalConstant: manyNodes ? -35 : -55,
        springLength: manyNodes ? 110 : 140,
        avoidOverlap: 0.2,
      },
      stabilization: {
        enabled: true,
        iterations: manyNodes ? 80 : 150,
        updateInterval: 25,
      },
    },
    interaction: {
      hover: true,
      tooltipDelay: 120,
      navigationButtons: true,
    },
  };

  if (networkInstance) {
    networkInstance.destroy();
    networkInstance = null;
  }

  networkInstance = new vis.Network(container, { nodes, edges }, options);
  graphSection.classList.remove("hidden");
}

function renderTop10(top10List) {
  top10Tbody.innerHTML = "";

  if (!top10List || top10List.length === 0) {
    top10Tbody.innerHTML = `<tr><td colspan="6">Tidak ada data peringkat yang tersedia.</td></tr>`;
    top10Section.classList.remove("hidden");
    return;
  }

  top10List.forEach((item) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="rank-badge">#${item.rank}</span></td>
      <td class="url-cell"><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.url)}</a></td>
      <td><strong>${Number(item.pagerank).toFixed(6)}</strong></td>
      <td>${item.depth}</td>
      <td>${item.in_degree}</td>
      <td>${item.out_degree}</td>
    `;
    top10Tbody.appendChild(tr);
  });

  top10Section.classList.remove("hidden");
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const url = urlInput.value.trim();
  const depth = parseInt(depthInput.value, 10);

  if (!url) {
    setStatus("Silakan masukkan link website terlebih dahulu.", "error");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Memproses...";
  setStatus("Sedang melakukan crawling dan menghitung skor PageRank. Mohon tunggu...", "info");

  try {
    const response = await fetch(`${API_BASE_URL}/api/crawl`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url, depth }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Gagal memproses permintaan.");
    }

    renderStats(data.stats);
    renderGraph(data.graph, data.seed_url);
    renderTop10(data.top_10);
    setStatus(
      `Selesai! Ditemukan ${data.stats.total_nodes} node dan ${data.stats.total_edges} edge pada kedalaman ${data.max_depth}.`,
      "success"
    );
  } catch (err) {
    setStatus(`Terjadi kesalahan: ${err.message}`, "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Mulai Crawling";
  }
});
