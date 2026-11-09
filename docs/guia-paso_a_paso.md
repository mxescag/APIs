
# Plantilla paso a paso: API REST con Node.js y Express

Oct 13, 2026 · @Maxi

Esta plantilla sirve de punto de partida para cualquier API REST con Node.js 20+ y Express 5: copias la estructura, cambias el recurso de ejemplo (`items`) por el tuyo y tienes un CRUD completo con validación y manejo de errores. Se basa en el tema [Introducción a las API REST](https://jbeteta-ies.github.io/2DAW_DWES/U1/U01_04_04/) del curso de Desarrollo de aplicaciones web en el servidor, generalizado y con arquitectura por capas.

## Cómo usar esta plantilla

**Qué incluye**

- estructura de carpetas por capas: rutas, controladores, validadores, repositorio y middlewares;
- un recurso de ejemplo, `items`, con los seis endpoints CRUD (`GET` lista, `GET` uno, `POST`, `PUT`, `PATCH`, `DELETE`);
- códigos de estado coherentes y respuestas de error en JSON con un formato único;
- datos en memoria detrás de un repositorio, para cambiarlos por una base de datos sin tocar el resto;
- un archivo `api.http` para probar cada endpoint.

**Requisitos**

- Node.js 20 o superior y npm.
- Un editor de código; con VS Code, la extensión REST Client para ejecutar `api.http`.
- Conocimientos básicos de JavaScript: funciones, objetos, `async/await` y módulos ES.

**Cómo está escrito el código**

Cada archivo lleva comentarios que explican qué hace cada parte y por qué. Los comentarios marcados con `PERSONALIZAR` señalan lo que debes cambiar al adaptarla a tu API. El último apartado resume esos cambios en una checklist.

## Conceptos clave

| Concepto | Qué es |
| --- | --- |
| HTTP | Protocolo de peticiones y respuestas: método, URL, cabeceras, cuerpo y código de estado |
| API | Contrato que define qué recursos, rutas, datos, respuestas y errores ofrece una aplicación |
| REST | Estilo arquitectónico: recursos con URL propia, métodos según su semántica, peticiones autocontenidas y representaciones, normalmente JSON |
| Recurso | Elemento del dominio (un producto, un usuario); la colección es `/items` y un elemento concreto `/items/1` |

Usar `GET`, `POST`, `PUT` y `DELETE` con JSON no convierte por sí solo una API en REST: también cuentan el diseño de recursos, la semántica de HTTP, la ausencia de estado y la coherencia del contrato.

**Códigos de estado que usa la plantilla**

| Código | Cuándo |
| --- | --- |
| `200` | Lectura o modificación correcta |
| `201` | Recurso creado (con cabecera `Location`) |
| `204` | Recurso eliminado, sin cuerpo |
| `400` | Petición mal formada: JSON inválido o `id` no numérico |
| `404` | Recurso o ruta inexistente |
| `409` | Conflicto: el recurso ya existe |
| `422` | Datos con formato o valores inválidos |
| `500` | Error interno inesperado |

## Paso 1: diseñar el contrato

Antes de programar, decide qué recurso expones y cuál es su contrato. En la plantilla el recurso es `items`; sustitúyelo por el tuyo (`productos`, `usuarios`, `tareas`…).

**Reglas para nombrar rutas**

- usa sustantivos, no verbos;
- usa plurales para las colecciones;
- deja que el método HTTP exprese la acción;
- antepón un prefijo con versión (`/api/v1`) para poder evolucionar la API sin romper a los clientes.

| Evita | Prefiere |
| --- | --- |
| `/getItems` | `GET /api/v1/items` |
| `/crearItem` | `POST /api/v1/items` |
| `/borrarItem/3` | `DELETE /api/v1/items/3` |

**Contrato del recurso de ejemplo**

| Operación | Método | Ruta | Respuestas |
| --- | --- | --- | --- |
| Listar | `GET` | `/api/v1/items` | `200` |
| Consultar uno | `GET` | `/api/v1/items/:id` | `200`, `400`, `404` |
| Crear | `POST` | `/api/v1/items` | `201`, `409`, `422` |
| Sustituir | `PUT` | `/api/v1/items/:id` | `200`, `400`, `404`, `409`, `422` |
| Modificar | `PATCH` | `/api/v1/items/:id` | `200`, `400`, `404`, `409`, `422` |
| Eliminar | `DELETE` | `/api/v1/items/:id` | `204`, `400`, `404` |

**Modelo del recurso**

| Campo | Tipo | Regla |
| --- | --- | --- |
| `id` | entero | Lo genera el servidor; no se envía |
| `nombre` | texto | Obligatorio, hasta 100 caracteres, único |
| `cantidad` | entero | Obligatorio, igual o mayor que 0 |

Si tu recurso tiene un identificador natural (un código de aeropuerto, un DNI), úsalo en lugar de un `id` numérico y valida su formato.

## Paso 2: crear el proyecto y su estructura

Crea la carpeta, inicializa npm e instala Express:

```bash
# Crea la carpeta del proyecto y entra en ella
mkdir mi-api
cd mi-api

# Genera package.json con valores por defecto
npm init -y

# Instala Express (única dependencia necesaria)
npm install express
```

Edita `package.json` para activar los módulos ES y añadir los scripts:

```json
{
  "name": "mi-api",
  "version": "1.0.0",
  // "module" permite usar import/export en lugar de require()
  "type": "module",
  "engines": { "node": ">=20" },
  "scripts": {
    // npm start: arranque normal (producción)
    "start": "node src/server.js",
    // npm run dev: reinicia el servidor al guardar cambios
    "dev": "node --watch src/server.js"
  },
  "dependencies": {
    "express": "^5.0.0"
  }
}
```

El JSON real no admite comentarios: borra las líneas que empiezan por `//` al copiarlo. No cambies a mano la versión de Express; la que instale npm queda fijada en `package-lock.json`.

Crea esta estructura. Cada carpeta es una capa con una única responsabilidad:

```text
mi-api/
├── api.http                       # peticiones de prueba (Paso 9)
├── package.json
└── src/
    ├── server.js                  # arranca el servidor (escucha en un puerto)
    ├── app.js                     # crea y configura la aplicación Express
    ├── config.js                  # configuración leída del entorno
    ├── routes/
    │   ├── index.js               # agrupa los routers de cada recurso
    │   └── items.routes.js        # método + ruta → función del controlador
    ├── controllers/
    │   └── items.controller.js    # lógica HTTP: lee la petición, responde
    ├── validators/
    │   └── items.validator.js     # reglas de validación de los datos
    ├── repositories/
    │   └── items.repository.js    # acceso a los datos (memoria, luego BD)
    └── middlewares/
        ├── notFound.js            # responde 404 a rutas inexistentes
        └── errorHandler.js        # responde a errores inesperados
```

El flujo de una petición es siempre el mismo: **ruta → controlador → validador y repositorio → respuesta**. Si algo falla, el error llega al middleware `errorHandler`.

## Paso 3: configuración, aplicación y servidor

Separa la **aplicación** (`app.js`) de su **arranque** (`server.js`): así puedes importar la app en pruebas automáticas sin abrir un puerto.

**`src/config.js`**

```js
// Punto único de configuración. El resto del código importa este objeto
// en vez de leer process.env por todas partes.
export const config = {
  // Puerto de escucha. Si no existe la variable PORT, usa 3000.
  // PORT llega siempre como texto, por eso se convierte a número.
  port: Number(process.env.PORT ?? 3000),

  // Entorno de ejecución: "development" por defecto.
  nodeEnv: process.env.NODE_ENV ?? "development",

  // PERSONALIZAR: añade aquí más ajustes (URL de la base de datos,
  // claves de API, etc.) leyéndolos siempre de variables de entorno.
};
```

**`src/app.js`**

```js
import express from "express";
import { apiRouter } from "./routes/index.js";
import { notFound } from "./middlewares/notFound.js";
import { errorHandler } from "./middlewares/errorHandler.js";

// Crea la aplicación Express. Se exporta para poder reutilizarla en pruebas.
export const app = express();

// Middleware que lee el cuerpo de las peticiones con JSON y lo deja
// disponible en req.body. DEBE registrarse antes de las rutas.
app.use(express.json());

// Ruta de salud: sirve para comprobar que el servidor está vivo
// (la usan balanceadores y plataformas de despliegue).
app.get("/health", (req, res) => {
  res.status(200).json({ status: "ok" });
});

// Monta todas las rutas de la API bajo el prefijo versionado /api/v1.
app.use("/api/v1", apiRouter);

// Si ninguna ruta anterior respondió, esta petición no existe → 404.
// Debe ir DESPUÉS de todas las rutas.
app.use(notFound);

// Último eslabón: captura cualquier error y responde con un JSON.
// Debe ir el ÚLTIMO de todos.
app.use(errorHandler);
```

**`src/server.js`**

```js
import { app } from "./app.js";
import { config } from "./config.js";

// Abre el puerto y empieza a atender peticiones.
app.listen(config.port, () => {
  console.log(`API disponible en http://localhost:${config.port}`);
});
```

El **orden** de los `app.use` importa: Express los ejecuta de arriba abajo. Primero `express.json()`, luego las rutas, después el 404 y por último el manejador de errores.

## Paso 4: las rutas

Las rutas solo **conectan** un método y una URL con una función del controlador; no contienen lógica. Hay un router por recurso y un router general que los agrupa.

**`src/routes/index.js`**

```js
import { Router } from "express";
import { itemsRouter } from "./items.routes.js";

// Router principal de la API: agrupa los routers de cada recurso.
export const apiRouter = Router();

// Todo lo que empiece por /items se delega en itemsRouter.
// Con el prefijo de app.js, la ruta completa es /api/v1/items.
apiRouter.use("/items", itemsRouter);

// PERSONALIZAR: registra aquí cada recurso nuevo, por ejemplo:
// apiRouter.use("/usuarios", usuariosRouter);
```

**`src/routes/items.routes.js`**

```js
import { Router } from "express";
import {
  crear,
  eliminar,
  listar,
  modificar,
  obtener,
  sustituir
} from "../controllers/items.controller.js";

export const itemsRouter = Router();

// Las rutas son relativas a /items (ya montado en routes/index.js).

itemsRouter.get("/", listar);            // GET    /items      → lista (admite ?nombre=)
itemsRouter.get("/:id", obtener);        // GET    /items/:id  → un elemento
itemsRouter.post("/", crear);            // POST   /items      → crea
itemsRouter.put("/:id", sustituir);      // PUT    /items/:id  → reemplaza completo
itemsRouter.patch("/:id", modificar);    // PATCH  /items/:id  → cambia solo algunos campos
itemsRouter.delete("/:id", eliminar);    // DELETE /items/:id  → borra
```

`:id` es un **parámetro de ruta**: Express lo expone como `req.params.id` y siempre llega como texto.

## Paso 5: el controlador

El controlador traduce entre HTTP y tu lógica: lee `req.params`, `req.query` y `req.body`, llama al validador y al repositorio, y elige el código de estado. Las funciones son `async` para que cambiar a una base de datos no exija reescribirlas. En Express 5, si una función `async` lanza un error, este llega solo al middleware de errores, sin `try/catch`.

Construye el archivo en tres bloques.

**5.1 Importaciones y funciones auxiliares**

```js
// src/controllers/items.controller.js
import { itemsRepository as repo } from "../repositories/items.repository.js";
import {
  seleccionarCampos,
  validarItem
} from "../validators/items.validator.js";

// Convierte el id de la URL (texto) en un entero positivo.
// Devuelve null si no es válido ("abc", "1.5", "0", "-3"...).
function parsearId(valor) {
  const id = Number(valor);
  return Number.isInteger(id) && id > 0 ? id : null;
}

// Respuestas de error repetidas, centralizadas para que todas
// tengan el mismo formato: { error, details? }.
const idInvalido = (res) =>
  res.status(400).json({ error: "El id debe ser un entero positivo" });

const noEncontrado = (res) =>
  res.status(404).json({ error: "Item no encontrado" });

const datosInvalidos = (res, errores) =>
  res.status(422).json({ error: "Datos no válidos", details: errores });

const duplicado = (res) =>
  res.status(409).json({ error: "Ya existe un item con ese nombre" });
```

**5.2 Lectura: listar y obtener uno**

```js
// GET /items  (opcional: ?nombre=texto para filtrar)
export async function listar(req, res) {
  // req.query contiene los parámetros de consulta (?clave=valor).
  // Solo se usa si llega como texto; si no, se ignora el filtro.
  const nombre =
    typeof req.query.nombre === "string"
      ? req.query.nombre.trim().toLowerCase()
      : undefined;

  const items = await repo.findAll({ nombre });

  return res.status(200).json(items);
}

// GET /items/:id
export async function obtener(req, res) {
  const id = parsearId(req.params.id);
  if (id === null) return idInvalido(res);        // 400

  const item = await repo.findById(id);
  if (!item) return noEncontrado(res);            // 404

  return res.status(200).json(item);              // 200
}
```

**5.3 Escritura: crear, sustituir, modificar y eliminar**

```js
// POST /items
export async function crear(req, res) {
  // Se queda solo con los campos permitidos: ignora cualquier otro
  // que envíe el cliente (por ejemplo, un id o campos ajenos al modelo).
  const datos = seleccionarCampos(req.body);

  const errores = validarItem(datos);
  if (errores.length > 0) return datosInvalidos(res, errores);   // 422

  datos.nombre = datos.nombre.trim();

  // El nombre debe ser único.
  if (await repo.findByNombre(datos.nombre)) return duplicado(res);   // 409

  const creado = await repo.create(datos);

  // 201 Created + cabecera Location con la URL del nuevo recurso.
  // req.baseUrl vale /api/v1/items
  return res
    .status(201)
    .location(`${req.baseUrl}/${creado.id}`)
    .json(creado);
}

// PUT /items/:id → sustituye el recurso completo
export async function sustituir(req, res) {
  const id = parsearId(req.params.id);
  if (id === null) return idInvalido(res);

  // Primero se comprueba que existe; después se validan los datos.
  if (!(await repo.findById(id))) return noEncontrado(res);

  const datos = seleccionarCampos(req.body);

  // En PUT deben venir TODOS los campos obligatorios.
  const errores = validarItem(datos);
  if (errores.length > 0) return datosInvalidos(res, errores);

  datos.nombre = datos.nombre.trim();

  // Duplicado solo si el nombre pertenece a OTRO item.
  const otro = await repo.findByNombre(datos.nombre);
  if (otro && otro.id !== id) return duplicado(res);

  const actualizado = await repo.replace(id, datos);
  return res.status(200).json(actualizado);
}

// PATCH /items/:id → modifica solo los campos enviados
export async function modificar(req, res) {
  const id = parsearId(req.params.id);
  if (id === null) return idInvalido(res);

  if (!(await repo.findById(id))) return noEncontrado(res);

  const cambios = seleccionarCampos(req.body);

  // parcial: true → solo se validan los campos presentes
  // y se exige que haya al menos uno.
  const errores = validarItem(cambios, { parcial: true });
  if (errores.length > 0) return datosInvalidos(res, errores);

  if ("nombre" in cambios) {
    cambios.nombre = cambios.nombre.trim();
    const otro = await repo.findByNombre(cambios.nombre);
    if (otro && otro.id !== id) return duplicado(res);
  }

  const actualizado = await repo.update(id, cambios);
  return res.status(200).json(actualizado);
}

// DELETE /items/:id
export async function eliminar(req, res) {
  const id = parsearId(req.params.id);
  if (id === null) return idInvalido(res);

  const eliminado = await repo.remove(id);
  if (!eliminado) return noEncontrado(res);

  // 204 No Content: éxito y sin cuerpo en la respuesta.
  return res.status(204).send();
}
```

En `PUT` se reemplaza el recurso entero; en `PATCH` solo cambian los campos recibidos. Al comprobar si un campo llegó, usa `"campo" in objeto` y no `||`, porque este último descarta valores válidos como `0`.

## Paso 6: la validación

Nunca confíes en que el cliente enviará datos correctos. El validador comprueba presencia, tipo, formato y rango, y devuelve una **lista de mensajes de error** (vacía si todo es correcto). Esta versión es manual y sirve para entender el principio; más adelante puedes sustituirla por una biblioteca de validación.

**`src/validators/items.validator.js`**

```js
// PERSONALIZAR: lista de campos que el cliente PUEDE enviar.
// El id no está: lo genera el servidor.
const CAMPOS_PERMITIDOS = ["nombre", "cantidad"];

// Copia solo los campos permitidos del cuerpo recibido.
// Protege de que el cliente cuele campos que no debe controlar.
// Si el cuerpo no es un objeto (o no existe), devuelve un objeto vacío.
export function seleccionarCampos(origen) {
  const resultado = {};

  if (typeof origen !== "object" || origen === null) return resultado;

  for (const campo of CAMPOS_PERMITIDOS) {
    if (campo in origen) resultado[campo] = origen[campo];
  }

  return resultado;
}

// Valida los datos de un item y devuelve un array de mensajes de error.
//   parcial = false → creación y PUT: todos los campos son obligatorios.
//   parcial = true  → PATCH: solo se validan los campos presentes.
export function validarItem(datos, { parcial = false } = {}) {
  const errores = [];

  // nombre: texto no vacío de hasta 100 caracteres
  if (!parcial || "nombre" in datos) {
    if (typeof datos.nombre !== "string" || datos.nombre.trim() === "") {
      errores.push("El nombre es obligatorio");
    } else if (datos.nombre.trim().length > 100) {
      errores.push("El nombre no puede superar los 100 caracteres");
    }
  }

  // cantidad: entero igual o mayor que 0
  if (!parcial || "cantidad" in datos) {
    if (!Number.isInteger(datos.cantidad) || datos.cantidad < 0) {
      errores.push("La cantidad debe ser un entero igual o superior a cero");
    }
  }

  // En PATCH no tiene sentido una petición sin ningún campo.
  if (parcial && Object.keys(datos).length === 0) {
    errores.push("Debe enviarse al menos un campo");
  }

  return errores;
}
```

Para tu recurso, cambia `CAMPOS_PERMITIDOS` y añade un bloque `if` por campo. Los patrones más habituales: texto obligatorio, número entero, número con decimales (`Number.isFinite`), formato con expresión regular (`/^[A-Z]{3}$/.test(valor)`) y valor dentro de una lista (`["a", "b"].includes(valor)`).

## Paso 7: el repositorio de datos

El repositorio es la **única capa que sabe dónde se guardan los datos**. Ahora usa un array en memoria, así que todo se pierde al reiniciar el servidor. Para pasar a una base de datos solo reescribes este archivo: el controlador seguirá llamando a los mismos métodos. Por eso todos son `async`.

**`src/repositories/items.repository.js`**

```js
// "Base de datos" en memoria. PERSONALIZAR: datos de partida de tu recurso.
const items = [
  { id: 1, nombre: "Ejemplo A", cantidad: 10 },
  { id: 2, nombre: "Ejemplo B", cantidad: 5 }
];

// Contador para asignar ids nuevos (una BD lo haría con autoincremento).
let siguienteId = 3;

// Busca la posición de un id en el array (-1 si no existe).
const indiceDe = (id) => items.findIndex((item) => item.id === id);

export const itemsRepository = {
  // Devuelve todos los items; si llega nombre, filtra los que lo contienen
  // (sin distinguir mayúsculas).
  async findAll({ nombre } = {}) {
    if (!nombre) return items;
    return items.filter((item) => item.nombre.toLowerCase().includes(nombre));
  },

  // Devuelve el item con ese id, o undefined si no existe.
  async findById(id) {
    return items.find((item) => item.id === id);
  },

  // Devuelve el item con ese nombre exacto (sin distinguir mayúsculas),
  // o undefined. Se usa para comprobar duplicados.
  async findByNombre(nombre) {
    const buscado = nombre.toLowerCase();
    return items.find((item) => item.nombre.toLowerCase() === buscado);
  },

  // Crea un item nuevo con el siguiente id y lo devuelve.
  async create(datos) {
    const nuevo = { id: siguienteId++, ...datos };
    items.push(nuevo);
    return nuevo;
  },

  // Sustituye por completo el item (conserva el id).
  // Devuelve el item actualizado, o null si no existe.
  async replace(id, datos) {
    const indice = indiceDe(id);
    if (indice === -1) return null;

    items[indice] = { id, ...datos };
    return items[indice];
  },

  // Cambia solo los campos recibidos y deja el resto como estaba.
  // Devuelve el item actualizado, o null si no existe.
  async update(id, cambios) {
    const indice = indiceDe(id);
    if (indice === -1) return null;

    items[indice] = { ...items[indice], ...cambios };
    return items[indice];
  },

  // Elimina el item. Devuelve true si existía y false si no.
  async remove(id) {
    const indice = indiceDe(id);
    if (indice === -1) return false;

    items.splice(indice, 1);
    return true;
  }
};
```

## Paso 8: middlewares de 404 y de errores

Distingue dos tipos de error:

- **Esperados** (datos inválidos, recurso inexistente, duplicado): el controlador responde con el código adecuado.
- **Inesperados** (fallo de base de datos, error de programación): llegan al middleware de errores, que responde `500` sin revelar detalles internos.

**`src/middlewares/notFound.js`**

```js
// Se ejecuta solo si ninguna ruta anterior atendió la petición.
// Un middleware normal recibe (req, res, next).
export function notFound(req, res) {
  res.status(404).json({
    error: `Ruta no encontrada: ${req.method} ${req.originalUrl}`
  });
}
```

**`src/middlewares/errorHandler.js`**

```js
// Manejador de errores: Express lo reconoce por tener 4 parámetros.
// Debe declararse con los 4 aunque "next" no se use.
export function errorHandler(error, req, res, next) {
  // Si la respuesta ya empezó a enviarse, no se puede cambiar:
  // se delega en el manejador por defecto de Express.
  if (res.headersSent) return next(error);

  // express.json() produce este tipo de error cuando el JSON
  // recibido está mal formado (llaves sin cerrar, comas de más...).
  if (error.type === "entity.parse.failed") {
    return res.status(400).json({ error: "El cuerpo JSON no es válido" });
  }

  // Cuerpo demasiado grande (el límite por defecto es 100 kb).
  if (error.type === "entity.too.large") {
    return res.status(413).json({ error: "El cuerpo es demasiado grande" });
  }

  // Cualquier otro error es inesperado: el detalle se registra en el
  // servidor, pero al cliente solo se le da un mensaje genérico.
  // Nunca envíes trazas, rutas locales, consultas SQL ni credenciales.
  console.error(error);
  return res.status(500).json({ error: "Error interno del servidor" });
}
```

Todas las respuestas de error comparten el formato `{ "error": "mensaje" }` (más `details` en los `422`), lo que simplifica el trabajo de quien consuma tu API.

## Paso 9: arrancar y probar

Arranca el servidor con `npm run dev`. Verás `API disponible en http://localhost:3000`.

Crea `api.http` en la raíz. Con la extensión REST Client de VS Code aparece un enlace *Send Request* sobre cada petición; también puedes usar Postman.

```http
# Variable reutilizable: cambia aquí la dirección base
@baseUrl = http://localhost:3000/api/v1

### Comprobar que el servidor está vivo
GET http://localhost:3000/health

### Listar items
GET {{baseUrl}}/items
Accept: application/json

### Filtrar por nombre (parámetro de consulta)
GET {{baseUrl}}/items?nombre=ejemplo
Accept: application/json

### Consultar un item
GET {{baseUrl}}/items/1
Accept: application/json

### Crear un item → 201 + cabecera Location
POST {{baseUrl}}/items
Content-Type: application/json
Accept: application/json

{
  "nombre": "Ejemplo C",
  "cantidad": 20
}

### Sustituir un item (todos los campos obligatorios)
PUT {{baseUrl}}/items/3
Content-Type: application/json
Accept: application/json

{
  "nombre": "Ejemplo C v2",
  "cantidad": 25
}

### Modificar solo la cantidad
PATCH {{baseUrl}}/items/3
Content-Type: application/json
Accept: application/json

{
  "cantidad": 30
}

### Eliminar un item → 204 sin cuerpo
DELETE {{baseUrl}}/items/3
```

En cada petición comprueba método, URL, cabeceras, cuerpo, código de estado, respuesta y efecto sobre los datos (por ejemplo, que un `GET` posterior ya no devuelva el item eliminado).

**Casos de error que conviene probar siempre**

| Petición | Resultado esperado |
| --- | --- |
| `POST` con un nombre ya existente | `409` |
| `POST` con nombre vacío o cantidad negativa | `422` con `details` |
| `POST` con JSON mal formado | `400` |
| `GET /items/abc` | `400` |
| `GET /items/999` | `404` |
| `PATCH` con cuerpo vacío `{}` | `422` |
| `GET /ruta-que-no-existe` | `404` |

## Adaptar la plantilla a una API nueva

**Checklist para un recurso nuevo** (por ejemplo `productos`)

1. Define el contrato: rutas, campos, reglas y códigos de respuesta (Paso 1).
2. Copia el proyecto y cambia el nombre en `package.json`.
3. Duplica los cuatro archivos de `items` con el nombre de tu recurso: `routes`, `controllers`, `validators` y `repositories`.
4. Busca los comentarios `PERSONALIZAR` y ajusta campos permitidos, reglas de validación y datos de partida.
5. Cambia mensajes y nombres de funciones (`Item no encontrado`, `validarItem`…).
6. Registra el router nuevo en `src/routes/index.js`.
7. Actualiza `api.http` y prueba cada endpoint, incluidos los casos de error.

**Qué cambia y qué se queda igual**

| Cambia con cada API | Se reutiliza tal cual |
| --- | --- |
| Nombre del recurso y sus rutas | `server.js`, `app.js` y `config.js` |
| Campos y reglas de validación | Middlewares `notFound` y `errorHandler` |
| Datos de partida del repositorio | Formato de errores y códigos de estado |
| Mensajes de error del controlador | Estructura por capas |

**Subrecursos**

Para relaciones como `/items/:id/comentarios`, crea un router con `Router({ mergeParams: true })` para que lea `req.params.id` del router padre, y móntalo dentro de `items.routes.js` con `itemsRouter.use("/:id/comentarios", comentariosRouter)`. Comprueba siempre primero que el recurso padre existe y devuelve `404` si no.

**Límites de la persistencia en memoria**

Los datos desaparecen al reiniciar. Guardarlos en un archivo JSON tampoco escala: se reescribe el archivo completo, hay condiciones de carrera y no hay transacciones. Úsalo, como mucho, de transición.

**Siguientes pasos**

- sustituir el repositorio por uno con base de datos (por ejemplo MySQL o PostgreSQL), manteniendo los mismos métodos;
- mover la configuración (puerto, conexión) a variables de entorno;
- añadir autenticación y rutas protegidas con middleware;
- añadir paginación y ordenación con parámetros de consulta (`?page=1&limit=20&sort=nombre`);
- escribir pruebas automáticas importando `app` sin llamar a `listen`;
- cambiar la validación manual por una biblioteca de validación.
