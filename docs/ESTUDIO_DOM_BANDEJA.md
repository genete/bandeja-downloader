# Estudio DOM BandeJA — Referencia para cliente Playwright

Verificado el 2026-06-09 con cuenta real.

---

## 1. Flujo de autenticación

### 1.1 Login SSO

- Navegar a `https://extranet.chie.junta-andalucia.es/bandeja/`
- Redirige a `https://ssoweb.juntadeandalucia.es/SAML2/SSOService.php?...`
- Formulario:
  - `input[name="username"]` → campo Usuario
  - `input[name="password"]` → campo Contraseña
  - `button "Inicio de sesión"` → enviar

### 1.2 Diálogo de obligaciones de uso

- Aparece en `https://extranet.chie.junta-andalucia.es/bandeja/inicio/accesoSSO.action`
- `button "Aceptar"` → continuar

### 1.3 Selección de puesto de trabajo (opcional)

- Solo aparece cuando el usuario tiene **más de un perfil**.
- `select#usuarioSeleccionado` → combobox con las opciones de puesto
- `button "Acceder"` → confirmar selección

URL tras login exitoso:
`https://extranet.chie.junta-andalucia.es/bandeja/modulos/bandejaTrabajo/inicio.action`

---

## 2. Bandeja principal

### 2.1 Filtros (panel izquierdo)

| Campo | Selector | Notas |
|---|---|---|
| Código | `input[placeholder="Código..."]` | Acepta código completo: `EXT/2026/...` |
| Asunto | `input[placeholder="Asunto..."]` | |
| Número expediente | `input[placeholder="Número Expediente..."]` | |
| Número registro | `input[placeholder="Número de registro..."]` | |
| Usuario asignado | `input[placeholder="Usuario asignado..."]` | |
| Botón Filtrar | `button#filtrar` | onclick: `filtra()` |
| Botón Borrar filtros | `button "Borrar filtros"` | |

### 2.2 Tabla de comunicaciones

- DataTables grid dentro de `main`
- Columnas: (checkbox), (acciones), **Entrada**, **Código**, **Asunto**, **Origen**, **Estado**
- Cada fila: `row "FECHA CODIGO ASUNTO ORIGEN ESTADO"`
- La columna de código (4ª celda) contiene valores tipo `EXT/2026/0000000003152345`

Para localizar fila por código:
```python
page.get_by_role("row", name=codigo)
# o más precisamente:
page.locator(f"td:text('{codigo}')").locator("..").  # fila padre
```

### 2.3 Acciones de fila

Algunas filas tienen botones de acción en la última celda:
- `img "Vincular"`
- `img "Informacion detallada"` ← el que nos interesa
- `img "Evolucion"`
- `img "Reasignar"`, `img "Redistribuir"`, `img "Reenviar"`, `img "Difundir"`, `img "Finalizar"`

Alternativa más robusta: **doble clic en la fila** abre directamente el modal de información detallada.

---

## 3. Modal de Información detallada

Se abre con doble clic en la fila o clic en `img "Informacion detallada"`.

### 3.1 Cabecera del modal

```
heading "Información detallada - EXT/2026/XXXXXXXXXXXXXXXX"
button "Más acciones"
button "Reenviar"
button "Cerrar" (×)
```

### 3.2 Pestaña "Documentación Asociada"

- Link `"Documentacion asociada"` (href `#documentosInfo`) — activa por defecto
- Botón de descarga masiva:
  ```
  a[href="javascript:mostrarEspera=false; descargarZip();"]
  # texto visible: " Descargar documentos"
  # selector alternativo: a:has-text("Descargar documentos")
  ```
- Tabla de documentos individuales:
  - Columnas: Fecha, Nombre, Abrir
  - Cada fila tiene un link "Descargar" por documento

### 3.3 Selectors clave del modal

```python
# Esperar a que el modal esté visible
page.wait_for_selector('text=Información detallada')

# Botón descargar ZIP (descarga todos los documentos como ZIP)
page.locator('a:has-text("Descargar documentos")')
# o por href:
page.locator('a[href*="descargarZip"]')

# Cerrar modal
page.get_by_role("button", name="Cerrar")
```

---

## 4. Gestión de descargas con Playwright

El botón `descargarZip()` dispara una descarga del navegador. Con Playwright:

```python
async with page.expect_download() as download_info:
    await page.locator('a:has-text("Descargar documentos")').click()
download = await download_info.value
await download.save_as(destino / download.suggested_filename)
```

El nombre sugerido del fichero será el ZIP con los documentos.

---

## 5. Flujo completo resumido para el cliente Playwright

```
1. page.goto("https://extranet.chie.junta-andalucia.es/bandeja/")
   → redirige a SSO

2. Rellenar usuario/contraseña → click "Inicio de sesión"
   → redirige a /bandeja/inicio/accesoSSO.action

3. click "Aceptar" (obligaciones de uso)
   → aparece selector de puesto (si hay más de uno)

4. [Opcional] select#usuarioSeleccionado → opción deseada → click "Acceder"
   → redirige a /modulos/bandejaTrabajo/inicio.action

5. Para cada código del CSV:
   a. Borrar filtro anterior (click "Borrar filtros")
   b. Rellenar input[placeholder="Código..."] con el código
   c. click button#filtrar → esperar a que la tabla se actualice
   d. Doble clic en la fila resultante
   e. Esperar modal: wait_for_selector('text=Información detallada')
   f. async with page.expect_download(): click 'a:has-text("Descargar documentos")'
   g. Guardar fichero en carpeta destino con nombre sugerido
   h. click button "Cerrar"
   i. Registrar resultado (ok/error/sin documentos)
```

---

## 6. Acción "Finalizar comunicación" (opcional)

Accesible desde el modal de Información detallada → desplegable "Más acciones".

### Selectores

```python
# 1. Abrir desplegable
page.get_by_role("button", name="Más acciones").click()

# 2. Click en la opción del dropdown
page.get_by_role("link", name="Finalizar").click()

# 3. Esperar modal de confirmación
#    heading "Finalizar comunicación"
#    text    "¿Está seguro que desea finalizar la comunicación?"
#    button  "VOLVER"    ← cancelar
#    button  "Finalizar" ← confirmar
page.wait_for_selector("text=Finalizar comunicación")

# 4. Confirmar
page.locator('div:has(h4:text("Finalizar comunicación")) button:text("Finalizar")').click()

# 5. Esperar que el modal de confirmación desaparezca
page.wait_for_selector("text=Finalizar comunicación", state="hidden")
```

### Notas
- La acción es **reversible** pero deja trazas en el historial de la comunicación.
- Solo aparece en comunicaciones con estado ASIGNADO (tienen acciones disponibles).
- Se ejecuta **después** de la descarga del ZIP, antes de cerrar el modal principal.

---

## 7. Casos especiales a gestionar

- **Sin documentos**: la tabla de documentos aparece vacía → detectar con `count() == 0` en las filas
- **Spinner de espera**: `img "Espere por favor..."` → esperar a que desaparezca tras filtrar
- **Puesto único**: si solo hay un perfil no aparece el selector de puesto, ir directamente a bandeja
- **Sesión expirada**: detectar redirección a SSO y relanzar login
