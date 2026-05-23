// Content script — automatización de BandeJA
// Se inyecta en: extranet.chie.junta-andalucia.es/bandeja/*

const TIMEOUT_FILTRO_MS   = 15_000;   // espera máx para que actualice la lista
const TIMEOUT_MODAL_MS    = 10_000;   // espera máx para que abra el modal
const TIMEOUT_DESCARGA_MS = 120_000;  // espera máx para que termine el ZIP (2 min)

// ── Utilidad: esperar condición con timeout ──────────────────────────────────

function waitFor(conditionFn, timeoutMs) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
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
    }, 300);
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
  const filas = document.querySelectorAll(
    'table.listadoComunicaciones tbody tr, table.dataTable tbody tr'
  );
  // Devuelve 0 si la única fila es el mensaje "sin resultados"
  if (filas.length === 1 && /sin resultado|no hay|no se han/i.test(filas[0]?.textContent)) {
    return 0;
  }
  return filas.length;
}

async function filtrarPorCodigo(codigo) {
  // 1. Borrar filtros predeterminados de BandeJA (estados, fechas, etc.)
  //    El botón puede llamarse "BORRAR FILTROS" o "Borrar filtros"
  const btnBorrar = Array.from(document.querySelectorAll('button'))
    .find(b => /borrar\s+filtros?/i.test(b.textContent.trim()));

  if (btnBorrar) {
    btnBorrar.click();
    // Esperar a que el listado se actualice tras borrar los filtros
    // (la lista mostrará más filas o se vaciará)
    await new Promise(r => setTimeout(r, 800));
  } else {
    console.warn('[BandeJA] Botón "Borrar filtros" no encontrado — continuando sin borrar');
  }

  // 2. Localizar el campo Código del panel de filtros
  const inputCodigo = document.querySelector(
    'input[placeholder*="digo"], input[id*="odigo" i], input[name*="odigo" i]'
  );
  if (!inputCodigo) throw new Error('Campo Código no encontrado en el filtro');

  // Limpiar primero el campo por si tenía valor previo
  inputCodigo.value = '';
  inputCodigo.dispatchEvent(new Event('input',  { bubbles: true }));

  // Escribir el código simulando eventos nativos (para que jQuery/Struts lo detecte)
  const nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  )?.set;
  if (nativeSetter) nativeSetter.call(inputCodigo, codigo);
  inputCodigo.dispatchEvent(new Event('input',  { bubbles: true }));
  inputCodigo.dispatchEvent(new Event('change', { bubbles: true }));

  // 3. Pulsar el botón "Filtrar"
  const btnFiltrar = Array.from(document.querySelectorAll('button'))
    .find(b => /^filtrar$/i.test(b.textContent.trim()));
  if (!btnFiltrar) throw new Error('Botón "Filtrar" no encontrado');
  btnFiltrar.click();

  // 4. Esperar a que la tabla muestre exactamente 1 fila (la comunicación buscada)
  await waitFor(() => contarFilas() === 1, TIMEOUT_FILTRO_MS);
}

// ── Paso 2: Abrir modal de información ──────────────────────────────────────

async function abrirModalInfo() {
  // La primera fila del listado filtrado
  const primeraFila = document.querySelector(
    'table.listadoComunicaciones tbody tr:first-child, table.dataTable tbody tr:first-child'
  );
  if (!primeraFila) throw new Error('No se encontró la fila de la comunicación en el listado');

  // Activar hover sobre la fila para que aparezcan los iconos de acción
  primeraFila.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
  primeraFila.dispatchEvent(new MouseEvent('mouseover',  { bubbles: true }));

  await new Promise(r => setTimeout(r, 400)); // pequeña pausa para que el DOM actualice

  // Buscar el icono/botón de "Información detallada"
  // Puede estar en la fila o en el documento (si es un overlay)
  const infoEl =
    primeraFila.querySelector('[title*="nformaci"], [onclick*="informaci"]') ||
    document.querySelector('[title*="nformaci"], [onclick*="informaci"]');

  if (!infoEl) {
    // Fallback: buscar por texto en spans/links de la fila
    const enlace = Array.from(primeraFila.querySelectorAll('a, span, i, button'))
      .find(el => /informaci/i.test(el.title || el.getAttribute('aria-label') || ''));
    if (!enlace) throw new Error('Icono "Información detallada" no encontrado en la fila');
    enlace.click();
  } else {
    infoEl.click();
  }

  // Esperar a que el modal esté visible
  await waitFor(() => {
    const modal = document.querySelector('#modal');
    return modal &&
      modal.classList.contains('show') &&
      modal.style.display !== 'none' &&
      document.querySelector('#descargarZip') !== null;
  }, TIMEOUT_MODAL_MS);
}

// ── Paso 3: Descargar ZIP y esperar resultado ────────────────────────────────

async function descargarYEsperar() {
  const btnDescargar = document.querySelector('#descargarZip');
  const spinnerEl    = document.querySelector('#descargandoZip');

  if (!btnDescargar) throw new Error('Botón "Descargar documentos" no encontrado en el modal');

  // Lanzar el observador de toast de error ANTES de pulsar
  const toastPromise = watchForErrorToast(TIMEOUT_DESCARGA_MS);

  // Pulsar descarga
  btnDescargar.click();

  // Esperar a que el spinner de "Descargando..." aparezca (señal de que la petición salió)
  try {
    await waitFor(() => {
      return spinnerEl && spinnerEl.style.display !== 'none';
    }, 8_000);
  } catch {
    // Puede que el spinner ya apareció y desapareció muy rápido → seguimos
  }

  // Notificar al background que la descarga fue iniciada
  chrome.runtime.sendMessage({ type: 'DOWNLOAD_STARTED' });

  // Esperar resultado: botón vuelve a aparecer (éxito) vs toast de error
  const botonVuelvePromise = waitFor(() => {
    return spinnerEl &&
      spinnerEl.style.display === 'none' &&
      btnDescargar.style.display !== 'none';
  }, TIMEOUT_DESCARGA_MS);

  const resultado = await Promise.race([
    toastPromise.then(r   => ({ tipo: 'toast',    ...r })),
    botonVuelvePromise.then(() => ({ tipo: 'completado' })),
  ]);

  return resultado;
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

    if (resultado.tipo === 'toast' && resultado.error) {
      chrome.runtime.sendMessage({
        type: 'DOWNLOAD_ERROR',
        reason: resultado.texto || 'Toast de error en BandeJA'
      });
    } else if (resultado.tipo === 'completado') {
      chrome.runtime.sendMessage({ type: 'DOWNLOAD_SUCCESS' });
    } else {
      chrome.runtime.sendMessage({ type: 'DOWNLOAD_ERROR', reason: 'Resultado inesperado' });
    }

  } catch (e) {
    console.error('[BandeJA] Error procesando', codigo, ':', e.message);
    chrome.runtime.sendMessage({ type: 'DOWNLOAD_ERROR', reason: e.message });
  } finally {
    // Cerrar modal si sigue abierto
    document.querySelector('#cerrarModalInfo')?.click();
  }
}

// ── Escuchar mensajes del background ────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'PROCESS_CODE') {
    procesarCodigo(msg.codigo);
  }
});

console.log('[BandeJA] Content script cargado en', window.location.href);
