// Popup — muestra el estado del servidor Python

const SERVER_URL = 'http://localhost:8000';

async function actualizarEstado() {
  try {
    const res = await fetch(`${SERVER_URL}/api/status`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) throw new Error('Respuesta no OK');
    const data = await res.json();

    document.getElementById('total').textContent     = data.total    ?? '—';
    document.getElementById('pendiente').textContent = data.pendiente ?? '—';
    document.getElementById('en_curso').textContent  = data.en_curso  ?? '—';
    document.getElementById('ok').textContent        = data.ok        ?? '—';
    document.getElementById('error').textContent     = data.error     ?? '—';

    const el = document.getElementById('estado-servidor');
    el.textContent = 'Servidor activo ✓';
    el.className = 'conectado';

  } catch {
    const el = document.getElementById('estado-servidor');
    el.textContent = 'Servidor no disponible';
    el.className = 'desconectado';
  }
}

actualizarEstado();

// ── Carga de CSV desde el popup ──────────────────────────────────────────────

const inputCsv   = document.getElementById('input-csv');
const btnCsv     = document.getElementById('btn-csv');
const feedback   = document.getElementById('csv-feedback');

btnCsv.addEventListener('click', () => inputCsv.click());

inputCsv.addEventListener('change', async () => {
  const file = inputCsv.files[0];
  if (!file) return;

  feedback.textContent = 'Enviando…';
  feedback.style.color = '#555';

  try {
    const buffer = await file.arrayBuffer();
    const res = await fetch(`${SERVER_URL}/api/load-csv`, {
      method: 'POST',
      body: buffer,
      signal: AbortSignal.timeout(10_000),
    });
    const data = await res.json();
    if (data.ok) {
      feedback.textContent = `✓ ${data.nuevos} códigos añadidos`;
      feedback.style.color = '#087021';
      actualizarEstado();
    } else {
      feedback.textContent = `✗ ${data.error}`;
      feedback.style.color = '#c0392b';
    }
  } catch {
    feedback.textContent = '✗ Servidor no disponible';
    feedback.style.color = '#c0392b';
  }

  // Limpiar para permitir seleccionar el mismo fichero otra vez
  inputCsv.value = '';
});

// ── Exportar resultados ──────────────────────────────────────────────────────

document.getElementById('btn-export').addEventListener('click', async () => {
  try {
    const res = await fetch(`${SERVER_URL}/api/export-csv`, {
      signal: AbortSignal.timeout(5000)
    });
    if (!res.ok) throw new Error();
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'resultados_bandeja.csv';
    a.click();
    URL.revokeObjectURL(url);
  } catch {
    feedback.textContent = '✗ No se pudo exportar';
    feedback.style.color = '#c0392b';
  }
});
