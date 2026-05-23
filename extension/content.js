// Content script — automatización de BandeJA
// Se inyecta en: extranet.chie.junta-andalucia.es/bandeja/*

const TIMEOUT_FILTRO_MS   = 15_000;   // espera máx para que actualice la lista
const TIMEOUT_MODAL_MS    = 10_000;   // espera máx para que abra el modal
const TIMEOUT_DESCARGA_MS = 120_000;  // espera máx para que termine el ZIP (2 min)

// ── Utilidad: esperar condición con timeout ──────────────────────────────────

function waitFor(conditionFn, timeoutMs) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    // 500 ms: con throttling de ventana minimizada (~1 s efectivo) sigue siendo suficiente
    const check = setInterval(() => {
      try {
        if (conditionFn()) {
          clearInterval(check);
          resolve(true);
        } else if (Date.now() - start > timeoutMs) {
          clearInterval(check);
          reject(new Error(`Timeout (${timeoutMs}ms) esperando condición`));
        }
      } catch (e) {
        clearInterval(check);
        reject(e);
      }
    }, 500);
  });
}

// ── Detectar toast de error via MutationObserver ─────────────────────────────

function watchForErrorToast(timeoutMs) {
  return new Promise((resolve) => {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType !== 1) continue;
          // Buscar elementos que indiquen error: clases Bootstrap o texto
          const esError =
            node.classList?.contains('alert-danger') ||
            node.classList?.contains('toast-error') ||
            /error|danger|no se pudo|fallo/i.test(node.textContent) &&
            (node.classList?.contains('alert') || node.classList?.contains('toast'));

          if (esError) {
            observer.disconnect();
            resolve({ error: true, texto: node.textContent?.trim() });
            return;
          }
          // También buscar en hijos
          const hijo = node.querySelector?.(
            '.alert-danger, .toast-error, [class*="danger"], [class*="error"]'
          );
          if (hijo) {
            observer.disconnect();
            resolve({ error: true, texto: hijo.textContent?.trim() });
            return;
          }
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    // Si pasa el timeout sin toast de error, resolvemos sin error
    setTimeout(() => {
      observer.disconnect();
      resolve({ error: false });
    }, timeoutMs);
  });
}

// ── Paso 1: Filtrar por código ───────────────────────────────────────────────

function contarFilas() {
  // Excluir filas que estén dentro del modal — table.dataTable se usa también ahí
  const filas = Array.from(document.querySelectorAll(
    'table.listadoComunicaciones tbody tr, table.dataTable tbody tr'
  )).filter(tr => !tr.closest('#modal'));

  if (filas.length === 1 && /sin resultado|no hay|no se han/i.test(filas[0]?.textContent)) {
    return 0;
  }
  return filas.length;
}

async function filtrarPorCodigo(codigo) {
  // 1. Borrar filtros predeterminados de BandeJA
  const btnBorrar = document.querySelector('#borrarFiltros');
  if (btnBorrar) {
    btnBorrar.click();
    await new Promise(r => setTimeout(r, 1200));
  } else {
    console.warn('[BandeJA] Botón #borrarFiltros no encontrado — continuando sin borrar');
  }

  // 2. Localizar el campo Código
  const inputCodigo = document.querySelector('#codigoExpedienteFiltro');
  if (!inputCodigo) throw new Error('Campo #codigoExpedienteFiltro no encontrado');

  // Escribir el código usando el setter nativo para que React/jQuery lo detecte
  const nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  )?.set;
  if (nativeSetter) nativeSetter.call(inputCodigo, codigo);
  else inputCodigo.value = codigo;
  inputCodigo.dispatchEvent(new Event('input',  { bubbles: true }));
  inputCodigo.dispatchEvent(new Event('change', { bubbles: true }));
  inputCodigo.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));

  // 3. Pulsar el botón "Filtrar"
  const btnFiltrar = document.querySelector('#filtrar');
  if (!btnFiltrar) throw new Error('Botón #filtrar no encontrado');
  btnFiltrar.click();

  // 4. Esperar a que la tabla muestre exactamente 1 fila
  try {
    await waitFor(() => contarFilas() === 1, TIMEOUT_FILTRO_MS);
  } catch {
    const n = contarFilas();
    if (n === 0) throw new Error(`Código no encontrado en BandeJA: ${codigo}`);
    throw new Error(`Filtro no convergió: ${n} filas tras ${TIMEOUT_FILTRO_MS / 1000}s (esperaba 1)`);
  }
}

// ── Paso 2: Abrir modal de información ──────────────────────────────────────

function modalAbierto() {
  const modal = document.querySelector('#modal');
  return modal &&
    modal.classList.contains('show') &&
    modal.style.display !== 'none' &&
    document.querySelector('#descargarZip') !== null;
}

async function cerrarModalSiAbierto() {
  if (!modalAbierto()) return;
  document.querySelector('#cerrarModalInfo')?.click();
  try { await waitFor(() => !modalAbierto(), 3_000); } catch { /* continuar igualmente */ }
}

async function abrirModalInfo() {
  // Asegurarse de que no hay un modal anterior abierto antes de abrir el nuevo
  await cerrarModalSiAbierto();

  const primeraFila = document.querySelector(
    'table.listadoComunicaciones tbody tr:first-child, table.dataTable tbody tr:first-child'
  );
  if (!primeraFila) throw new Error('No se encontró la fila de la comunicación en el listado');

  // ── Intento 1: doble clic sobre la fila (método confirmado por el usuario) ──
  primeraFila.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true }));
  try {
    await waitFor(modalAbierto, 4_000);
    return; // éxito
  } catch { /* seguimos con el siguiente intento */ }

  // ── Intento 2: hover + buscar icono por título/aria-label/onclick ────────────
  primeraFila.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
  primeraFila.dispatchEvent(new MouseEvent('mouseover',  { bubbles: true }));
  await new Promise(r => setTimeout(r, 500));

  // Buscar en la fila Y en el documento (por si el overlay está fuera del <tr>)
  const candidatos = [
    ...primeraFila.querySelectorAll('a, button, i, span, img'),
    ...document.querySelectorAll('a, button, i, span, img'),
  ];
  const infoEl = candidatos.find(el => {
    const texto = (el.title || el.getAttribute('aria-label') || el.getAttribute('onclick') || '').toLowerCase();
    return texto.includes('informaci');
  });

  if (infoEl) {
    infoEl.click();
    try {
      await waitFor(modalAbierto, 4_000);
      return;
    } catch { /* seguimos */ }
  }

  // ── Intento 3: llamar abrirModal() inyectando código en el contexto de página ─
  // Los content scripts no tienen acceso a las funciones globales de BandeJA,
  // pero sí pueden inyectar un <script> que las llame.
  const onclicks = Array.from(primeraFila.querySelectorAll('[onclick]'))
    .map(el => el.getAttribute('onclick'));
  const idMatch = onclicks.join(' ').match(/abrirModal\([^,]+,\s*'?(\d+)'?\)/);

  if (idMatch) {
    const idInterno = idMatch[1];
    console.log('[BandeJA] Enviando abrirModal con ID interno:', idInterno);
    window.postMessage({ bandeja: true, action: 'abrirModal', args: ['informacion', idInterno] }, '*');
    try {
      await waitFor(modalAbierto, 4_000);
      return;
    } catch { /* seguimos */ }
  }

  throw new Error('MODAL_NO_DISPONIBLE');
}

// ── Paso 3: Descargar ZIP y esperar resultado ────────────────────────────────

async function descargarYEsperar() {
  const btnDescargar = document.querySelector('#descargarZip');
  const spinnerEl    = document.querySelector('#descargandoZip');

  if (!btnDescargar) throw new Error('Botón #descargarZip no encontrado en el modal');

  // Pulsar descarga vía bridge (mundo MAIN) para evitar la CSP de BandeJA
  window.postMessage({ bandeja: true, action: 'descargarZip' }, '*');

  // Notificar al background que la petición salió (compilación en servidor, sin timeout aún)
  chrome.runtime.sendMessage({ type: 'DOWNLOAD_STARTED' });

  // Esperar a que el spinner aparezca (confirma que la petición llegó al servidor)
  const spinnerDetectado = await waitFor(
    () => spinnerEl && spinnerEl.style.display !== 'none', 8_000
  ).then(() => true).catch(() => false);

  // Cuando el spinner desaparezca → compilación terminada → avisar al background
  // para que arranque el timer de "el navegador debe iniciar la descarga ya"
  if (spinnerDetectado) {
    waitFor(() => spinnerEl.style.display === 'none', TIMEOUT_DESCARGA_MS)
      .then(() => chrome.runtime.sendMessage({ type: 'COMPILATION_DONE' }))
      .catch(() => {});
  } else {
    // Spinner no detectado: apareció y desapareció antes de poder verlo → compilación instantánea
    chrome.runtime.sendMessage({ type: 'COMPILATION_DONE' });
  }

  // Dos señales en carrera: toast de error vs botón reapareciendo
  // Si ninguna llega en TIMEOUT_DESCARGA_MS → 'pendiente' (background.js detecta éxito via chrome.downloads)
  return new Promise((resolve) => {
    let resuelto = false;
    const resolver = (valor) => { if (!resuelto) { resuelto = true; resolve(valor); } };

    watchForErrorToast(TIMEOUT_DESCARGA_MS).then(r => {
      if (r.error) resolver({ tipo: 'error', razon: r.texto });
      else         resolver({ tipo: 'pendiente' }); // timeout sin error
    });

    waitFor(() =>
      spinnerEl && spinnerEl.style.display === 'none' && btnDescargar.style.display !== 'none',
      TIMEOUT_DESCARGA_MS
    ).then(() => resolver({ tipo: 'completado' }))
     .catch(() => { /* ignorado: ya resuelto por otra vía */ });
  });
}

// ── Proceso completo para un código ─────────────────────────────────────────

async function procesarCodigo(codigo) {
  console.log('[BandeJA] Procesando:', codigo);
  try {
    // 1. Filtrar
    await filtrarPorCodigo(codigo);

    // 2. Abrir modal info
    await abrirModalInfo();

    // 3. Descargar y esperar resultado
    const resultado = await descargarYEsperar();

    if (resultado.tipo === 'error') {
      chrome.runtime.sendMessage({ type: 'DOWNLOAD_ERROR', reason: resultado.razon });
    } else if (resultado.tipo === 'completado') {
      // Éxito rápido detectado por DOM — background.js también lo confirmará via onChanged
      chrome.runtime.sendMessage({ type: 'DOWNLOAD_SUCCESS' });
    }
    // tipo === 'pendiente': background.js gestiona el resultado via chrome.downloads.onChanged

  } catch (e) {
    console.error('[BandeJA] Error procesando', codigo, ':', e.message);
    if (e.message === 'MODAL_NO_DISPONIBLE') {
      chrome.runtime.sendMessage({ type: 'SIN_DOCUMENTOS' });
    } else {
      chrome.runtime.sendMessage({ type: 'DOWNLOAD_ERROR', reason: e.message });
    }
  } finally {
    // Cerrar modal y esperar a que desaparezca antes de que llegue el siguiente trabajo
    await cerrarModalSiAbierto();
  }
}

// ── Escuchar mensajes del background ────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'PROCESS_CODE') {
    procesarCodigo(msg.codigo);
  }
});

console.log('[BandeJA] Content script cargado en', window.location.href);
