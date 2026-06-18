---
name: js-data-analysis
description: Análisis y manipulación de datos (CSV, JSON, Excel) con JavaScript/Deno. Requiere aplicar primero js-tool-general.
---

# Skill: js-data-analysis
**Análisis y manipulación de datos (CSV, JSON, Excel) con JavaScript/Deno**

> **Requiere**: Aplicar primero `js-tool-general` para el formato de salida y manejo de errores.

---

## ¿Cuándo activar este skill?

- "analiza este CSV", "procesa este JSON", "extrae datos de..."
- Transformaciones, filtros, agrupaciones, agregaciones
- Estadísticas básicas sobre conjuntos de datos
- Conversión entre formatos de datos

---

## Parsear CSV

```javascript
// Opción A: sin librería (CSV simple, sin comillas ni comas en campos)
function parseCSVSimple(text) {
  const lines = text.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim());
  return lines.slice(1).map(line => {
    const values = line.split(',');
    return Object.fromEntries(headers.map((h, i) => [h, values[i]?.trim()]));
  });
}

// Opción B: con librería Deno (CSV con campos complejos, recomendado)
import { parse } from "https://deno.land/std@0.224.0/csv/mod.ts";

const csvText = await Deno.readTextFile("datos.csv");
const rows = parse(csvText, { skipFirstRow: true, strip: true });
```

---

## Transformaciones comunes

```javascript
// Filtrar
const adultos = datos.filter(row => Number(row.edad) >= 18);

// Agrupar por categoría
const porCategoria = datos.reduce((acc, row) => {
  const key = row.categoria;
  if (!acc[key]) acc[key] = [];
  acc[key].push(row);
  return acc;
}, {});

// Estadísticas básicas de una columna numérica
function stats(arr, campo) {
  const nums = arr.map(r => Number(r[campo])).filter(n => !isNaN(n));
  const sum = nums.reduce((a, b) => a + b, 0);
  const sorted = [...nums].sort((a, b) => a - b);
  return {
    count: nums.length,
    sum: sum,
    mean: sum / nums.length,
    min: sorted[0],
    max: sorted[sorted.length - 1],
    median: sorted[Math.floor(sorted.length / 2)]
  };
}
```

---

## Parsear JSON anidado / aplanar

```javascript
// Aplanar objeto anidado
function flatten(obj, prefix = '', result = {}) {
  for (const [key, val] of Object.entries(obj)) {
    const newKey = prefix ? `${prefix}.${key}` : key;
    if (val && typeof val === 'object' && !Array.isArray(val)) {
      flatten(val, newKey, result);
    } else {
      result[newKey] = val;
    }
  }
  return result;
}

// Extraer campo de array de objetos anidados
const emails = usuarios.map(u => u.contacto?.email).filter(Boolean);
```

---

## Leer desde stdin (cuando el usuario pega datos)

```javascript
// Leer todo desde stdin
const decoder = new TextDecoder();
const chunks = [];
for await (const chunk of Deno.stdin.readable) {
  chunks.push(chunk);
}
const rawText = decoder.decode(new Uint8Array(chunks.flatMap(c => [...c])));
const data = JSON.parse(rawText); // o parseCSVSimple(rawText)
```

---

## Formato de resultado recomendado para datos

```javascript
const result = {
  status: "ok",
  summary: {
    total_rows: data.length,
    columns: Object.keys(data[0] || {}),
    // estadísticas clave
  },
  data: data.slice(0, 100), // limitar si son muchos registros
  truncated: data.length > 100
};
console.log(JSON.stringify(result, null, 2));
```

---

## Patrones de análisis frecuentes

```javascript
// Top N por campo numérico
const top5Ventas = datos
  .sort((a, b) => Number(b.ventas) - Number(a.ventas))
  .slice(0, 5);

// Contar ocurrencias
const frecuencia = datos.reduce((acc, row) => {
  acc[row.estado] = (acc[row.estado] || 0) + 1;
  return acc;
}, {});

// Pivot: suma de columna por grupo
const pivot = datos.reduce((acc, row) => {
  const key = row.region;
  acc[key] = (acc[key] || 0) + Number(row.monto);
  return acc;
}, {});
```
