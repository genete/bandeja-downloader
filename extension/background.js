// Service worker — gestiona la cola, el polling y los eventos de descarga de Chrome

const SERVER_URL = 'http://localhost:8000';
// Intervalo de polling en segundos (mínimo de chrome.alarms es ~1 min; usamos storage para control fino)
const POLL_INTERVAL_MS = 3000;

// Estado del trabajo activo
let activeJob = null;      // { codigo, downloadId }
let pollTimer = null;

// ── Arranque ────────────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  console.log('[BandeJA] Extensión instalada. Iniciando polling.');
  startPolling();
});

chrome.runtime.onStartup.addListener(() => {
  startPolling();
});

// Reanudar polling si el service worker se reactiva
startPolling();

// ── Polling al servidor Python ───────────────────────────────────────────────

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollServer, POLL_INTERVAL_MS);
}

async function pollServer() {
  // No pedir trabajo si ya hay uno en curso
  if (activeJob) return;

  try {
    const res = await fetch(`${SERVER_URL}/api/next`, { signal: AbortSignal.timeout(5000) });
    if (!res.ok) return;
    const job = await res.json();
    if (!job?.codigo) return;

    activeJob = { codigo: job.codigo, downloadId: null };
    await dispatchToContentScript(job.codigo);

  } catch (e) {
    // Servidor no disponible — silencioso (puede que no esté arrancado)
  }
}

// ── Envío al content script ──────────────────────────────────────────────────

async function dispatchToContentScript(codigo) {
  const tabs = await chrome.tabs.query({
    url: 'https://extranet.chie.junta-andalucia.es/bandeja/*'
  });

  if (tabs.length === 0) {
    console.warn('[BandeJA] No hay pestaña de BandeJA abierta.');
    await reportResult(codigo, 'error', 'No hay pestaña de BandeJA abierta');
    activeJob = null;
    return;
  }

  const tabId = tabs[0].id;

  try {
    await chrome.tabs.sendMessage(tabId, { type: 'PROCESS_CODE', codigo });
  } catch (e) {
    // El content script no está cargado (pestaña abierta antes de instalar la extensión)
    // → inyectarlo programáticamente y reintentar
    console.warn('[BandeJA] Content script no disponible, inyectando…');
    try {
      await chrome.scripting.executeScript({
        target: { tabId },
        files: ['content.js']
      });
      // Pequeña pausa para que el script se inicialice
      await new Promise(r => setTimeout(r, 500));
      await chrome.tabs.sendMessage(tabId, { type: 'PROCESS_CODE', codigo });
    } catch (e2) {
      await reportResult(codigo, 'error', 'No se pudo inyectar content script: ' + e2.message);
      activeJob = null;
    }
  }
}

// ── Mensajes desde el content script ────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  switch (msg.type) {

    case 'DOWNLOAD_STARTED':
      // La descarga ZIP fue iniciada — esperamos el evento chrome.downloads
      console.log('[BandeJA] Descarga iniciada para', activeJob?.codigo);
      break;

    case 'DOWNLOAD_SUCCESS':
      // El botón volvió a aparecer + descarga completada por chrome.downloads
      finishJob('ok', msg.filename || '');
      break;

    case 'DOWNLOAD_ERROR':
      finishJob('error', msg.reason || 'Error desconocido');
      break;
  }
});

// ── Eventos de descarga de Chrome ────────────────────────────────────────────

chrome.downloads.onCreated.addListener((item) => {
  if (activeJob && activeJob.downloadId === null) {
    // Asociar la primera descarga creada con el trabajo activo
    activeJob.downloadId = item.id;
    activeJob.filename   = item.filename || '';
    console.log('[BandeJA] Descarga Chrome registrada:', item.id, item.filename);
  }
});

chrome.downloads.onChanged.addListener((delta) => {
  if (!activeJob || delta.id !== activeJob.downloadId) return;

  if (delta.state?.current === 'complete') {
    console.log('[BandeJA] Descarga completada:', delta.id);
    // El content script habrá notificado DOWNLOAD_SUCCESS; si no, lo hacemos aquí
    if (activeJob) finishJob('ok', '');
  }

  if (delta.state?.current === 'interrupted') {
    const motivo = delta.error?.current || 'Interrumpida';
    finishJob('error', 'Descarga interrumpida: ' + motivo);
  }
});

// ── Helpers ──────────────────────────────────────────────────────────────────

function finishJob(status, detail) {
  if (!activeJob) return;
  const codigo   = activeJob.codigo;
  const filename = activeJob.filename || '';
  activeJob = null;
  reportResult(codigo, status, detail, filename);
}

async function reportResult(codigo, status, detail, zip_filename = '') {
  try {
    await fetch(`${SERVER_URL}/api/result`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        codigo,
        status,
        detail,
        zip_filename,
        timestamp: new Date().toISOString()
      }),
      signal: AbortSignal.timeout(5000)
    });
    console.log('[BandeJA] Resultado reportado:', codigo, status);
  } catch (e) {
    console.error('[BandeJA] Error reportando resultado:', e);
  }
}
