# Guía paso a paso: API REST con Node.js y Express

Oct 13, 2026 · @Maxi

Esta guía construye una API REST de **ciudades** con Node.js 20+ y Express 5, con CRUD completo, validación y manejo de errores, en unos 9 pasos. Está basada en el tema [Introducción a las API REST](https://jbeteta-ies.github.io/2DAW_DWES/U1/U01_04_04/) del curso de Desarrollo de aplicaciones web en el servidor.

## Qué vas a construir

Una API que gestiona ciudades identificadas por un código de tres letras (por ejemplo `MAD`). Los datos se guardan en memoria, así que se pierden al reiniciar el servidor; la persistencia real con base de datos es el paso siguiente tras esta guía.

**Requisitos previos**

- Node.js 20 o superior y npm instalados.
- Un editor de código (por ejemplo VS Code con la extensión REST Client).
- Conocimientos básicos de JavaScript: funciones, arrays, objetos y módulos ES.

**Al terminar sabrás**

- diseñar recursos, rutas y un contrato de API antes de programar;
- crear un servidor Express con módulos ESM;
- leer parámetros de ruta, de consulta y de cuerpo;
- devolver JSON con los códigos de estado adecuados (`200`, `201`, `204`, `404`, `409`, `422`, `500`);
- implementar un CRUD en memoria con validación de entrada;
- separar rutas y controladores, y gestionar rutas inexistentes y errores;
- probar la API con un archivo `api.http`.

## Conceptos previos

Cuatro términos se confunden con frecuencia; conviene distinguirlos antes de escribir código.

| Concepto | Qué es | En esta guía |
| --- | --- | --- |
| HTTP | Protocolo de peticiones y respuestas: método, URL, cabeceras, cuerpo y código de estado | `POST /ciudades` con un cuerpo JSON |
| API | Contrato que define qué recursos, rutas, datos, respuestas y errores ofrece una aplicación | El conjunto de rutas de `/ciudades` |
| Servicio web | Funcionalidad expuesta mediante tecnologías web; una API HTTP es un caso habitual | Nuestro servidor Express |
| REST | Estilo arquitectónico: recursos con URL propia, métodos según su semántica, peticiones autocontenidas y representaciones (normalmente JSON) | Ciudades como recurso, JSON como representación |

Usar `GET`, `POST`, `PUT` y `DELETE` con JSON no convierte por sí solo una API en REST. También cuentan el diseño de los recursos, la semántica de HTTP, la ausencia de estado en el servidor y la coherencia del contrato.

## Paso 1: diseñar el contrato

Antes de programar, define qué recursos existen y qué rutas y respuestas ofrecerá la API. Aquí el recurso es `ciudad`.

**Reglas para nombrar rutas**

- usa sustantivos, no verbos;
- usa plurales para las colecciones;
- deja que el método HTTP exprese la operación;
- mantén una convención uniforme.

| Evita | Prefiere |
| --- | --- |
| `/getCiudades` | `GET /ciudades` |
| `/crearCiudad` | `POST /ciudades` |
| `/borrarCiudad/MAD` | `DELETE /ciudades/MAD` |

**Contrato de la API**

| Operación | Método | Ruta | Respuestas |
| --- | --- | --- | --- |
| Listar ciudades | `GET` | `/ciudades` | `200` |
| Consultar una ciudad | `GET` | `/ciudades/:codigo` | `200`, `404` |
| Crear una ciudad | `POST` | `/ciudades` | `201`, `409`, `422` |
| Sustituir una ciudad | `PUT` | `/ciudades/:codigo` | `200`, `404`, `422` |
| Modificar una ciudad | `PATCH` | `/ciudades/:codigo` | `200`, `404`, `422` |
| Eliminar una ciudad | `DELETE` | `/ciudades/:codigo` | `204`, `404` |

Cada ciudad tendrá tres campos: `codigo` (tres letras), `nombre` (texto) y `poblacion` (entero igual o mayor que 0).

## Paso 2: crear el proyecto

Crea la carpeta, inicializa npm e instala Express:

```bash
mkdir api-ciudades
cd api-ciudades
npm init -y
npm install express
```

Edita `package.json` para activar los módulos ES (`"type": "module"`) y añadir los scripts de arranque:

```json
{
  "name": "api-ciudades",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node src/server.js",
    "dev": "node --watch src/server.js"
  },
  "dependencies": {
    "express": "^5.0.0"
  }
}
```

No cambies a mano la versión de Express: la que instale npm quedará fijada en `package-lock.json`. El script `dev` reinicia el servidor al guardar cambios.

Crea esta estructura de carpetas y archivos vacíos:

```text
api-ciudades/
├── src/
│   ├── app.js
│   ├── server.js
│   ├── controllers/
│   │   └── ciudades.controller.js
│   └── routes/
│       └── ciudades.routes.js
├── package.json
└── package-lock.json
```

## Paso 3: la aplicación y el servidor

Separa la aplicación Express (`app.js`) de su arranque (`server.js`). Así podrás probarla, configurarla y desplegarla con más facilidad.

**`src/app.js`**

```js
import express from "express";
import { ciudadesRouter } from "./routes/ciudades.routes.js";

export const app = express();

// Interpreta cuerpos JSON: debe ir antes de las rutas
app.use(express.json());

app.get("/", (req, res) => {
  res.status(200).json({ name: "API de ciudades", version: "1.0.0" });
});

app.use("/ciudades", ciudadesRouter);

// Ruta inexistente
app.use((req, res) => {
  res.status(404).json({ error: "Ruta no encontrada" });
});

// Manejador final de errores (4 parámetros)
app.use((error, req, res, next) => {
  console.error(error);

  if (error instanceof SyntaxError && "body" in error) {
    return res.status(400).json({ error: "El cuerpo JSON no es válido" });
  }

  return res.status(500).json({ error: "Error interno del servidor" });
});
```

**`src/server.js`**

```js
import { app } from "./app.js";

const PORT = Number(process.env.PORT ?? 3000);

app.listen(PORT, () => {
  console.log(`API disponible en http://localhost:${PORT}`);
});
```

El orden de los `app.use` importa: `express.json()` primero, luego las rutas, después el 404 y por último el manejador de errores.

## Paso 4: definir las rutas

Un `Router` asocia cada método y ruta con una función controladora. Las rutas quedan relativas a `/ciudades`, que ya se montó en `app.js`.

**`src/routes/ciudades.routes.js`**

```js
import { Router } from "express";
import {
  crearCiudad,
  eliminarCiudad,
  listarCiudades,
  modificarCiudad,
  obtenerCiudad,
  sustituirCiudad
} from "../controllers/ciudades.controller.js";

export const ciudadesRouter = Router();

ciudadesRouter.get("/", listarCiudades);
ciudadesRouter.get("/:codigo", obtenerCiudad);
ciudadesRouter.post("/", crearCiudad);
ciudadesRouter.put("/:codigo", sustituirCiudad);
ciudadesRouter.patch("/:codigo", modificarCiudad);
ciudadesRouter.delete("/:codigo", eliminarCiudad);
```

Las seis rutas coinciden una a una con el contrato del paso 1.

## Paso 5: controladores, datos y validación

El controlador contiene la lógica de cada operación. Por ahora los datos viven en un array en memoria. Construye el archivo en tres bloques.

**5.1 Datos y funciones auxiliares**

En `src/controllers/ciudades.controller.js`, empieza con los datos de partida, una función que normaliza el código (`mad` → `MAD`) y otra que valida el cuerpo de la petición.

```js
const ciudades = [
  { codigo: "MAD", nombre: "Madrid", poblacion: 3332035 },
  { codigo: "VLC", nombre: "València", poblacion: 807693 }
];

function normalizarCodigo(codigo) {
  return String(codigo).trim().toUpperCase();
}

function validarCiudad(datos, { parcial = false } = {}) {
  const errores = [];

  if (!parcial || "codigo" in datos) {
    if (typeof datos.codigo !== "string" || datos.codigo.trim() === "") {
      errores.push("El código es obligatorio");
    } else if (!/^[A-Za-z]{3}$/.test(datos.codigo.trim())) {
      errores.push("El código debe contener tres letras");
    }
  }

  if (!parcial || "nombre" in datos) {
    if (typeof datos.nombre !== "string" || datos.nombre.trim() === "") {
      errores.push("El nombre es obligatorio");
    }
  }

  if (!parcial || "poblacion" in datos) {
    if (!Number.isInteger(datos.poblacion) || datos.poblacion < 0) {
      errores.push("La población debe ser un entero igual o superior a cero");
    }
  }

  if (parcial && Object.keys(datos).length === 0) {
    errores.push("Debe enviarse al menos un campo");
  }

  return errores;
}
```

La validación comprueba presencia, tipo, formato y rango. Con `parcial: true` (para `PATCH`) solo se validan los campos que llegan.

**5.2 Lectura: listar y consultar**

```js
export function listarCiudades(req, res) {
  const nombre = req.query.nombre?.trim().toLowerCase();

  const resultado = nombre
    ? ciudades.filter((c) => c.nombre.toLowerCase().includes(nombre))
    : ciudades;

  return res.status(200).json(resultado);
}

export function obtenerCiudad(req, res) {
  const codigo = normalizarCodigo(req.params.codigo);
  const ciudad = ciudades.find((c) => c.codigo === codigo);

  if (!ciudad) {
    return res.status(404).json({ error: "Ciudad no encontrada" });
  }

  return res.status(200).json(ciudad);
}
```

**5.3 Escritura: crear, sustituir, modificar y eliminar**

```js
export function crearCiudad(req, res) {
  const errores = validarCiudad(req.body);

  if (errores.length > 0) {
    return res.status(422).json({ error: "Datos no válidos", details: errores });
  }

  const codigo = normalizarCodigo(req.body.codigo);

  if (ciudades.some((c) => c.codigo === codigo)) {
    return res.status(409).json({ error: "Ya existe una ciudad con ese código" });
  }

  const nueva = {
    codigo,
    nombre: req.body.nombre.trim(),
    poblacion: req.body.poblacion
  };

  ciudades.push(nueva);

  return res.status(201).location(`/ciudades/${nueva.codigo}`).json(nueva);
}

export function sustituirCiudad(req, res) {
  const codigo = normalizarCodigo(req.params.codigo);
  const indice = ciudades.findIndex((c) => c.codigo === codigo);

  if (indice === -1) {
    return res.status(404).json({ error: "Ciudad no encontrada" });
  }

  // El código lo fija la URL, no el cuerpo
  const datos = { ...req.body, codigo };
  const errores = validarCiudad(datos);

  if (errores.length > 0) {
    return res.status(422).json({ error: "Datos no válidos", details: errores });
  }

  const ciudad = {
    codigo,
    nombre: datos.nombre.trim(),
    poblacion: datos.poblacion
  };

  ciudades[indice] = ciudad;

  return res.status(200).json(ciudad);
}

export function modificarCiudad(req, res) {
  const codigo = normalizarCodigo(req.params.codigo);
  const indice = ciudades.findIndex((c) => c.codigo === codigo);

  if (indice === -1) {
    return res.status(404).json({ error: "Ciudad no encontrada" });
  }

  // Solo se aceptan los campos modificables
  const cambios = {};
  if ("nombre" in req.body) cambios.nombre = req.body.nombre;
  if ("poblacion" in req.body) cambios.poblacion = req.body.poblacion;

  const errores = validarCiudad(cambios, { parcial: true });

  if (errores.length > 0) {
    return res.status(422).json({ error: "Datos no válidos", details: errores });
  }

  const actualizada = { ...ciudades[indice], ...cambios };
  actualizada.nombre = actualizada.nombre.trim();

  ciudades[indice] = actualizada;

  return res.status(200).json(actualizada);
}

export function eliminarCiudad(req, res) {
  const codigo = normalizarCodigo(req.params.codigo);
  const indice = ciudades.findIndex((c) => c.codigo === codigo);

  if (indice === -1) {
    return res.status(404).json({ error: "Ciudad no encontrada" });
  }

  ciudades.splice(indice, 1);

  return res.status(204).send();
}
```

Puntos clave: `201` al crear con la cabecera `Location`; `409` si el código ya existe; `422` si los datos no son válidos; `404` si la ciudad no existe; `204` sin cuerpo al eliminar.

## Paso 6: parámetros de la petición y PUT frente a PATCH

Express ofrece tres sitios donde llega información del cliente. Ya los has usado en el controlador.

| Origen | Ejemplo de petición | En Express | Uso habitual |
| --- | --- | --- | --- |
| Ruta | `GET /ciudades/MAD` | `req.params.codigo` | Identificar un recurso |
| Consulta | `GET /ciudades?nombre=val` | `req.query.nombre` | Filtros, ordenación, paginación |
| Cuerpo | `POST /ciudades` con JSON | `req.body` | Datos del recurso a crear o cambiar |

`req.body` solo está disponible si `express.json()` se registró antes de las rutas.

**`PUT` sustituye, `PATCH` modifica**

- `PUT /ciudades/MAD` reemplaza la representación completa: hay que enviar todos los campos obligatorios (`nombre` y `poblacion`).
- `PATCH /ciudades/MAD` cambia solo lo enviado, por ejemplo `{ "poblacion": 3400000 }`.

En `PATCH` no conserves valores con `||`, por ejemplo `ciudad.poblacion = req.body.poblacion || ciudad.poblacion`. Falla con valores válidos como `0`, que se consideran falsos. Comprueba con `"poblacion" in req.body`, como hace el controlador.

## Paso 7: errores y códigos de estado

Distingue dos tipos de error y trata cada uno de forma distinta.

- **Esperados** (datos inválidos, recurso inexistente, duplicado): el controlador construye la respuesta con el código adecuado.
- **Inesperados** (fallo de base de datos, error de programación): llegan al middleware final de errores de `app.js`, que responde `500`.

| Código | Cuándo usarlo en esta API |
| --- | --- |
| `200` | Lectura o modificación correcta |
| `201` | Ciudad creada (con cabecera `Location`) |
| `204` | Ciudad eliminada, sin cuerpo |
| `400` | JSON mal formado |
| `404` | Ciudad o ruta inexistente |
| `409` | Ya existe una ciudad con ese código |
| `422` | Datos con formato o valores inválidos |
| `500` | Error interno inesperado |

En Express 5, si un manejador `async` lanza una excepción o su promesa se rechaza, el error pasa solo al middleware de errores. No hace falta `try/catch` ni `next(error)` para eso.

Una respuesta `500` nunca debe incluir trazas, rutas locales, consultas SQL ni credenciales. Regístralas con `console.error` en el servidor y devuelve un mensaje genérico al cliente.

## Paso 8: arrancar y probar la API

Arranca el servidor con `npm run dev`. Verás `API disponible en http://localhost:3000`.

Crea en la raíz un archivo `api.http`. Con la extensión REST Client de VS Code aparece un enlace *Send Request* sobre cada petición; también sirve Postman.

```http
### Información de la API
GET http://localhost:3000/

### Listar ciudades
GET http://localhost:3000/ciudades
Accept: application/json

### Filtrar ciudades
GET http://localhost:3000/ciudades?nombre=val
Accept: application/json

### Consultar ciudad
GET http://localhost:3000/ciudades/MAD
Accept: application/json

### Crear ciudad
POST http://localhost:3000/ciudades
Content-Type: application/json
Accept: application/json

{
  "codigo": "ALC",
  "nombre": "Alicante",
  "poblacion": 358720
}

### Sustituir ciudad
PUT http://localhost:3000/ciudades/ALC
Content-Type: application/json
Accept: application/json

{
  "nombre": "Alacant",
  "poblacion": 360000
}

### Modificar ciudad
PATCH http://localhost:3000/ciudades/ALC
Content-Type: application/json
Accept: application/json

{
  "poblacion": 365000
}

### Eliminar ciudad
DELETE http://localhost:3000/ciudades/ALC
```

En cada petición comprueba método, URL, cabeceras, cuerpo, código de estado, respuesta y efecto sobre los datos (por ejemplo, que un `GET` posterior ya no devuelva la ciudad eliminada).

**Casos de error que conviene provocar**

- código duplicado (`409`);
- población negativa o nombre vacío (`422`);
- JSON mal formado (`400`);
- ciudad inexistente (`404`);
- ruta inexistente (`404`).

## Práctica: ampliar con aeropuertos

Para afianzar lo aprendido, añade aeropuertos como subrecurso de cada ciudad. Cada ciudad pasa a tener una lista `aeropuertos`:

```js
{
  codigo: "MAD",
  nombre: "Madrid",
  poblacion: 3332035,
  aeropuertos: [
    { codigo: "MAD", nombre: "Adolfo Suárez Madrid-Barajas" }
  ]
}
```

| Método | Ruta | Operación |
| --- | --- | --- |
| `GET` | `/ciudades/:codigo/aeropuertos` | Listar aeropuertos |
| `GET` | `/ciudades/:codigo/aeropuertos/:aeropuerto` | Consultar aeropuerto |
| `POST` | `/ciudades/:codigo/aeropuertos` | Crear aeropuerto |
| `DELETE` | `/ciudades/:codigo/aeropuertos/:aeropuerto` | Eliminar aeropuerto |

**Requisitos**

- normaliza los códigos;
- `404` si no existe la ciudad o el aeropuerto;
- `409` si el código de aeropuerto ya existe;
- `422` si los datos son inválidos;
- `201` con cabecera `Location` al crear y `204` al eliminar;
- añade las peticiones nuevas a `api.http`.

**Ruta sugerida**

1. Añade `aeropuertos: []` a cada ciudad.
2. Comprueba que la ciudad existe antes de operar con sus aeropuertos.
3. Crea un controlador y un router de aeropuertos independientes.
4. Registra el router en `app.js`; `server.js` no cambia.
5. Comprueba la unicidad del código recorriendo los aeropuertos de todas las ciudades.
6. Impide eliminar una ciudad que aún tenga aeropuertos.
7. Prueba cada caso en `api.http`.

Tras tu primer intento, puedes comparar con la [solución del curso](https://jbeteta-ies.github.io/2DAW_DWES/U1/U01_04_04_sol/).

## Límites y siguientes pasos

La API funciona, pero guardar datos en un array pierde todo al reiniciar. Guardarlos en un archivo JSON (con `readFile` y `writeFile` de `node:fs/promises`) sirve solo como transición didáctica, por estos límites:

- se lee y escribe el archivo completo en cada operación;
- hay condiciones de carrera y pérdida de actualizaciones con peticiones simultáneas;
- no existen transacciones;
- escala mal y es difícil de consultar.

**Siguientes pasos**

- usar una base de datos (por ejemplo MySQL) con conexión desde Node.js;
- configurar mediante variables de entorno;
- separar el acceso a datos en repositorios;
- ejecutar el gestor de base de datos con Docker Compose;
- sustituir la validación manual por una biblioteca de validación (la responsabilidad de validar seguirá siendo de tu aplicación).

**Comprueba que sabes explicar**

- la diferencia entre HTTP, API y REST;
- por qué las rutas usan sustantivos;
- la diferencia entre `req.params`, `req.query` y `req.body`;
- cuándo usar `404`, `409`, `422` y `500`;
- por qué se separan aplicación, servidor, rutas y controladores.
