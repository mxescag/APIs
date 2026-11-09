# Guía paso a paso: vuelos y buscador público (OpenFlights + MySQL + Express)

Esta guía parte de que la práctica anterior está terminada y funciona: ciudades, aeropuertos, usuarios, JWT y rutas de administración. Por eso no repito nada de eso y solo añado lo nuevo, con el mismo estilo de carpetas (`routes → controllers → services → repositories`, más `validators`).

## Antes de empezar: las ideas clave

- **Hay que importar datos reales.** Los datos vienen de tres ficheros CSV de OpenFlights (`airports.dat`, `airlines.dat`, `routes.dat`). Escribirás un script que los lee y los guarda en MySQL.
- **`openflights_id` es el puente.** Cada aeropuerto y aerolínea del fichero tiene un ID numérico propio. Lo guardas en tu tabla y lo usas para enlazar las rutas. No uses los códigos IATA para enlazar, porque en `routes.dat` a veces faltan.
- **Importación repetible (idempotente).** Si ejecutas el script dos veces, la segunda no debe duplicar nada. Los aeropuertos y las aerolíneas se saltan gracias a sus claves únicas, y las rutas gracias a `source_key`, un hash SHA-256 de la fila.
- **`stops` significa dos cosas distintas.** `flights.stops` es lo que dice el fichero para esa fila (0 = directa). Las escalas de una ruta completa las calculas tú contando aeropuertos intermedios.
- **Los datos son históricos.** No son horarios, precios ni disponibilidad. Debes decirlo en la respuesta de la API (`dataSource`) y en el README.
- **Las rutas de búsqueda son públicas** (sin token). Las rutas de administración siguen igual que antes.

Plan de trabajo:

1. Descargar los datos.
2. Migrar la base de datos.
3. Escribir el importador.
4. Hacer la búsqueda pública de vuelos directos.
5. Hacer la búsqueda con escalas (ampliación para nota).
6. Probar, documentar y entregar.

Es un trabajo en grupo. Un reparto razonable es una persona por bloque (importador de aeropuertos y aerolíneas, importador de rutas, API pública, algoritmo de escalas). Aun así, el enunciado pide que cada integrante sepa explicar todo, así que repasad el código entre vosotros.

---

## Paso 1. Descargar los datos y preparar el proyecto

1. Crea la carpeta `data/openflights/` y descarga ahí los tres ficheros:
   - [airports.dat](https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat)
   - [airlines.dat](https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat)
   - [routes.dat](https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat)

   Con `curl` sería, por ejemplo: `curl -o data/openflights/airports.dat https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat`

2. Añade `data/` al `.gitignore`. El enunciado dice que no hace falta subir estos ficheros.

3. Instala el lector de CSV. **No uses `split(",")`**: hay campos entrecomillados con comas dentro.
   ```bash
   npm install csv-parse
   ```

4. Añade el script en `package.json`:
   ```json
   "scripts": {
     "start": "node src/server.js",
     "dev": "node --watch src/server.js",
     "import:openflights": "node src/scripts/importOpenflights.js"
   }
   ```

Cosas que debes saber de los ficheros:

- No tienen fila de cabecera: cada valor se identifica por su **posición**.
- El valor nulo se escribe `\N` (una barra y una N). En JavaScript, para escribirlo en un string, es `'\\N'`.
- Los índices que da el enunciado empiezan en 1, pero en un array de JavaScript empiezan en 0. La columna 13 de `airports.dat` es `fila[12]`.

## Paso 2. Migración de la base de datos

1. Guarda en `database/002_flights.sql` el script **exacto** del enunciado (el `ALTER TABLE airports` más las tablas `airlines` y `flights`).
2. Ejecútalo **una sola vez** sobre tu base `dwes_airports`:
   ```bash
   mysql -u root -p < database/002_flights.sql
   ```
3. Comprueba que existe todo:
   ```sql
   USE dwes_airports;
   SHOW TABLES;                 -- debe aparecer airlines y flights
   DESCRIBE airports;           -- debe tener openflights_id e icao_code
   ```

Si lo ejecutas una segunda vez, MySQL se quejará de que las columnas ya existen. Es normal y no hay que arreglarlo.

### Dos decisiones antes de importar

**1. Países en español frente a inglés.** Tus datos de ejemplo usan `España` y `Francia`, y OpenFlights usa `Spain` y `France`. Si no haces nada, el importador creará ciudades duplicadas (una en `España` y otra en `Spain`). Una solución sencilla es unificar tus ciudades de ejemplo al inglés antes de importar:

```sql
UPDATE cities SET country = 'Spain'  WHERE country = 'España';
UPDATE cities SET country = 'France' WHERE country = 'Francia';
```

Con la colación `utf8mb4_unicode_ci`, `Paris` y `París` se consideran iguales al comparar, así que tu "París" se reutilizará. Es una decisión que debéis tomar y documentar en el grupo.

**2. Ciudades repetidas.** Comprueba que no tienes duplicados de nombre y país:

```sql
SELECT name, country, COUNT(*) FROM cities GROUP BY name, country HAVING COUNT(*) > 1;
```

Si salen filas, resuélvelas a mano antes de importar.

## Paso 3. El importador

Crea `src/scripts/importOpenflights.js`. Lo construyes en bloques, y el fichero final es la suma de todos ellos en este orden.

### 3.1 Utilidades y estadísticas

```js
import 'dotenv/config';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { parse } from 'csv-parse/sync';
import { pool } from '../config/database.js';

const DATA_DIR = path.resolve('data/openflights');
const BATCH_SIZE = 500;
const NULL_MARK = '\\N'; // en el fichero aparece como \N

const stats = {
  airportsRead: 0, airportsInserted: 0, airportsLinked: 0, airportsAlready: 0, airportsSkipped: 0,
  airlinesRead: 0, airlinesInserted: 0, airlinesAlready: 0, airlinesSkipped: 0,
  routesRead: 0, routesInserted: 0, routesAlready: 0, routesSkipped: 0, routesNoAirline: 0,
};

// Convierte "", "\N" y undefined en null y recorta espacios
function clean(value) {
  if (value === undefined || value === null) return null;
  const v = String(value).trim();
  return v === '' || v === NULL_MARK ? null : v;
}

function toPositiveInt(value) {
  const v = clean(value);
  return v !== null && /^\d+$/.test(v) && Number(v) > 0 ? Number(v) : null;
}

function readDat(fileName) {
  const file = path.join(DATA_DIR, fileName);
  if (!fs.existsSync(file)) {
    throw new Error(`No se encuentra ${file}. Descárgalo siguiendo el README.`);
  }
  return parse(fs.readFileSync(file, 'utf8'), {
    relax_column_count: true,
    relax_quotes: true,
    skip_empty_lines: true,
  });
}

// Ejecuta el trabajo por lotes, cada uno en su propia transacción
async function runInBatches(items, size, label, work) {
  for (let i = 0; i < items.length; i += size) {
    const batch = items.slice(i, i + size);
    const conn = await pool.getConnection();
    try {
      await conn.beginTransaction();
      await work(conn, batch);
      await conn.commit();
    } catch (err) {
      await conn.rollback();
      console.error(`Falló el lote de ${label} (filas ${i}-${i + batch.length}): ${err.message}`);
      throw err;
    } finally {
      conn.release();
    }
  }
}

async function checkSchema() {
  try {
    await pool.query('SELECT openflights_id, icao_code FROM airports LIMIT 1');
    await pool.query('SELECT 1 FROM airlines LIMIT 1');
    await pool.query('SELECT 1 FROM flights LIMIT 1');
  } catch {
    throw new Error('Falta la migración: ejecuta database/002_flights.sql antes de importar.');
  }
}
```

Si un lote falla, se deshace solo ese lote (`rollback`) y el mensaje te dice qué filas eran. Eso cumple el requisito de "dejar claro qué lote no se completó".

### 3.2 Importar aeropuertos

Para cada fila hay tres caminos:

1. **Ya importado antes** (su `openflights_id` ya existe): se salta. Así la segunda ejecución no duplica.
2. **Ya existe por código IATA** (por ejemplo, tu MAD de la práctica anterior): se completa `openflights_id` y `icao_code`, sin tocar su `id` ni su ciudad.
3. **Nuevo**: se busca o crea su ciudad y se inserta.

```js
async function importAirports() {
  const rows = readDat('airports.dat');
  stats.airportsRead = rows.length;

  await runInBatches(rows, BATCH_SIZE, 'aeropuertos', async (conn, batch) => {
    for (const r of batch) {
      const openflightsId = toPositiveInt(r[0]);
      const name = clean(r[1]);
      const cityName = clean(r[2]);
      const country = clean(r[3]);
      const iata = clean(r[4])?.toUpperCase() ?? null;
      const icaoRaw = clean(r[5])?.toUpperCase() ?? null;
      const icao = icaoRaw && icaoRaw.length === 4 ? icaoRaw : null;
      const type = clean(r[12]);

      const valid =
        type === 'airport' && openflightsId && name && cityName && country &&
        iata && /^[A-Z]{3}$/.test(iata);
      if (!valid) { stats.airportsSkipped++; continue; }

      // 1) ya importado
      const [byOf] = await conn.execute(
        'SELECT id FROM airports WHERE openflights_id = ?', [openflightsId]);
      if (byOf.length > 0) { stats.airportsAlready++; continue; }

      // 2) existe por IATA (p. ej. los datos de ejemplo de la práctica 1)
      const [byIata] = await conn.execute(
        'SELECT id, openflights_id FROM airports WHERE iata_code = ?', [iata]);
      if (byIata.length > 0) {
        if (byIata[0].openflights_id === null) {
          await conn.execute(
            'UPDATE airports SET openflights_id = ?, icao_code = ? WHERE id = ?',
            [openflightsId, icao, byIata[0].id]);
          stats.airportsLinked++;
        } else {
          stats.airportsSkipped++; // conflicto: ese IATA ya está asignado a otro ID externo
        }
        continue;
      }

      // 3) nuevo: buscar o crear la ciudad
      let cityId;
      const [cityRows] = await conn.execute(
        'SELECT id FROM cities WHERE name = ? AND country = ? LIMIT 1', [cityName, country]);
      if (cityRows.length > 0) {
        cityId = cityRows[0].id;
      } else {
        const [res] = await conn.execute(
          'INSERT INTO cities (name, country) VALUES (?, ?)', [cityName, country]);
        cityId = res.insertId;
      }

      await conn.execute(
        `INSERT INTO airports (iata_code, name, city_id, openflights_id, icao_code)
         VALUES (?, ?, ?, ?, ?)`,
        [iata, name, cityId, openflightsId, icao]);
      stats.airportsInserted++;
    }
  });
}
```

Las filas descartadas (sin IATA, sin ciudad, de tipo estación o puerto…) se cuentan en `airportsSkipped`. **No se inventan códigos.**

### 3.3 Importar aerolíneas

Aquí no se descarta una fila por no tener IATA: lo único imprescindible es el ID y el nombre.

```js
async function importAirlines() {
  const rows = readDat('airlines.dat');
  stats.airlinesRead = rows.length;

  const valid = [];
  for (const r of rows) {
    const id = toPositiveInt(r[0]);
    const name = clean(r[1]);
    if (!id || !name) { stats.airlinesSkipped++; continue; }

    const iata = clean(r[3]);
    const icao = clean(r[4]);
    const active = clean(r[7]);
    valid.push([
      id,
      name.slice(0, 180),
      iata && iata !== '-' && iata.length <= 2 ? iata : null,
      icao && icao.length <= 3 ? icao : null,
      clean(r[6])?.slice(0, 120) ?? null,
      active === 'Y' || active === 'N' ? active : null,
    ]);
  }

  await runInBatches(valid, BATCH_SIZE, 'aerolíneas', async (conn, batch) => {
    const [res] = await conn.query(
      `INSERT IGNORE INTO airlines (openflights_id, name, iata_code, icao_code, country, active)
       VALUES ?`,
      [batch]);
    stats.airlinesInserted += res.affectedRows;
  });
  stats.airlinesAlready = valid.length - stats.airlinesInserted;
}
```

`INSERT IGNORE ... VALUES ?` inserta un lote de golpe. Los valores van como parámetros, nunca concatenados, y las filas repetidas (por la clave única) se ignoran sin contarse en `affectedRows`.

### 3.4 Importar rutas

Para no hacer 67 000 consultas, se cargan antes en memoria dos mapas: ID de OpenFlights → ID interno (aeropuertos y aerolíneas).

```js
async function importRoutes() {
  const rows = readDat('routes.dat');
  stats.routesRead = rows.length;

  const [airportRows] = await pool.query(
    'SELECT id, openflights_id FROM airports WHERE openflights_id IS NOT NULL');
  const airportMap = new Map(airportRows.map((a) => [a.openflights_id, a.id]));
  const [airlineRows] = await pool.query('SELECT id, openflights_id FROM airlines');
  const airlineMap = new Map(airlineRows.map((a) => [a.openflights_id, a.id]));

  const valid = [];
  for (const r of rows) {
    const src = airportMap.get(toPositiveInt(r[3]));
    const dst = airportMap.get(toPositiveInt(r[5]));
    const stopsRaw = clean(r[7]);

    // Sin origen o destino enlazable no se puede guardar (FK); tampoco origen = destino
    if (!src || !dst || src === dst || !/^\d+$/.test(stopsRaw ?? '')) {
      stats.routesSkipped++;
      continue;
    }

    const airlineExt = toPositiveInt(r[1]);
    const airline = airlineExt ? (airlineMap.get(airlineExt) ?? null) : null;
    if (airline === null) stats.routesNoAirline++; // se conserva con airline_id = NULL

    // Identidad de la fila: hash de sus 9 campos normalizados (no el número de línea)
    const fields = Array.from({ length: 9 }, (_, i) => clean(r[i]) ?? '');
    const sourceKey = createHash('sha256').update(fields.join('|')).digest('hex');

    valid.push([
      airline, src, dst,
      clean(r[6]) === 'Y' ? 1 : 0,
      Number(stopsRaw),
      clean(r[8])?.slice(0, 100) ?? null,
      sourceKey,
    ]);
  }

  await runInBatches(valid, BATCH_SIZE, 'rutas', async (conn, batch) => {
    const [res] = await conn.query(
      `INSERT IGNORE INTO flights
         (airline_id, source_airport_id, destination_airport_id, codeshare, stops, equipment, source_key)
       VALUES ?`,
      [batch]);
    stats.routesInserted += res.affectedRows;
    stats.routesAlready += batch.length - res.affectedRows;
  });
}
```

Sobre `INSERT IGNORE`: también convierte en aviso otros errores, no solo los duplicados. Aquí es seguro porque ya hemos comprobado a mano las referencias (origen, destino) antes de insertar.

### 3.5 Resumen y arranque

```js
function printSummary() {
  const line = (label, value) => console.log(`${label.padEnd(44)}${value}`);
  console.log('\n--- Resumen de importación ---');
  line('Aeropuertos leídos:', stats.airportsRead);
  line('Aeropuertos insertados:', stats.airportsInserted);
  line('Aeropuertos enlazados (ya existían por IATA):', stats.airportsLinked);
  line('Aeropuertos ya importados:', stats.airportsAlready);
  line('Aeropuertos omitidos:', stats.airportsSkipped);
  line('Aerolíneas leídas:', stats.airlinesRead);
  line('Aerolíneas insertadas:', stats.airlinesInserted);
  line('Aerolíneas ya importadas / omitidas:', `${stats.airlinesAlready} / ${stats.airlinesSkipped}`);
  line('Rutas leídas:', stats.routesRead);
  line('Rutas insertadas:', stats.routesInserted);
  line('Rutas ya importadas:', stats.routesAlready);
  line('Rutas omitidas por referencias ausentes:', stats.routesSkipped);
  line('Rutas guardadas sin aerolínea:', stats.routesNoAirline);
}

async function main() {
  await checkSchema();
  await importAirports();
  await importAirlines();
  await importRoutes();
  printSummary();
}

main()
  .catch((err) => {
    console.error('Importación fallida:', err.message);
    process.exitCode = 1;
  })
  .finally(() => pool.end());
```

El orden importa: aeropuertos, luego aerolíneas, luego rutas, porque las rutas necesitan los otros dos.

### Prueba del importador

1. Ejecuta `npm run import:openflights` y mira el resumen.
2. Verifica los datos:
   ```sql
   SELECT COUNT(*) FROM airports;
   SELECT COUNT(*) FROM airlines;
   SELECT COUNT(*) FROM flights;

   -- ¿Se enlazó tu MAD de ejemplo?
   SELECT id, iata_code, openflights_id, icao_code FROM airports WHERE iata_code = 'MAD';
   ```
3. **Ejecútalo una segunda vez.** Los insertados deben ser 0 y los "ya importados" deben coincidir con los insertados de la primera vez.
4. Comprueba que las tablas de la práctica 1 siguen intactas (usuarios, y que el login del admin sigue funcionando).

## Paso 4. Búsqueda pública de vuelos directos

### 4.1 Repositorio

`src/repositories/flightRepository.js`

```js
import { pool } from '../config/database.js';

export async function findDirect(fromCityId, toCityId) {
  const [rows] = await pool.execute(
    `SELECT al.name AS airline,
            sa.iata_code AS fromIata, sa.name AS fromAirport, sc.name AS fromCity,
            da.iata_code AS toIata,   da.name AS toAirport,   dc.name AS toCity
     FROM flights f
     JOIN airports sa ON sa.id = f.source_airport_id
     JOIN cities sc   ON sc.id = sa.city_id
     JOIN airports da ON da.id = f.destination_airport_id
     JOIN cities dc   ON dc.id = da.city_id
     LEFT JOIN airlines al ON al.id = f.airline_id
     WHERE sa.city_id = ? AND da.city_id = ? AND f.stops = 0
     ORDER BY sa.iata_code, da.iata_code, al.name`,
    [fromCityId, toCityId]
  );
  return rows;
}
```

Usas `LEFT JOIN` con `airlines` porque `airline_id` puede ser `NULL`. Con un `JOIN` normal se perderían esas rutas.

### 4.2 Controlador público

`src/controllers/publicController.js`

```js
import * as cities from '../repositories/cityRepository.js';
import * as airports from '../repositories/airportRepository.js';
import * as flights from '../repositories/flightRepository.js';
import { HttpError, assertValid, parseId } from '../utils/httpError.js';

const DATA_SOURCE = 'OpenFlights (dataset histórico)';
const cityInfo = (c) => ({ cityId: c.id, city: c.name, country: c.country });

function parseSearchParams(query, withMaxStops) {
  const details = {};
  const fromCityId = parseId(query.fromCityId);
  const toCityId = parseId(query.toCityId);

  if (!fromCityId) details.fromCityId = 'fromCityId debe ser un entero positivo.';
  if (!toCityId) details.toCityId = 'toCityId debe ser un entero positivo.';
  if (fromCityId && toCityId && fromCityId === toCityId) {
    details.toCityId = 'El origen y el destino deben ser distintos.';
  }

  let maxStops = 0;
  if (withMaxStops && query.maxStops !== undefined) {
    if (/^[0-3]$/.test(String(query.maxStops))) maxStops = Number(query.maxStops);
    else details.maxStops = 'maxStops debe ser un entero entre 0 y 3.';
  }

  assertValid(details);
  return { fromCityId, toCityId, maxStops };
}

async function loadCities(fromCityId, toCityId) {
  const [from, to] = await Promise.all([cities.findById(fromCityId), cities.findById(toCityId)]);
  if (!from) throw new HttpError(404, 'CITY_NOT_FOUND', 'La ciudad de origen no existe.');
  if (!to) throw new HttpError(404, 'CITY_NOT_FOUND', 'La ciudad de destino no existe.');
  return { from, to };
}

export async function searchCities(req, res) {
  const search = typeof req.query.search === 'string' ? req.query.search.trim() : '';
  res.json(await cities.findAll(search));
}

export async function cityAirports(req, res) {
  const id = parseId(req.params.id);
  if (!id || !(await cities.findById(id))) {
    throw new HttpError(404, 'NOT_FOUND', 'Ciudad no encontrada.');
  }
  res.json(await airports.findByCity(id));
}

export async function searchDirect(req, res) {
  const { fromCityId, toCityId } = parseSearchParams(req.query, false);
  const { from, to } = await loadCities(fromCityId, toCityId);

  const rows = await flights.findDirect(fromCityId, toCityId);
  const routes = rows.map((r) => ({
    stops: 0,
    legs: [{
      airline: r.airline,
      from: { iataCode: r.fromIata, airport: r.fromAirport, city: r.fromCity },
      to: { iataCode: r.toIata, airport: r.toAirport, city: r.toCity },
    }],
  }));

  res.json({
    from: cityInfo(from),
    to: cityInfo(to),
    routes,
    count: routes.length,
    dataSource: DATA_SOURCE,
  });
}
```

Primero validas (`422`) y después compruebas que las ciudades existen (`404`). Si no hay rutas, `routes` es `[]` y la respuesta es `200`.

### 4.3 Rutas y montaje

`src/routes/publicRoutes.js`: no lleva `authenticate`.

```js
import { Router } from 'express';
import * as ctrl from '../controllers/publicController.js';

const router = Router();

router.get('/cities', ctrl.searchCities);
router.get('/cities/:id/airports', ctrl.cityAirports);
router.get('/routes/direct', ctrl.searchDirect);

export default router;
```

En `src/app.js`, añade el import y monta la ruta junto a las demás:

```js
import publicRoutes from './routes/publicRoutes.js';
// ...
app.use('/api/public', publicRoutes);
```

### Prueba

Primero necesitas IDs de ciudad reales, porque el dataset es enorme. Esta consulta te ayuda a elegir:

```sql
-- Ciudades con más salidas directas
SELECT c.id, c.name, c.country, COUNT(*) AS salidas
FROM flights f
JOIN airports a ON a.id = f.source_airport_id
JOIN cities c ON c.id = a.city_id
WHERE f.stops = 0
GROUP BY c.id, c.name, c.country
ORDER BY salidas DESC LIMIT 10;
```

Con dos de esas ciudades, prueba en `api.http`:

- `GET /api/public/routes/direct?fromCityId=X&toCityId=Y` sin token devuelve `200` con rutas.
- Un par de ciudades sin conexión directa devuelve `200` con `"routes": []` y `"count": 0`.
- `fromCityId=abc` devuelve `422`.
- `fromCityId=999999` devuelve `404`.
- `fromCityId` igual a `toCityId` devuelve `422`.

## Paso 5. Búsqueda con escalas (ampliación para nota)

### La idea

Piensa en los aeropuertos como puntos y en cada ruta directa (`stops = 0`) como una flecha entre dos puntos. Buscar una ruta con escalas es buscar caminos por ese mapa. Con **BFS (búsqueda en anchura)** explora primero los caminos de 1 tramo, luego los de 2, etc., así que los resultados salen ya ordenados de menos a más escalas.

Reglas del enunciado y cómo se cumplen:

| Regla | Cómo |
|---|---|
| Partir de cada aeropuerto de la ciudad origen | La cola empieza con un camino por cada aeropuerto origen |
| Detenerse al llegar a un aeropuerto de la ciudad destino | Al llegar a uno se guarda el camino y no se sigue por él |
| No repetir aeropuerto en una ruta | `path.includes(next)` |
| Respetar `maxStops` | Un camino con `maxStops + 1` tramos ya no se amplía |
| Máximo de resultados | `limit = 20` |
| No duplicar secuencias | El grafo tiene una sola flecha por par de aeropuertos |

### 5.1 Repositorio

Añade a `src/repositories/flightRepository.js`:

```js
// Una arista por par (origen, destino); si hay varias aerolíneas se elige una (la primera por nombre)
export async function loadDirectEdges() {
  const [rows] = await pool.query(
    `SELECT f.source_airport_id AS src, f.destination_airport_id AS dst, MIN(al.name) AS airline
     FROM flights f
     LEFT JOIN airlines al ON al.id = f.airline_id
     WHERE f.stops = 0
     GROUP BY f.source_airport_id, f.destination_airport_id`
  );
  return rows;
}
```

Y a `src/repositories/airportRepository.js`:

```js
export async function findManyWithCity(ids) {
  if (ids.length === 0) return [];
  const [rows] = await pool.query(
    `SELECT a.id, a.iata_code AS iataCode, a.name, c.name AS city
     FROM airports a JOIN cities c ON c.id = a.city_id
     WHERE a.id IN (?)`,
    [ids]
  );
  return rows;
}
```

### 5.2 Servicio con el algoritmo

Aquí encaja la carpeta `services/`: es lógica de negocio, no validación ni SQL.

`src/services/routeSearchService.js`

```js
import * as flights from '../repositories/flightRepository.js';
import * as airportsRepo from '../repositories/airportRepository.js';

const MAX_PATHS = 300000; // protección: evita agotar la memoria en búsquedas enormes
let graphCache = null;

// El grafo se carga una vez y se reutiliza (si reimportas datos, reinicia el servidor)
async function getGraph() {
  if (!graphCache) {
    const edges = await flights.loadDirectEdges();
    const adjacency = new Map();      // aeropuerto -> [aeropuertos alcanzables]
    const airlineByEdge = new Map();  // "origen-destino" -> nombre de aerolínea
    for (const { src, dst, airline } of edges) {
      if (!adjacency.has(src)) adjacency.set(src, []);
      adjacency.get(src).push(dst);
      airlineByEdge.set(`${src}-${dst}`, airline);
    }
    graphCache = { adjacency, airlineByEdge };
  }
  return graphCache;
}

const place = (a) => ({ iataCode: a.iataCode, airport: a.name, city: a.city });

export async function findRoutes(fromCityId, toCityId, maxStops, limit = 20) {
  const { adjacency, airlineByEdge } = await getGraph();
  const sources = (await airportsRepo.findByCity(fromCityId)).map((a) => a.id);
  const targets = new Set((await airportsRepo.findByCity(toCityId)).map((a) => a.id));

  const queue = sources.map((id) => [id]); // cada elemento es un camino: [aeropuerto, aeropuerto, ...]
  const found = [];
  let head = 0;

  while (head < queue.length && found.length < limit) {
    const path = queue[head++];
    const last = path[path.length - 1];

    for (const next of adjacency.get(last) ?? []) {
      if (path.includes(next)) continue;      // sin ciclos
      const newPath = [...path, next];

      if (targets.has(next)) {
        found.push(newPath);                  // llegamos: se guarda y no se sigue por aquí
        if (found.length >= limit) break;
      } else if (newPath.length - 1 <= maxStops && queue.length < MAX_PATHS) {
        queue.push(newPath);                  // aún caben más tramos
      }
    }
  }

  if (found.length === 0) return [];

  const ids = [...new Set(found.flat())];
  const details = new Map((await airportsRepo.findManyWithCity(ids)).map((a) => [a.id, a]));

  return found.map((path) => ({
    stops: path.length - 2, // aeropuertos intermedios
    legs: path.slice(0, -1).map((fromId, i) => {
      const toId = path[i + 1];
      return {
        airline: airlineByEdge.get(`${fromId}-${toId}`) ?? null,
        from: place(details.get(fromId)),
        to: place(details.get(toId)),
      };
    }),
  }));
}
```

Cómo funciona el bucle, con `maxStops = 1`:

1. La cola empieza con `[MAD]`.
2. De MAD se sacan sus destinos. Si uno está en la ciudad destino, ya hay una ruta de 1 tramo (0 escalas).
3. Si no, el camino `[MAD, X]` tiene 1 tramo, que es `<= maxStops`, así que vuelve a la cola.
4. De `[MAD, X]` se sacan los destinos de X. Los que llegan al destino forman rutas de 2 tramos (1 escala). Los demás ya no se amplían, porque tendrían 3 tramos.

Como la cola es FIFO, los caminos cortos se procesan antes que los largos, y por eso las rutas con menos escalas salen primero.

### 5.3 Conectar con el controlador y las rutas

En `src/controllers/publicController.js` añade el import y el manejador:

```js
import { findRoutes } from '../services/routeSearchService.js';

export async function searchRoutes(req, res) {
  const { fromCityId, toCityId, maxStops } = parseSearchParams(req.query, true);
  const { from, to } = await loadCities(fromCityId, toCityId);

  const routes = await findRoutes(fromCityId, toCityId, maxStops);

  res.json({
    from: cityInfo(from),
    to: cityInfo(to),
    routes,
    count: routes.length,
    dataSource: DATA_SOURCE,
  });
}
```

En `src/routes/publicRoutes.js`:

```js
router.get('/routes', ctrl.searchRoutes);
```

### Prueba

Necesitas un par de ciudades **sin vuelo directo pero con conexión por escala**. Un truco: elige una ciudad hub (de la lista de más salidas) y una ciudad pequeña, y prueba con `maxStops` 0, 1, 2 y 3. Anota qué ciudades usaste, porque lo pide la entrega.

- Con `maxStops=0` no debe haber resultados (o solo directos).
- Con `maxStops=1` debe aparecer alguna ruta con `stops: 1` y dos `legs`.
- Ninguna ruta repite aeropuerto.
- Los resultados vienen ordenados de menos a más escalas.
- `maxStops=4` devuelve `422`.
- Hay como máximo 20 resultados.

Una mejora opcional, si tu búsqueda con `maxStops=3` va lenta, es calcular antes, con una búsqueda inversa desde el destino, qué aeropuertos pueden llegar a él en pocos tramos, y descartar el resto al explorar. Primero haz que funcione la versión sencilla.

## Paso 6. Pruebas, documentación y entrega

### 6.1 `api.http`

Añade a tu fichero de la práctica anterior, con IDs reales de tu base:

```http
### Buscar ciudades sin autenticación
GET {{baseUrl}}/api/public/cities?search=mad
Accept: application/json

### Aeropuertos de una ciudad (público)
GET {{baseUrl}}/api/public/cities/1/airports
Accept: application/json

### Vuelos directos
GET {{baseUrl}}/api/public/routes/direct?fromCityId=1&toCityId=3
Accept: application/json

### Rutas con hasta dos escalas
GET {{baseUrl}}/api/public/routes?fromCityId=1&toCityId=8&maxStops=2
Accept: application/json

### Parámetro incorrecto → 422
GET {{baseUrl}}/api/public/routes?fromCityId=abc&toCityId=3

### Ciudad inexistente → 404
GET {{baseUrl}}/api/public/routes/direct?fromCityId=999999&toCityId=3

### maxStops fuera de rango → 422
GET {{baseUrl}}/api/public/routes?fromCityId=1&toCityId=3&maxStops=9

### Lo administrativo sigue protegido: sin token → 401
POST {{baseUrl}}/api/cities
Content-Type: application/json

{ "name": "Prueba", "country": "Spain" }
```

Repite también el caso de la práctica 1: un usuario normal que intenta crear una ciudad sigue recibiendo `403`.

### 6.2 Casos de aceptación

Ve marcándolos con el resultado real:

**Importación**
- [ ] Los CSV se leen bien, incluidos los campos entrecomillados.
- [ ] `\N` y los vacíos se tratan como ausentes.
- [ ] Solo se importan aeropuertos de tipo `airport` con IATA, ciudad y país.
- [ ] Cada aeropuerto conserva su `openflights_id`.
- [ ] Las rutas se enlazan por ID externo, no por IATA.
- [ ] Las referencias ausentes se cuentan y no rompen claves foráneas.
- [ ] La segunda ejecución no duplica nada.
- [ ] El resumen muestra insertados, ya existentes y descartados.

**API**
- [ ] Las consultas públicas funcionan sin token.
- [ ] Una conexión directa sale con 0 escalas y un tramo.
- [ ] Sin resultados: `200` con lista vacía.
- [ ] Ciudad inexistente: `404`. Parámetros mal: `422`.
- [ ] Ninguna ruta repite aeropuerto.
- [ ] El límite de escalas se aplica en el servidor.
- [ ] Primero salen las rutas con menos escalas.
- [ ] Las rutas de administración siguen exigiendo token y rol `admin`.
- [ ] La respuesta indica que los datos son históricos (`dataSource`).

### 6.3 README

Debe incluir:

- Cómo preparar el entorno y el orden de carga: `schema.sql`, luego `002_flights.sql`, luego `npm run import:openflights`.
- De dónde se descargan los tres ficheros y en qué carpeta se colocan.
- La **atribución de OpenFlights**. Ponla también visible en la aplicación (por ejemplo, en la respuesta de la API):
  > Datos de aeropuertos, aerolíneas y rutas: OpenFlights, https://openflights.org/data.php. Dataset histórico; consultado para uso educativo.
- Las limitaciones: son rutas históricas (no se actualizan desde 2014), no hay horarios, precios ni disponibilidad.
- La decisión que tomasteis sobre los países en español e inglés.
- Para la nota: el límite de escalas elegido y las ciudades de la prueba con varias escalas.

### 6.4 Entrega

- `database/002_flights.sql`.
- El comando de importación y su resumen.
- Instrucciones y enlaces de descarga.
- El endpoint público de directos (y el de escalas, si lo hacéis).
- `api.http` o colección de Postman.
- README completo y una demostración de la búsqueda directa.
- Sin los ficheros `.dat`, `node_modules`, `.env`, contraseñas ni JWT.

---

## Errores típicos

| Síntoma | Causa probable |
|---|---|
| `Falta la migración` al importar | No ejecutaste `002_flights.sql`, o la ejecutaste en otra base |
| Se importan 0 rutas | Los aeropuertos no tienen `openflights_id` (importa primero aeropuertos) |
| Muchas ciudades duplicadas (`Spain` y `España`) | No unificaste los países antes de importar |
| Error de columnas o de comillas al leer el CSV | Usaste `split(",")`, o falta `relax_quotes: true` |
| `\N` aparece guardado como texto | No pasas los valores por `clean()` |
| La segunda ejecución inserta de nuevo | Falla la `source_key` (por ejemplo, si el hash usa el número de línea en vez de los campos) |
| `/routes/direct` no devuelve rutas con aerolínea desconocida | Usaste `JOIN` en vez de `LEFT JOIN` con `airlines` |
| La búsqueda con escalas se cuelga | Falta `maxStops` acotado o el límite `MAX_PATHS` |
| Cambió el dataset y la búsqueda no lo ve | El grafo está en caché; reinicia el servidor |
| Error en `CHECK` al migrar | Tu MySQL es anterior a 8.0.16 y no soporta `CHECK` |

## Orden de trabajo recomendado

1. Descargar datos y migrar la base de datos (pasos 1 y 2).
2. Importar aeropuertos y comprobar. Después aerolíneas. Después rutas (paso 3).
3. Ejecutar el importador dos veces para comprobar que no duplica.
4. Búsqueda de directos y sus pruebas (paso 4).
5. Escalas con BFS (paso 5), si queréis la ampliación.
6. Pruebas completas, README y entrega (paso 6).

---

Fuente: [Trabajo en grupo: vuelos y buscador público (enunciado)](https://jbeteta-ies.github.io/2DAW_DWES/U1/U01_05_06/)
