# Plantilla reutilizable: API REST con Node.js y Express

Oct 13, 2026 · @Maxi

Esqueleto de API REST con Express 5 y módulos ES que sirve de punto de partida para cualquier recurso: se cambia `tareas` por tu dominio y el resto se mantiene.

## Cómo usar esta plantilla

Copia la estructura, ejecuta los comandos de la puesta en marcha y sustituye el recurso de ejemplo `tareas` por el tuyo. El núcleo (configuración, errores, middlewares, `app.js`, `server.js`) no cambia de un proyecto a otro.

**Qué sustituir en cada proyecto**

| Elemento de ejemplo | Cámbialo por |
| --- | --- |
| `tareas`, `tarea` | El nombre de tu recurso, en plural y singular |
| Campos `titulo`, `completada` | Los campos de tu recurso |
| `/api/v1` | Tu prefijo y versión (variable `API_PREFIX`) |
| Repositorio en memoria | Tu base de datos, sin tocar el resto del código |

**Recorrido de una petición**

1. `app.js` recibe la petición y `express.json()` convierte el cuerpo en `req.body`.
2. El router de `routes/` encuentra la ruta que coincide con método y URL.
3. El middleware `validate` comprueba el cuerpo; si es inválido lanza un `422`.
4. El controlador aplica la lógica y llama al repositorio, que es el único que toca los datos.
5. El controlador responde con el código de estado y el JSON adecuados.
6. Si algo lanza un error en cualquier punto, `errorHandler` lo convierte en una respuesta JSON uniforme.

Express 5 captura por sí solo las excepciones y las promesas rechazadas de los manejadores, por eso los controladores pueden lanzar errores con `throw` sin `try/catch`.

## Estructura de carpetas

El código se organiza por capas: cada carpeta tiene una responsabilidad y solo conoce a la capa inferior. Añadir un recurso nuevo significa añadir un archivo en cada carpeta, sin tocar el núcleo.

```text
mi-api/
├── src/
│   ├── server.js                  # Arranca el servidor (puerto, cierre ordenado)
│   ├── app.js                     # Crea la app Express y registra middlewares y rutas
│   ├── config/
│   │   └── env.js                 # Lee y valida variables de entorno una sola vez
│   ├── routes/
│   │   ├── index.js               # Agrupa todos los routers bajo el prefijo /api/v1
│   │   └── tareas.routes.js       # Método + URL -> middlewares + controlador
│   ├── controllers/
│   │   └── tareas.controller.js   # Lógica HTTP: lee la petición y elige la respuesta
│   ├── repositories/
│   │   └── tareas.repository.js   # Acceso a datos (hoy memoria, mañana base de datos)
│   ├── validators/
│   │   └── tareas.validator.js    # Reglas de validación del recurso
│   ├── middlewares/
│   │   ├── validate.js            # Aplica un validador al cuerpo de la petición
│   │   ├── notFound.js            # Responde 404 a rutas inexistentes
│   │   └── errorHandler.js        # Convierte cualquier error en una respuesta JSON
│   └── utils/
│       └── AppError.js            # Error con código de estado HTTP
├── api.http                       # Peticiones de prueba (extensión REST Client)
├── .env.example                   # Plantilla de variables de entorno (se sube a git)
├── .env                           # Valores reales (NO se sube a git)
├── .gitignore
└── package.json
```

**Reglas de dependencia**

- `routes` conoce a `controllers`, `middlewares` y `validators`.
- `controllers` conoce a `repositories` y `utils`, pero no a Express más allá de `req` y `res`.
- `repositories` no sabe nada de HTTP: reciben y devuelven objetos JavaScript.
- Si la lógica de negocio crece, añade una capa `services/` entre controladores y repositorios.

## Puesta en marcha

Requiere Node.js 20.6 o superior, por la opción `--env-file` que carga el archivo `.env` sin instalar nada más.

```bash
# 1. Crear la carpeta del proyecto y entrar en ella
mkdir mi-api && cd mi-api

# 2. Generar package.json con valores por defecto
npm init -y

# 3. Instalar Express (única dependencia de ejecución)
npm install express

# 4. Crear la estructura de carpetas
mkdir -p src/{config,routes,controllers,repositories,validators,middlewares,utils}

# 5. Crear los archivos vacíos que rellenarás con el código de esta plantilla
touch src/{app,server}.js \
      src/config/env.js \
      src/routes/{index,tareas.routes}.js \
      src/controllers/tareas.controller.js \
      src/repositories/tareas.repository.js \
      src/validators/tareas.validator.js \
      src/middlewares/{validate,notFound,errorHandler}.js \
      src/utils/AppError.js \
      api.http .env.example .gitignore

# 6. Copiar la plantilla de variables a tu .env local
cp .env.example .env
```

**`package.json`**

```json
{
  "name": "mi-api",
  "version": "1.0.0",
  "type": "module",
  "engines": { "node": ">=20.6" },
  "scripts": {
    "start": "node --env-file=.env src/server.js",
    "dev": "node --watch --env-file=.env src/server.js"
  },
  "dependencies": {
    "express": "^5.0.0"
  }
}
```

El JSON no admite comentarios, así que aquí van aparte:

| Clave | Para qué sirve |
| --- | --- |
| `"type": "module"` | Activa `import`/`export` (módulos ES) en todos los `.js` |
| `"engines"` | Documenta la versión mínima de Node que necesita el proyecto |
| `"start"` | Arranque para producción: `npm start` |
| `"dev"` | Arranque para desarrollo: reinicia el servidor al guardar un archivo |
| `--env-file=.env` | Carga las variables de `.env` en `process.env` antes de ejecutar |
| `"express"` | Framework HTTP; npm fija la versión exacta en `package-lock.json` |

**`.env.example`**

```bash
# Entorno de ejecución: development | production | test
NODE_ENV=development
# Puerto donde escucha el servidor
PORT=3000
# Prefijo (y versión) de todas las rutas de la API
API_PREFIX=/api/v1
```

**`.gitignore`**

```bash
# Dependencias: se reinstalan con npm install
node_modules/
# Valores reales y posiblemente secretos: nunca se suben
.env
```

Arranca con `npm run dev` y comprueba que aparece el mensaje de servidor disponible.

## Núcleo reutilizable

Estos archivos son idénticos en cualquier API. Cópialos tal cual.

**`src/config/env.js`**

```js
// Centraliza la lectura de variables de entorno. El resto de la app importa
// `config` y nunca toca `process.env` directamente.

const NODE_ENV = process.env.NODE_ENV ?? "development";

// process.env siempre guarda texto: hay que convertirlo a número
const PORT = Number(process.env.PORT ?? 3000);

// Falla al arrancar (no más tarde) si la configuración es incorrecta
if (!Number.isInteger(PORT) || PORT <= 0) {
  throw new Error(`PORT no válido: ${process.env.PORT}`);
}

// Object.freeze impide modificar la configuración por accidente
export const config = Object.freeze({
  env: NODE_ENV,
  isProduction: NODE_ENV === "production",
  port: PORT,
  apiPrefix: process.env.API_PREFIX ?? "/api/v1"
});
```

**`src/utils/AppError.js`**

```js
// Error con código de estado HTTP. Los controladores lo lanzan con `throw`
// y errorHandler lo convierte en la respuesta JSON.
export class AppError extends Error {
  constructor(status, message, details) {
    super(message);
    this.name = "AppError";
    this.status = status;   // Código HTTP: 404, 409, 422...
    this.details = details; // Opcional: lista de problemas concretos
  }

  // Atajos para los errores más habituales
  static notFound(message = "Recurso no encontrado") {
    return new AppError(404, message);
  }

  static conflict(message = "El recurso ya existe") {
    return new AppError(409, message);
  }

  static unprocessable(details, message = "Datos no válidos") {
    return new AppError(422, message, details);
  }
}
```

**`src/middlewares/validate.js`**

```js
import { AppError } from "../utils/AppError.js";

// Fábrica de middlewares: recibe una función validadora y devuelve un
// middleware que la ejecuta sobre req.body antes de llegar al controlador.
// `opciones` se pasa tal cual al validador (por ejemplo { parcial: true }).
export function validate(validador, opciones = {}) {
  return (req, res, next) => {
    const cuerpo = req.body;

    // Sin cuerpo (undefined), null, un array o un valor simple: no es un objeto JSON
    if (cuerpo === null || typeof cuerpo !== "object" || Array.isArray(cuerpo)) {
      throw AppError.unprocessable(["El cuerpo debe ser un objeto JSON"]);
    }

    // El validador devuelve una lista de mensajes; vacía significa válido
    const errores = validador(cuerpo, opciones);

    if (errores.length > 0) {
      throw AppError.unprocessable(errores);
    }

    next(); // Todo correcto: pasa al siguiente middleware o al controlador
  };
}
```

**`src/middlewares/notFound.js`**

```js
// Se registra DESPUÉS de todas las rutas: si ninguna respondió, llega aquí.
export function notFound(req, res) {
  res.status(404).json({
    error: `Ruta no encontrada: ${req.method} ${req.originalUrl}`
  });
}
```

**`src/middlewares/errorHandler.js`**

```js
import { AppError } from "../utils/AppError.js";

// Express reconoce un manejador de errores por sus 4 parámetros,
// aunque no uses `next`. Debe registrarse el último.
export function errorHandler(error, req, res, next) {
  // Si ya se empezó a enviar la respuesta, Express debe cerrarla él
  if (res.headersSent) {
    return next(error);
  }

  // 1. Errores esperados, lanzados por nuestro código con AppError
  if (error instanceof AppError) {
    return res.status(error.status).json({
      error: error.message,
      ...(error.details && { details: error.details })
    });
  }

  // 2. Errores del cliente generados por Express al leer el cuerpo
  //    (JSON mal formado, cuerpo demasiado grande...): traen status 4xx
  if (error.expose && error.status >= 400 && error.status < 500) {
    const mensaje =
      error.type === "entity.parse.failed"
        ? "El cuerpo JSON no es válido"
        : error.message;

    return res.status(error.status).json({ error: mensaje });
  }

  // 3. Cualquier otro error es inesperado: se registra en el servidor
  //    y el cliente solo recibe un mensaje genérico (sin trazas ni datos internos)
  console.error(error);
  return res.status(500).json({ error: "Error interno del servidor" });
}
```

**`src/app.js`**

```js
import express from "express";
import { config } from "./config/env.js";
import { apiRouter } from "./routes/index.js";
import { notFound } from "./middlewares/notFound.js";
import { errorHandler } from "./middlewares/errorHandler.js";

// Se exporta la app sin arrancarla para poder probarla sin abrir un puerto
export const app = express();

// No revela en las cabeceras que se usa Express
app.disable("x-powered-by");

// Convierte el cuerpo JSON en req.body. Debe ir ANTES de las rutas.
// `limit` evita cuerpos enormes.
app.use(express.json({ limit: "100kb" }));

// Ruta de salud: la usan monitores y plataformas de despliegue
app.get("/health", (req, res) => {
  res.status(200).json({ status: "ok" });
});

// Todas las rutas de la API cuelgan del prefijo, por ejemplo /api/v1/tareas
app.use(config.apiPrefix, apiRouter);

// El orden importa: primero 404 y, al final de todo, el manejador de errores
app.use(notFound);
app.use(errorHandler);
```

**`src/server.js`**

```js
import { app } from "./app.js";
import { config } from "./config/env.js";

// Arranca el servidor HTTP en el puerto configurado
const server = app.listen(config.port, () => {
  console.log(
    `API (${config.env}) en http://localhost:${config.port}${config.apiPrefix}`
  );
});

// Cierre ordenado: deja de aceptar conexiones nuevas, termina las que están
// en curso y entonces sale. Lo usan Ctrl+C (SIGINT) y los orquestadores (SIGTERM).
function apagar(senal) {
  console.log(`${senal} recibido: cerrando el servidor...`);
  server.close(() => process.exit(0));
}

process.on("SIGINT", apagar);
process.on("SIGTERM", apagar);
```

## Recurso de ejemplo: tareas

Estos cuatro archivos son los que se copian y se renombran por cada recurso nuevo. La tarea tiene `id` (lo genera el servidor), `titulo` (texto obligatorio), `completada` (booleano, `false` por defecto) y `creadaEn` (fecha ISO).

**`src/validators/tareas.validator.js`**

```js
// Un validador es una función pura: recibe datos y devuelve una lista de
// mensajes de error. Lista vacía = datos válidos. No conoce Express.
//
// parcial = false -> POST y PUT: los campos obligatorios deben venir
// parcial = true  -> PATCH: solo se validan los campos que llegan
export function validarTarea(datos, { parcial = false } = {}) {
  const errores = [];

  if (!parcial || "titulo" in datos) {
    if (typeof datos.titulo !== "string" || datos.titulo.trim() === "") {
      errores.push("El título es obligatorio");
    } else if (datos.titulo.trim().length > 100) {
      errores.push("El título admite como máximo 100 caracteres");
    }
  }

  // Opcional: si viene, debe ser booleano (no el texto "true")
  if ("completada" in datos && typeof datos.completada !== "boolean") {
    errores.push("completada debe ser true o false");
  }

  // Un PATCH vacío no cambiaría nada
  if (parcial && Object.keys(datos).length === 0) {
    errores.push("Debe enviarse al menos un campo");
  }

  return errores;
}
```

**`src/repositories/tareas.repository.js`**

```js
import { randomUUID } from "node:crypto";

// Almacén temporal en memoria. Un Map (id -> tarea) busca y borra por id
// sin recorrer todo el array. Los datos se pierden al reiniciar.
const tareas = new Map();

// Contrato del repositorio: cuando pases a una base de datos, reescribe
// SOLO este archivo manteniendo los mismos métodos y resultados.
// Los métodos son async porque una base de datos real lo será.
// Devuelven null (o false) si el recurso no existe; decidir qué hacer
// en ese caso (404) es cosa del controlador.
export const tareasRepository = {
  // Lista todas las tareas; opcionalmente filtra por `completada`
  async findAll({ completada } = {}) {
    const todas = [...tareas.values()];
    return completada === undefined
      ? todas
      : todas.filter((t) => t.completada === completada);
  },

  // Devuelve la tarea con ese id, o null
  async findById(id) {
    return tareas.get(id) ?? null;
  },

  // Crea una tarea; el id y la fecha los genera el servidor, no el cliente
  async create({ titulo, completada = false }) {
    const tarea = {
      id: randomUUID(),
      titulo,
      completada,
      creadaEn: new Date().toISOString()
    };
    tareas.set(tarea.id, tarea);
    return tarea;
  },

  // Sustituye los campos editables; conserva id y creadaEn. Devuelve null si no existe
  async replace(id, { titulo, completada = false }) {
    const actual = tareas.get(id);
    if (!actual) return null;

    const nueva = { ...actual, titulo, completada };
    tareas.set(id, nueva);
    return nueva;
  },

  // Cambia solo los campos recibidos. Devuelve null si no existe
  async update(id, cambios) {
    const actual = tareas.get(id);
    if (!actual) return null;

    const nueva = { ...actual, ...cambios };
    tareas.set(id, nueva);
    return nueva;
  },

  // Borra la tarea. Devuelve true si existía y false si no
  async remove(id) {
    return tareas.delete(id);
  }
};
```

**`src/controllers/tareas.controller.js`**

```js
import { AppError } from "../utils/AppError.js";
import { tareasRepository as repo } from "../repositories/tareas.repository.js";

// Lista blanca de campos que el cliente puede enviar. Así no puede
// colarnos `id`, `creadaEn` ni ningún otro campo que no queramos aceptar.
const CAMPOS = ["titulo", "completada"];

// Copia solo los campos permitidos que vengan en el cuerpo y recorta
// los espacios sobrantes de los textos.
function extraerCampos(cuerpo) {
  const datos = {};
  for (const campo of CAMPOS) {
    if (campo in cuerpo) {
      datos[campo] =
        typeof cuerpo[campo] === "string" ? cuerpo[campo].trim() : cuerpo[campo];
    }
  }
  return datos;
}

// GET /tareas?completada=true
export async function listar(req, res) {
  const filtros = {};

  // Los parámetros de consulta siempre llegan como texto
  if (req.query.completada !== undefined) {
    if (!["true", "false"].includes(req.query.completada)) {
      throw AppError.unprocessable(["completada debe ser true o false"]);
    }
    filtros.completada = req.query.completada === "true";
  }

  res.status(200).json(await repo.findAll(filtros));
}

// GET /tareas/:id  (el id de la URL está en req.params)
export async function obtener(req, res) {
  const tarea = await repo.findById(req.params.id);

  if (!tarea) throw AppError.notFound("Tarea no encontrada");

  res.status(200).json(tarea);
}

// POST /tareas
export async function crear(req, res) {
  // Si algún campo debiera ser único, comprueba aquí y lanza
  // AppError.conflict("...") para responder 409.
  const tarea = await repo.create(extraerCampos(req.body));

  // 201 Created + cabecera Location con la URL del recurso nuevo.
  // req.baseUrl vale "/api/v1/tareas": el prefijo donde está montado el router.
  res.status(201).location(`${req.baseUrl}/${tarea.id}`).json(tarea);
}

// PUT /tareas/:id  (reemplazo completo)
export async function sustituir(req, res) {
  const tarea = await repo.replace(req.params.id, extraerCampos(req.body));

  if (!tarea) throw AppError.notFound("Tarea no encontrada");

  res.status(200).json(tarea);
}

// PATCH /tareas/:id  (cambio parcial)
export async function modificar(req, res) {
  const tarea = await repo.update(req.params.id, extraerCampos(req.body));

  if (!tarea) throw AppError.notFound("Tarea no encontrada");

  res.status(200).json(tarea);
}

// DELETE /tareas/:id
export async function eliminar(req, res) {
  const existia = await repo.remove(req.params.id);

  if (!existia) throw AppError.notFound("Tarea no encontrada");

  // 204 No Content: éxito sin cuerpo en la respuesta
  res.status(204).send();
}
```

**`src/routes/tareas.routes.js`**

```js
import { Router } from "express";
import { validate } from "../middlewares/validate.js";
import { validarTarea } from "../validators/tareas.validator.js";
import {
  crear,
  eliminar,
  listar,
  modificar,
  obtener,
  sustituir
} from "../controllers/tareas.controller.js";

export const tareasRouter = Router();

// Cada línea: método + ruta relativa -> [middlewares] -> controlador.
// Las rutas son relativas al punto donde se monta el router (/api/v1/tareas).
tareasRouter.get("/", listar);
tareasRouter.get("/:id", obtener);

// validate se ejecuta antes del controlador y corta la petición si hay errores
tareasRouter.post("/", validate(validarTarea), crear);
tareasRouter.put("/:id", validate(validarTarea), sustituir);
tareasRouter.patch("/:id", validate(validarTarea, { parcial: true }), modificar);

tareasRouter.delete("/:id", eliminar);
```

**`src/routes/index.js`**

```js
import { Router } from "express";
import { tareasRouter } from "./tareas.routes.js";

// Punto único donde se monta cada recurso. Para añadir uno nuevo,
// importa su router y regístralo con su ruta.
export const apiRouter = Router();

apiRouter.use("/tareas", tareasRouter);
// apiRouter.use("/usuarios", usuariosRouter);
```

En `PUT` y `PATCH`, un cuerpo inválido da `422` antes de comprobar si la tarea existe. Es una decisión de diseño habitual y aceptable.

## Pruebas con api.http

Guarda este archivo en la raíz y ábrelo en VS Code con la extensión REST Client; aparece *Send Request* sobre cada petición. Las peticiones se ejecutan de arriba abajo y la primera guarda el `id` de la tarea creada para reutilizarlo en las siguientes.

```http
# Variable de archivo: cambia aquí el servidor y el prefijo para todo el archivo
@baseUrl = http://localhost:3000/api/v1

### Salud del servicio
GET http://localhost:3000/health

### Crear una tarea
# @name crear
POST {{baseUrl}}/tareas
Content-Type: application/json

{
  "titulo": "Aprender Express"
}

### Guarda el id devuelto por la petición anterior (nombrada "crear")
@id = {{crear.response.body.id}}

### Listar todas
GET {{baseUrl}}/tareas

### Filtrar por estado
GET {{baseUrl}}/tareas?completada=false

### Consultar una
GET {{baseUrl}}/tareas/{{id}}

### Sustituir (PUT: reemplazo completo)
PUT {{baseUrl}}/tareas/{{id}}
Content-Type: application/json

{
  "titulo": "Aprender Express a fondo",
  "completada": false
}

### Modificar (PATCH: solo los campos enviados)
PATCH {{baseUrl}}/tareas/{{id}}
Content-Type: application/json

{
  "completada": true
}

### Eliminar (204 sin cuerpo)
DELETE {{baseUrl}}/tareas/{{id}}

### ERROR 422: título vacío
POST {{baseUrl}}/tareas
Content-Type: application/json

{
  "titulo": ""
}

### ERROR 404: tarea inexistente
GET {{baseUrl}}/tareas/no-existe

### ERROR 400: JSON mal formado
POST {{baseUrl}}/tareas
Content-Type: application/json

{ "titulo": 

### ERROR 404: ruta inexistente
GET {{baseUrl}}/ruta-que-no-existe
```

Por cada petición comprueba método, URL, cuerpo, código de estado, respuesta y efecto sobre los datos (por ejemplo, que un `GET` posterior ya no devuelva la tarea eliminada).

## Convenciones

Decide estas reglas una vez y aplícalas igual en todos los recursos.

**Rutas**

- sustantivos en plural y minúsculas: `/tareas`, no `/getTarea`;
- el método HTTP expresa la acción: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`;
- subrecursos con anidación de un nivel: `/tareas/:id/comentarios`;
- versión en la URL (`/api/v1`) para poder evolucionar sin romper a los clientes;
- filtros, ordenación y paginación en la consulta: `?completada=true&limit=20`.

**Códigos de estado**

| Código | Cuándo | Ejemplo |
| --- | --- | --- |
| `200` | Lectura o modificación correcta | `GET`, `PUT`, `PATCH` |
| `201` | Recurso creado, con cabecera `Location` | `POST` |
| `204` | Éxito sin cuerpo | `DELETE` |
| `400` | Petición mal formada | JSON roto |
| `401` | Falta autenticación o es inválida | Token ausente |
| `403` | Autenticado pero sin permiso | Rol insuficiente |
| `404` | El recurso o la ruta no existen | `GET /tareas/xyz` |
| `409` | Choca con el estado actual | Código duplicado |
| `422` | Formato correcto pero datos inválidos | Título vacío |
| `500` | Error inesperado del servidor | Fallo de base de datos |

**Formato de errores**

Todos los errores devuelven JSON con la misma forma, para que el cliente los trate igual:

```json
{
  "error": "Datos no válidos",
  "details": ["El título es obligatorio"]
}
```

`details` solo aparece cuando hay problemas concretos que listar, como en los errores de validación.

**Reglas de código**

- los controladores lanzan `AppError` en lugar de construir respuestas de error a mano;
- solo los repositorios acceden a los datos;
- nunca confíes en el cliente: valida siempre el cuerpo y los parámetros;
- el cliente no fija `id` ni fechas de creación;
- las respuestas `500` no incluyen trazas, rutas internas ni consultas SQL.

## Checklist y evolución

**Al empezar una API nueva**

- [ ] Definir recursos, rutas y códigos de respuesta antes de programar.
- [ ] Crear el proyecto y copiar el núcleo (`config`, `utils`, `middlewares`, `app.js`, `server.js`).
- [ ] Ajustar `.env.example`, `.env` y `.gitignore`.
- [ ] Verificar que `/health` responde `200`.

**Al añadir un recurso nuevo**

- [ ] Copiar y renombrar los cuatro archivos del recurso: validador, repositorio, controlador y rutas.
- [ ] Ajustar los campos y las reglas del validador.
- [ ] Registrar el router en `routes/index.js`.
- [ ] Añadir sus peticiones a `api.http`, con casos de éxito y de error.
- [ ] Comprobar `404`, `409` (si hay campos únicos) y `422`.

**Cómo evoluciona esta plantilla**

| Necesidad | Qué hacer |
| --- | --- |
| Persistencia | Reescribir solo los repositorios con una base de datos (por ejemplo MySQL o PostgreSQL); conservar el contrato y la configuración por variables de entorno |
| Autenticación | Añadir un middleware que valide el token y registrarlo en las rutas protegidas |
| Paginación | Leer `limit` y `offset` de `req.query` y pasarlos al repositorio |
| Lógica de negocio | Crear una capa `services/` entre controladores y repositorios |
| Pruebas | Probar `app` (ya exportada sin arrancar) con el ejecutor de pruebas de Node (`node --test`) y una librería HTTP |
| Seguridad | Añadir CORS y cabeceras de seguridad; limitar peticiones por cliente |
| Documentación | Describir el contrato con OpenAPI |
| Despliegue | Usar `/health` como comprobación y las variables de entorno de la plataforma |

La validación manual de esta plantilla es didáctica y suficiente para empezar. Más adelante puede sustituirse por una biblioteca de validación, manteniendo el mismo patrón: un validador por recurso conectado mediante el middleware `validate`.
