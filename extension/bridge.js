// Mundo MAIN: tiene acceso a los globales de BandeJA (abrirModal, descargarZip…)
// Los content scripts viven en un mundo aislado y no pueden llamar estas funciones
// directamente. Este bridge recibe comandos via postMessage y los ejecuta aquí.

// Suprimir el alert() bloqueante de DataTables — redirigir a console.warn
(function suprimirDataTablesAlert() {
  const aplicar = () => {
    if (window.jQuery?.fn?.dataTable?.ext) {
      window.jQuery.fn.dataTable.ext.errMode = 'none';
      console.log('[BandeJA] DataTables errMode → none (sin alert bloqueante)');
      return true;
    }
    return false;
  };
  if (!aplicar()) {
    // jQuery puede cargarse después del bridge — reintentar brevemente
    const t = setInterval(() => { if (aplicar()) clearInterval(t); }, 200);
    setTimeout(() => clearInterval(t), 5000);
  }
})();

window.addEventListener('message', (event) => {
  if (event.source !== window || event.data?.bandeja !== true) return;

  const { action, args = [] } = event.data;

  switch (action) {
    case 'abrirModal':
      if (typeof abrirModal === 'function') abrirModal(...args);
      break;

    case 'descargarZip':
      if (typeof descargarZip === 'function') {
        if (typeof mostrarEspera !== 'undefined') mostrarEspera = false;
        descargarZip();
      }
      break;
  }
});
