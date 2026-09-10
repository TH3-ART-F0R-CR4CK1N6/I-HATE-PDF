const TOOLS = {
  "merge": {
    title: "Unir PDF",
    endpoint: "/api/merge",
    multiple: true,
    accept: ".pdf",
    fields: [],
  },
  "split": {
    title: "Dividir PDF",
    endpoint: "/api/split",
    multiple: false,
    accept: ".pdf",
    fields: [
      { name: "mode", label: "Modo", type: "select", options: [
          { value: "all", label: "Una página por archivo (ZIP)" },
          { value: "ranges", label: "Extraer rango de páginas" },
        ]},
      { name: "ranges", label: "Rango (ej: 1-3,5)", type: "text", placeholder: "1-3,5" },
    ],
  },
  "compress": {
    title: "Comprimir PDF",
    endpoint: "/api/compress",
    multiple: false,
    accept: ".pdf",
    fields: [
      { name: "level", label: "Nivel de compresión", type: "select", options: [
          { value: "low", label: "Baja (mejor calidad)" },
          { value: "medium", label: "Media (recomendado)" },
          { value: "high", label: "Alta (menor tamaño)" },
        ]},
    ],
  },
  "rotate": {
    title: "Rotar PDF",
    endpoint: "/api/rotate",
    multiple: false,
    accept: ".pdf",
    fields: [
      { name: "angle", label: "Ángulo", type: "select", options: [
          { value: "90", label: "90°" },
          { value: "180", label: "180°" },
          { value: "270", label: "270°" },
        ]},
    ],
  },
  "pdf-to-jpg": {
    title: "PDF a JPG",
    endpoint: "/api/pdf-to-jpg",
    multiple: false,
    accept: ".pdf",
    fields: [],
  },
  "jpg-to-pdf": {
    title: "JPG/PNG a PDF",
    endpoint: "/api/jpg-to-pdf",
    multiple: true,
    accept: ".jpg,.jpeg,.png",
    fields: [],
  },
  "pdf-to-word": {
    title: "PDF a Word",
    endpoint: "/api/pdf-to-word",
    multiple: false,
    accept: ".pdf",
    fields: [],
  },
  "word-to-pdf": {
    title: "Word a PDF",
    endpoint: "/api/word-to-pdf",
    multiple: false,
    accept: ".docx",
    fields: [],
  },
  "extract": {
    title: "Extraer páginas",
    endpoint: "/api/extract",
    multiple: false,
    accept: ".pdf",
    fields: [
      { name: "ranges", label: "Páginas a conservar (ej: 1-3,5)", type: "text", placeholder: "1-3,5" },
    ],
  },
  "remove-pages": {
    title: "Eliminar páginas",
    endpoint: "/api/remove-pages",
    multiple: false,
    accept: ".pdf",
    fields: [
      { name: "ranges", label: "Páginas a eliminar (ej: 2,4-5)", type: "text", placeholder: "2,4-5" },
    ],
  },
  "watermark": {
    title: "Marca de agua",
    endpoint: "/api/watermark",
    multiple: false,
    accept: ".pdf",
    fields: [
      { name: "text", label: "Texto de la marca de agua", type: "text", placeholder: "CONFIDENCIAL" },
    ],
  },
  "page-numbers": {
    title: "Numerar páginas",
    endpoint: "/api/page-numbers",
    multiple: false,
    accept: ".pdf",
    fields: [],
  },
  "protect": {
    title: "Proteger PDF",
    endpoint: "/api/protect",
    multiple: false,
    accept: ".pdf",
    fields: [
      { name: "password", label: "Contraseña", type: "password", placeholder: "••••••••" },
    ],
  },
  "unlock": {
    title: "Desbloquear PDF",
    endpoint: "/api/unlock",
    multiple: false,
    accept: ".pdf",
    fields: [
      { name: "password", label: "Contraseña actual", type: "password", placeholder: "••••••••" },
    ],
  },
  "repair": {
    title: "Reparar PDF",
    endpoint: "/api/repair",
    multiple: false,
    accept: ".pdf",
    fields: [],
  },
};

const overlay = document.getElementById("modal-overlay");
const modalTitle = document.getElementById("modal-title");
const modalBody = document.getElementById("modal-body");
const modalStatus = document.getElementById("modal-status");
const closeBtn = document.getElementById("modal-close");

let selectedFiles = [];

document.querySelectorAll(".card").forEach(card => {
  card.addEventListener("click", () => openTool(card.dataset.tool));
});

closeBtn.addEventListener("click", closeModal);
overlay.addEventListener("click", (e) => { if (e.target === overlay) closeModal(); });

function closeModal() {
  overlay.classList.add("hidden");
  selectedFiles = [];
  modalStatus.textContent = "";
  modalStatus.className = "";
}

function openTool(toolKey) {
  const tool = TOOLS[toolKey];
  if (!tool) return;
  selectedFiles = [];
  modalTitle.textContent = tool.title;
  modalStatus.textContent = "";
  modalStatus.className = "";

  let html = `
    <div class="dropzone" id="dropzone">
      <p>📂 Arrastra tu${tool.multiple ? "s archivo(s)" : " archivo"} aquí<br>o haz clic para seleccionar</p>
      <input type="file" id="file-input" accept="${tool.accept}" ${tool.multiple ? "multiple" : ""}>
      <div class="file-list" id="file-list"></div>
    </div>
  `;

  tool.fields.forEach(field => {
    html += `<div class="field"><label>${field.label}</label>`;
    if (field.type === "select") {
      html += `<select name="${field.name}" id="f-${field.name}">`;
      field.options.forEach(opt => {
        html += `<option value="${opt.value}">${opt.label}</option>`;
      });
      html += `</select>`;
    } else {
      html += `<input type="${field.type}" name="${field.name}" id="f-${field.name}" placeholder="${field.placeholder || ''}">`;
    }
    html += `</div>`;
  });

  html += `<button class="btn-primary" id="submit-btn">Procesar</button>`;

  modalBody.innerHTML = html;
  overlay.classList.remove("hidden");

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileListEl = document.getElementById("file-list");

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    handleFiles(e.dataTransfer.files, tool, fileListEl);
  });
  fileInput.addEventListener("change", () => handleFiles(fileInput.files, tool, fileListEl));

  document.getElementById("submit-btn").addEventListener("click", () => submitTool(toolKey));
}

function handleFiles(fileList, tool, fileListEl) {
  const files = Array.from(fileList);
  selectedFiles = tool.multiple ? files : files.slice(0, 1);
  fileListEl.innerHTML = selectedFiles.map(f => `• ${f.name}`).join("<br>");
}

async function submitTool(toolKey) {
  const tool = TOOLS[toolKey];
  if (selectedFiles.length === 0) {
    setStatus("Por favor selecciona al menos un archivo.", "error");
    return;
  }

  const formData = new FormData();
  if (tool.multiple) {
    selectedFiles.forEach(f => formData.append("files", f));
  } else {
    formData.append("file", selectedFiles[0]);
  }

  tool.fields.forEach(field => {
    const el = document.getElementById(`f-${field.name}`);
    if (el) formData.append(field.name, el.value);
  });

  const submitBtn = document.getElementById("submit-btn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Procesando...";
  setStatus("Procesando tu archivo, esto puede tardar unos segundos...", "");

  try {
    const res = await fetch(tool.endpoint, { method: "POST", body: formData });
    if (!res.ok) {
      let msg = "Ocurrió un error procesando el archivo.";
      try {
        const errJson = await res.json();
        if (errJson.error) msg = errJson.error;
      } catch (_) {}
      setStatus(msg, "error");
      submitBtn.disabled = false;
      submitBtn.textContent = "Procesar";
      return;
    }

    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    let filename = "resultado";
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match) filename = match[1];

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    setStatus("¡Listo! Tu archivo se ha descargado.", "success");
  } catch (err) {
    setStatus("Error de conexión con el servidor.", "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Procesar";
  }
}

function setStatus(msg, type) {
  modalStatus.textContent = msg;
  modalStatus.className = type || "";
}
