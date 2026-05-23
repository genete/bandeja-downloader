// Mundo MAIN: tiene acceso a los globales de BandeJA (abrirModal, descargarZip…)
// Los content scripts viven en un mundo aislado y no pueden llamar estas funciones
// directamente. Este bridge recibe comandos via postMessage y los ejecuta aquí.
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
