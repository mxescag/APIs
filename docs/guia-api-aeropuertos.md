# Guía paso a paso: API de ciudades y aeropuertos (Node.js + Express + MySQL + JWT)

Esta guía sigue el enunciado de la práctica. Está pensada para que entiendas cada pieza y pruebes cada paso antes de pasar al siguiente. El código es una propuesta completa y funcional, pero escríbelo tú mientras lees, porque así se aprende.

## Las ideas clave

- **REST**: cada recurso (ciudades, aeropuertos) tiene su URL y se manipula con verbos HTTP: `GET` consulta, `POST` crea, `PUT` modifica.
- **CRUD**: en esta práctica haces Create (`POST`), Read (`GET`) y Update (`PUT`). No hay Delete.
- **bcrypt**: guarda un hash de la contraseña, no la contraseña. Al hacer login se compara con `bcrypt.compare`.
- **JWT**: tras el login el servidor entrega un token firmado. El cliente lo envía en cada petición con `Authorization: Bearer <token>`, y el servidor lo verifica sin guardar sesión.
- **401 frente a 403**: `401` significa "no sé quién eres" (sin token o token malo). `403` significa "sé quién eres, pero no tienes permiso" (usuario normal intentando escribir).
- **Consultas parametrizadas**: usa `?` en el SQL y pasa los valores aparte. Así evitas la inyección SQL.

Flujo de una petición: `Ruta → authenticate (JWT) → authorizeAdmin (si toca) → Controlador → Repositorio → MySQL`.

---

## Paso 1. Crear el proyecto

```bash
mkdir api-aeropuertos && cd api-aeropuertos
npm init -y
npm install express mysql2 bcrypt jsonwebtoken dotenv
git init
```

En `package.json` añade el modo ESM y un script de desarrollo:

```json
{
  "type": "module",
  "scripts": {
    "start": "node src/server.js",
    "dev": "node --watch src/server.js"
  }
}
```

Crea `.gitignore`:

```
node_modules
.env
```

Crea `.env` (no se sube al repositorio) y `.env.example` (sin secretos, sí se sube):

```
PORT=3000
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password
DB_NAME=dwes_airports
JWT_SECRET=cambia_esto_por_una_cadena_larga_y_aleatoria
JWT_EXPIRES_IN=3600
```

`JWT_EXPIRES_IN` está en segundos (3600 = 1 hora) y es el `expiresIn` que devuelve el login.

## Paso 2. Base de datos

1. Crea la carpeta `database/` y guarda dentro `schema.sql` con **exactamente** el script del enunciado.
2. Ejecútalo en MySQL:
   ```bash
   mysql -u root -p < database/schema.sql
   ```
3. Comprueba que existe todo:
   ```sql
   USE dwes_airports;
   SHOW TABLES;
   SELECT * FROM cities;
   SELECT * FROM airports;
   ```

Debes ver 3 tablas, 4 ciudades (Teruel sin aeropuerto), 4 aeropuertos y el usuario admin.

## Paso 3. Estructura de carpetas

```
src/
├── app.js
├── server.js
├── config/database.js
├── utils/httpError.js
├── middleware/
│   ├── authenticate.js
│   ├── authorizeAdmin.js
│   └── errorHandler.js
├── validators/
├── repositories/
├── controllers/
└── routes/
```

Cada capa tiene una función:

- **routes**: solo asocian URL, middlewares y controlador.
- **controllers**: leen la petición, validan, llaman al repositorio y responden.
- **repositories**: son la única capa que escribe SQL.
- **validators**: comprueban los datos que llegan.

## Paso 4. Base: conexión, errores y servidor

`src/config/database.js`

```js
import 'dotenv/config';
import mysql from 'mysql2/promise';

export const pool = mysql.createPool({
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT) || 3306,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  waitForConnections: true,
  connectionLimit: 10,
});
```

`src/utils/httpError.js`: una clase de error con estado HTTP, para lanzar errores desde cualquier capa.

```js
export class HttpError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function assertValid(details) {
  if (Object.keys(details).length > 0) {
    throw new HttpError(422, 'VALIDATION_ERROR', 'Los datos enviados no son válidos.', details);
  }
}

export function parseId(value) {
  if (!/^\d+$/.test(String(value)) || Number(value) < 1) return null;
  return Number(value);
}
```

`src/middleware/errorHandler.js`: un único sitio que genera todas las respuestas de error con el formato del contrato.

```js
import { HttpError } from '../utils/httpError.js';

export function errorHandler(err, req, res, next) {
  if (err instanceof HttpError) {
    const error = { code: err.code, message: err.message };
    if (err.details) error.details = err.details;
    return res.status(err.status).json({ error });
  }
  // JSON mal formado en el cuerpo
  if (err.type === 'entity.parse.failed') {
    return res.status(400).json({
      error: { code: 'BAD_REQUEST', message: 'El JSON enviado no es válido.' },
    });
  }
  console.error(err); // el detalle solo va al log, nunca al cliente
  res.status(500).json({
    error: { code: 'INTERNAL_ERROR', message: 'Error interno del servidor.' },
  });
}
```

`src/app.js` (lo completarás al añadir rutas):

```js
import express from 'express';
import authRoutes from './routes/authRoutes.js';
import cityRoutes from './routes/cityRoutes.js';
import airportRoutes from './routes/airportRoutes.js';
import { errorHandler } from './middleware/errorHandler.js';

const app = express();
app.use(express.json());

app.use('/api/auth', authRoutes);
app.use('/api/cities', cityRoutes);
app.use('/api/airports', airportRoutes);

app.use((req, res) => {
  res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Ruta no encontrada.' } });
});
app.use(errorHandler);

export default app;
```

`src/server.js`

```js
import 'dotenv/config';
import app from './app.js';

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`API en http://localhost:${port}`));
```

> Esto usa Express 5, que captura los errores de funciones `async` automáticamente. Si tu `npm install express` instalara la 4, tendrías que envolver cada controlador en un `try/catch` o en un helper. Comprueba la versión con `npm ls express`.

Para probar este paso, comenta temporalmente los `import` y los `app.use` de las rutas que aún no existen, arranca con `npm run dev` y comprueba que responde.

## Paso 5. Registro y login

### 5.1 Validadores

`src/validators/authValidator.js`

```js
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateRegister(body) {
  const b = body ?? {};
  const name = typeof b.name === 'string' ? b.name.trim() : '';
  const email = typeof b.email === 'string' ? b.email.trim().toLowerCase() : '';
  const password = typeof b.password === 'string' ? b.password : '';
  const details = {};

  if (name.length < 2 || name.length > 100)
    details.name = 'El nombre debe tener entre 2 y 100 caracteres.';
  if (!EMAIL_RE.test(email) || email.length > 254)
    details.email = 'El correo no tiene un formato válido.';
  if (password.length < 8 || password.length > 72)
    details.password = 'La contraseña debe tener entre 8 y 72 caracteres.';

  return { values: { name, email, password }, details };
}

export function validateLogin(body) {
  const b = body ?? {};
  const email = typeof b.email === 'string' ? b.email.trim().toLowerCase() : '';
  const password = typeof b.password === 'string' ? b.password : '';
  const details = {};
  if (!email) details.email = 'El correo es obligatorio.';
  if (!password) details.password = 'La contraseña es obligatoria.';
  return { values: { email, password }, details };
}
```

El límite de 72 caracteres existe porque bcrypt ignora lo que pase de 72 bytes.

### 5.2 Repositorio de usuarios

`src/repositories/userRepository.js`

```js
import { pool } from '../config/database.js';

export async function findByEmail(email) {
  const [rows] = await pool.execute('SELECT * FROM users WHERE email = ?', [email]);
  return rows[0] ?? null;
}

export async function findById(id) {
  const [rows] = await pool.execute(
    'SELECT id, name, email, role FROM users WHERE id = ?',
    [id]
  );
  return rows[0] ?? null;
}

export async function create({ name, email, passwordHash }) {
  // El rol NO se recibe: la base de datos aplica DEFAULT 'user'
  const [result] = await pool.execute(
    'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
    [name, email, passwordHash]
  );
  return result.insertId;
}
```

### 5.3 Controlador

`src/controllers/authController.js`

```js
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import * as users from '../repositories/userRepository.js';
import { validateRegister, validateLogin } from '../validators/authValidator.js';
import { HttpError, assertValid } from '../utils/httpError.js';

export async function register(req, res) {
  const { values, details } = validateRegister(req.body);
  assertValid(details);

  const passwordHash = await bcrypt.hash(values.password, 10);

  try {
    const id = await users.create({
      name: values.name,
      email: values.email,
      passwordHash,
    });
    // Solo usamos name, email y password: cualquier "role" del body se ignora
    res.status(201).json({ id, name: values.name, email: values.email, role: 'user' });
  } catch (err) {
    if (err.code === 'ER_DUP_ENTRY') {
      throw new HttpError(409, 'EMAIL_TAKEN', 'El correo ya está registrado.');
    }
    throw err;
  }
}

export async function login(req, res) {
  const { values, details } = validateLogin(req.body);
  assertValid(details);

  const user = await users.findByEmail(values.email);
  const ok = user && (await bcrypt.compare(values.password, user.password_hash));
  if (!ok) {
    // Mismo mensaje tanto si falla el correo como la contraseña
    throw new HttpError(401, 'INVALID_CREDENTIALS', 'Credenciales incorrectas.');
  }

  const expiresIn = Number(process.env.JWT_EXPIRES_IN) || 3600;
  const accessToken = jwt.sign({ sub: String(user.id) }, process.env.JWT_SECRET, { expiresIn });

  res.json({
    accessToken,
    tokenType: 'Bearer',
    expiresIn,
    user: { id: user.id, name: user.name, email: user.email, role: user.role },
  });
}

export function me(req, res) {
  res.json(req.user);
}
```

Fíjate en que el registro nunca lee `role` del cuerpo. Esa es la forma más segura de cumplir la regla: no hace falta "rechazarlo", simplemente no se usa.

### 5.4 Middleware de autenticación y autorización

`src/middleware/authenticate.js`

```js
import jwt from 'jsonwebtoken';
import { findById } from '../repositories/userRepository.js';
import { HttpError } from '../utils/httpError.js';

export async function authenticate(req, res, next) {
  const header = req.headers.authorization ?? '';
  const [scheme, token] = header.split(' ');

  if (scheme !== 'Bearer' || !token) {
    throw new HttpError(401, 'UNAUTHORIZED', 'Falta el token de autenticación.');
  }

  let payload;
  try {
    payload = jwt.verify(token, process.env.JWT_SECRET); // verifica firma y caducidad
  } catch {
    throw new HttpError(401, 'UNAUTHORIZED', 'Token inválido o caducado.');
  }

  // El rol se lee de la base de datos, no del token
  const user = await findById(Number(payload.sub));
  if (!user) throw new HttpError(401, 'UNAUTHORIZED', 'Token inválido o caducado.');

  req.user = user;
  next();
}
```

`src/middleware/authorizeAdmin.js`

```js
import { HttpError } from '../utils/httpError.js';

export function authorizeAdmin(req, res, next) {
  if (req.user?.role !== 'admin') {
    throw new HttpError(403, 'FORBIDDEN', 'No tienes permisos para esta operación.');
  }
  next();
}
```

### 5.5 Rutas de autenticación

`src/routes/authRoutes.js`

```js
import { Router } from 'express';
import { register, login, me } from '../controllers/authController.js';
import { authenticate } from '../middleware/authenticate.js';

const router = Router();
router.post('/register', register);
router.post('/login', login);
router.get('/me', authenticate, me);

export default router;
```

### Prueba antes de seguir

Crea un `api.http` y comprueba estos casos:

- registro válido devuelve `201` sin hash;
- el mismo correo otra vez devuelve `409`;
- un registro con `"role": "admin"` crea un usuario con rol `user`;
- login correcto devuelve `accessToken`; contraseña incorrecta devuelve `401`;
- `GET /api/auth/me` con token devuelve `200`; sin token o con token inventado devuelve `401`;
- login con `admin@aeropuertos.test` / `password` funciona. Si fallara, el hash del script no coincide con tu versión de bcrypt: genera uno con `bcrypt.hash('password', 10)` y actualiza la fila.

Para probar la caducidad, pon `JWT_EXPIRES_IN=5`, haz login, espera y repite `/me`.

## Paso 6. Ciudades

### 6.1 Repositorio

`src/repositories/cityRepository.js`

```js
import { pool } from '../config/database.js';

export async function findAll(search) {
  if (search) {
    const [rows] = await pool.execute(
      'SELECT id, name, country FROM cities WHERE name LIKE ? ORDER BY name',
      [`%${search}%`]   // el patrón también va como parámetro
    );
    return rows;
  }
  const [rows] = await pool.execute('SELECT id, name, country FROM cities ORDER BY name');
  return rows;
}

export async function findById(id) {
  const [rows] = await pool.execute('SELECT id, name, country FROM cities WHERE id = ?', [id]);
  return rows[0] ?? null;
}

export async function findWithAirports() {
  const [rows] = await pool.execute(
    `SELECT c.id, c.name, c.country, COUNT(a.id) AS airportCount
     FROM cities c
     JOIN airports a ON a.city_id = c.id
     GROUP BY c.id, c.name, c.country
     ORDER BY c.name`
  );
  return rows;
}

export async function create({ name, country }) {
  const [result] = await pool.execute(
    'INSERT INTO cities (name, country) VALUES (?, ?)',
    [name, country]
  );
  return result.insertId;
}

export async function update(id, { name, country }) {
  await pool.execute('UPDATE cities SET name = ?, country = ? WHERE id = ?', [name, country, id]);
}
```

La búsqueda no distingue mayúsculas porque la colación `utf8mb4_unicode_ci` del script ya es insensible a mayúsculas y minúsculas. El `JOIN` (interno) deja fuera las ciudades sin aeropuerto, y por eso Teruel no aparece en `with-airports`.

### 6.2 Repositorio de aeropuertos

Lo necesitas ya para `/cities/:id/airports`.

`src/repositories/airportRepository.js`

```js
import { pool } from '../config/database.js';

const SELECT_FULL = `
  SELECT a.id, a.iata_code AS iataCode, a.name, a.city_id AS cityId,
         c.name AS cityName, c.country
  FROM airports a
  JOIN cities c ON c.id = a.city_id`;

export async function findAll(cityId) {
  if (cityId) {
    const [rows] = await pool.execute(`${SELECT_FULL} WHERE a.city_id = ? ORDER BY a.iata_code`, [cityId]);
    return rows;
  }
  const [rows] = await pool.execute(`${SELECT_FULL} ORDER BY a.iata_code`);
  return rows;
}

export async function findByCity(cityId) {
  const [rows] = await pool.execute(
    `SELECT id, iata_code AS iataCode, name, city_id AS cityId
     FROM airports WHERE city_id = ? ORDER BY iata_code`,
    [cityId]
  );
  return rows;
}

export async function findById(id) {
  const [rows] = await pool.execute(`${SELECT_FULL} WHERE a.id = ?`, [id]);
  return rows[0] ?? null;
}

export async function findBasicById(id) {
  const [rows] = await pool.execute(
    'SELECT id, iata_code AS iataCode, name, city_id AS cityId FROM airports WHERE id = ?',
    [id]
  );
  return rows[0] ?? null;
}

export async function create({ iataCode, name, cityId }) {
  const [result] = await pool.execute(
    'INSERT INTO airports (iata_code, name, city_id) VALUES (?, ?, ?)',
    [iataCode, name, cityId]
  );
  return result.insertId;
}

export async function update(id, { iataCode, name, cityId }) {
  await pool.execute(
    'UPDATE airports SET iata_code = ?, name = ?, city_id = ? WHERE id = ?',
    [iataCode, name, cityId, id]
  );
}
```

Los alias (`AS iataCode`, `AS cityId`) convierten los nombres de columna en snake_case de MySQL al camelCase que exige el contrato.

### 6.3 Validador y controlador

`src/validators/cityValidator.js`

```js
export function validateCity(body) {
  const b = body ?? {};
  const name = typeof b.name === 'string' ? b.name.trim() : '';
  const country = typeof b.country === 'string' ? b.country.trim() : '';
  const details = {};
  if (!name || name.length > 120) details.name = 'El nombre es obligatorio (máx. 120 caracteres).';
  if (!country || country.length > 120) details.country = 'El país es obligatorio (máx. 120 caracteres).';
  return { values: { name, country }, details };
}
```

`src/controllers/cityController.js`

```js
import * as cities from '../repositories/cityRepository.js';
import * as airports from '../repositories/airportRepository.js';
import { validateCity } from '../validators/cityValidator.js';
import { HttpError, assertValid, parseId } from '../utils/httpError.js';

const notFound = () => new HttpError(404, 'NOT_FOUND', 'Ciudad no encontrada.');

export async function list(req, res) {
  const search = typeof req.query.search === 'string' ? req.query.search.trim() : '';
  res.json(await cities.findAll(search));
}

export async function listWithAirports(req, res) {
  res.json(await cities.findWithAirports());
}

export async function listAirports(req, res) {
  const id = parseId(req.params.id);
  if (!id || !(await cities.findById(id))) throw notFound();
  res.json(await airports.findByCity(id));
}

export async function create(req, res) {
  const { values, details } = validateCity(req.body);
  assertValid(details);
  const id = await cities.create(values);
  res.status(201).json({ id, ...values });
}

export async function update(req, res) {
  const id = parseId(req.params.id);
  if (!id || !(await cities.findById(id))) throw notFound();

  const { values, details } = validateCity(req.body);
  assertValid(details);
  await cities.update(id, values);
  res.json({ id, ...values });
}
```

### 6.4 Rutas

`src/routes/cityRoutes.js`: **el orden importa**.

```js
import { Router } from 'express';
import * as ctrl from '../controllers/cityController.js';
import { authenticate } from '../middleware/authenticate.js';
import { authorizeAdmin } from '../middleware/authorizeAdmin.js';

const router = Router();
router.use(authenticate); // todo lo de ciudades exige estar autenticado

router.get('/', ctrl.list);
router.get('/with-airports', ctrl.listWithAirports); // ANTES de cualquier /:id
router.get('/:id/airports', ctrl.listAirports);

router.post('/', authorizeAdmin, ctrl.create);
router.put('/:id', authorizeAdmin, ctrl.update);

export default router;
```

## Paso 7. Aeropuertos

`src/validators/airportValidator.js`

```js
export function validateAirport(body) {
  const b = body ?? {};
  const iataCode = typeof b.iataCode === 'string' ? b.iataCode.trim().toUpperCase() : '';
  const name = typeof b.name === 'string' ? b.name.trim() : '';
  const cityIdRaw = b.cityId;
  const details = {};

  if (!/^[A-Z]{3}$/.test(iataCode)) details.iataCode = 'El código IATA debe tener 3 letras.';
  if (!name || name.length > 180) details.name = 'El nombre es obligatorio (máx. 180 caracteres).';
  if (!Number.isInteger(cityIdRaw) || cityIdRaw < 1) details.cityId = 'cityId debe ser un entero positivo.';

  return { values: { iataCode, name, cityId: cityIdRaw }, details };
}
```

`src/controllers/airportController.js`

```js
import * as airports from '../repositories/airportRepository.js';
import * as cities from '../repositories/cityRepository.js';
import { validateAirport } from '../validators/airportValidator.js';
import { HttpError, assertValid, parseId } from '../utils/httpError.js';

const notFound = () => new HttpError(404, 'NOT_FOUND', 'Aeropuerto no encontrado.');
const duplicated = () => new HttpError(409, 'IATA_TAKEN', 'El código IATA ya existe.');

export async function list(req, res) {
  let cityId;
  if (req.query.cityId !== undefined) {
    cityId = parseId(req.query.cityId);
    if (!cityId) return res.json([]); // cityId no válido: no hay coincidencias
  }
  res.json(await airports.findAll(cityId));
}

export async function getOne(req, res) {
  const id = parseId(req.params.id);
  const airport = id && (await airports.findById(id));
  if (!airport) throw notFound();
  res.json(airport);
}

export async function create(req, res) {
  const { values, details } = validateAirport(req.body);
  assertValid(details);

  if (!(await cities.findById(values.cityId))) {
    throw new HttpError(404, 'CITY_NOT_FOUND', 'La ciudad indicada no existe.');
  }
  try {
    const id = await airports.create(values);
    res.status(201).json({ id, ...values });
  } catch (err) {
    if (err.code === 'ER_DUP_ENTRY') throw duplicated();
    throw err;
  }
}

export async function update(req, res) {
  const id = parseId(req.params.id);
  if (!id || !(await airports.findBasicById(id))) throw notFound();

  const { values, details } = validateAirport(req.body);
  assertValid(details);

  if (!(await cities.findById(values.cityId))) {
    throw new HttpError(404, 'CITY_NOT_FOUND', 'La ciudad indicada no existe.');
  }
  try {
    await airports.update(id, values);
    res.json({ id, ...values });
  } catch (err) {
    if (err.code === 'ER_DUP_ENTRY') throw duplicated();
    throw err;
  }
}
```

`src/routes/airportRoutes.js`

```js
import { Router } from 'express';
import * as ctrl from '../controllers/airportController.js';
import { authenticate } from '../middleware/authenticate.js';
import { authorizeAdmin } from '../middleware/authorizeAdmin.js';

const router = Router();
router.use(authenticate);

router.get('/', ctrl.list);
router.get('/:id', ctrl.getOne);
router.post('/', authorizeAdmin, ctrl.create);
router.put('/:id', authorizeAdmin, ctrl.update);

export default router;
```

Aquí el `409` sale de la restricción `UNIQUE` de MySQL. Es más fiable que comprobar "si existe" antes de insertar, porque evita condiciones de carrera.

## Paso 8. Pruebas HTTP

1. Instala la extensión **REST Client** en VS Code (o usa Postman).
2. Copia en `api.http` la secuencia de la sección 6 del enunciado.
3. Añade tus propios casos. Estos son los que más fallan:

```http
### Token inventado → 401
GET {{baseUrl}}/api/cities
Authorization: Bearer abc.def.ghi

### Intento de elevar privilegios (debe crear un "user")
POST {{baseUrl}}/api/auth/register
Content-Type: application/json

{ "name": "Hacker", "email": "hacker@example.com", "password": "12345678", "role": "admin" }

### IATA mal formado → 422
POST {{baseUrl}}/api/airports
Authorization: Bearer {{adminToken}}
Content-Type: application/json

{ "iataCode": "V1", "name": "Prueba", "cityId": 1 }

### IATA duplicado → 409
POST {{baseUrl}}/api/airports
Authorization: Bearer {{adminToken}}
Content-Type: application/json

{ "iataCode": "MAD", "name": "Otro", "cityId": 1 }

### cityId inexistente → 404
POST {{baseUrl}}/api/airports
Authorization: Bearer {{adminToken}}
Content-Type: application/json

{ "iataCode": "XXX", "name": "Fantasma", "cityId": 9999 }

### Ciudad inexistente en la ruta anidada → 404
GET {{baseUrl}}/api/cities/9999/airports
Authorization: Bearer {{userToken}}

### Inyección SQL en search: debe devolver [] y no romper nada
GET {{baseUrl}}/api/cities?search=' OR '1'='1
Authorization: Bearer {{userToken}}
```

Ve apuntando el resultado de cada caso de aceptación de la sección 7 del enunciado en una tabla (caso, esperado, obtenido). Te la piden como "registro de pruebas".

## Paso 9. Entrega

- Código fuente y `package.json`.
- `.env.example` sin secretos.
- `database/schema.sql`.
- `api.http` (o la colección de Postman).
- `README.md` con: requisitos, `npm install`, configuración del `.env`, cómo cargar la base de datos, cómo arrancar, explicación de las carpetas, cómo se protegen las rutas (`authenticate` + `authorizeAdmin`) y el registro de pruebas.
- Sin `node_modules`, `.env` ni tokens reales. Revisa con `git status` antes de subir.

## Errores típicos

| Síntoma | Causa probable |
|---|---|
| `GET /cities/with-airports` devuelve 404 o error de id | La ruta está declarada después de `/:id` |
| `Cannot use import statement` | Falta `"type": "module"` en `package.json` |
| Todos los login dan 401, incluso el admin | El hash del script no coincide: regenera uno con bcrypt |
| `ER_NOT_SUPPORTED_AUTH_MODE` al conectar | Problema de autenticación del usuario MySQL; usa otro usuario o cambia el plugin de autenticación |
| Una ruta con error se queda colgada sin responder | Estás en Express 4 con funciones `async` sin `try/catch` |
| `cityId` llega como texto y da 422 | En el JSON debe ir como número (`5`, no `"5"`) |
| El body llega `undefined` | Falta `app.use(express.json())` o la cabecera `Content-Type: application/json` |

## Orden de trabajo recomendado

1. Proyecto y base de datos (pasos 1 a 3).
2. Servidor arrancando (paso 4).
3. Registro, login y `/me` con pruebas (paso 5).
4. Consultas de ciudades y aeropuertos (pasos 6 y 7, solo los `GET`).
5. Escrituras de administrador (`POST` y `PUT`).
6. Pruebas completas, README y entrega.

---

Fuente: [Práctica: API de ciudades y aeropuertos (enunciado)](https://jbeteta-ies.github.io/2DAW_DWES/U1/U01_05_05/)
