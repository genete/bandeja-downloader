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
