---
name: js-math-precision
description: Cálculos matemáticos precisos con JavaScript/Deno. Requiere aplicar primero js-tool-general.
---

# Skill: js-math-precision
**Cálculos matemáticos precisos con JavaScript/Deno**

> **Requiere**: Aplicar primero `js-tool-general` para el formato de salida y manejo de errores.

---

## ¿Cuándo activar este skill?

- Cálculos financieros (sumas de dinero, porcentajes, interés)
- Estadísticas y probabilidad
- Álgebra lineal, matrices
- Cualquier operación donde la precisión decimal importa

---

## El problema del punto flotante en JS

```javascript
// ❌ NUNCA uses aritmética nativa para dinero o precisión crítica
0.1 + 0.2 === 0.3          // false → resultado: 0.30000000000000004
(1.005 * 100) / 100        // 1.005 → resultado: 1.0049999999...

// ✅ Usa enteros escalados para dinero (centavos)
const precio = 1005;        // $10.05 en centavos
const iva = Math.round(precio * 0.16);
const total = precio + iva; // 1005 + 161 = 1166 centavos = $11.66
const display = (total / 100).toFixed(2); // "11.66"
```

---

## Librería mathjs (para cálculos complejos)

```javascript
import * as math from "https://esm.sh/mathjs@13";

// Aritmética de precisión
math.add(0.1, 0.2)               // 0.3 exacto
math.evaluate("0.1 + 0.2")       // 0.3

// Fracciones exactas
const fraccion = math.fraction(1, 3);
math.format(fraccion)             // "1/3"

// Unidades
math.evaluate("5 kg + 300 g")    // 5.3 kg
math.evaluate("100 km/h to mph") // 62.137... mph

// Álgebra simbólica básica
math.simplify("2x + 3x")         // "5 * x"
math.derivative("x^2 + 3x", "x") // "2 * x + 3"

// Matrices
const A = math.matrix([[1, 2], [3, 4]]);
const B = math.matrix([[5, 6], [7, 8]]);
math.multiply(A, B)               // [[19, 22], [43, 50]]
math.det(A)                       // -2
math.inv(A)                       // [[-2, 1], [1.5, -0.5]]
```

---

## Estadísticas descriptivas

```javascript
// Con mathjs
import * as math from "https://esm.sh/mathjs@13";

const datos = [4, 7, 13, 2, 8, 11, 5, 9, 3, 6];

const estadisticas = {
  media: math.mean(datos),
  mediana: math.median(datos),
  desviacion_std: math.std(datos),
  varianza: math.variance(datos),
  min: math.min(datos),
  max: math.max(datos),
  suma: math.sum(datos),
  rango: math.max(datos) - math.min(datos)
};

// Percentil (manual, mathjs no lo incluye directamente)
function percentil(arr, p) {
  const sorted = [...arr].sort((a, b) => a - b);
  const index = (p / 100) * (sorted.length - 1);
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
}

estadisticas.p25 = percentil(datos, 25);
estadisticas.p75 = percentil(datos, 75);
estadisticas.iqr = estadisticas.p75 - estadisticas.p25;
```

---

## Cálculos financieros

```javascript
// Interés compuesto: A = P(1 + r/n)^(nt)
function interesCompuesto(principal, tasaAnual, vecesAnio, anios) {
  const r = tasaAnual / 100;
  const amount = principal * Math.pow(1 + r / vecesAnio, vecesAnio * anios);
  return {
    capital_inicial: principal,
    tasa_anual_pct: tasaAnual,
    anios: anios,
    monto_final: Number(amount.toFixed(2)),
    intereses_ganados: Number((amount - principal).toFixed(2))
  };
}

// Cuota de préstamo (amortización)
function cuotaPrestamo(principal, tasaAnualPct, meses) {
  const r = tasaAnualPct / 100 / 12;
  if (r === 0) return principal / meses;
  const cuota = principal * (r * Math.pow(1 + r, meses)) / (Math.pow(1 + r, meses) - 1);
  return {
    cuota_mensual: Number(cuota.toFixed(2)),
    total_pagado: Number((cuota * meses).toFixed(2)),
    total_intereses: Number((cuota * meses - principal).toFixed(2))
  };
}
```

---

## Números grandes (BigInt)

```javascript
// Para factoriales, combinatorias u operaciones que superan Number.MAX_SAFE_INTEGER
function factorialBig(n) {
  let result = 1n;
  for (let i = 2n; i <= BigInt(n); i++) result *= i;
  return result.toString(); // devolver como string para JSON
}

factorialBig(50) // "30414093201713378043612608166979581188299763898377856000000000000"

// Combinaciones C(n, k)
function combinacion(n, k) {
  if (k > n) return 0n;
  let num = 1n, den = 1n;
  for (let i = 0n; i < BigInt(k); i++) {
    num *= BigInt(n) - i;
    den *= i + 1n;
  }
  return (num / den).toString();
}
```

---

## Formato de resultado recomendado para cálculos

```javascript
const result = {
  status: "ok",
  operation: "descripción del cálculo",
  inputs: { /* parámetros usados */ },
  result: valorCalculado,
  precision_note: "calculado con mathjs / enteros escalados"
};
console.log(JSON.stringify(result, null, 2));
```

---

## Reglas de precisión

| Tipo de cálculo | Método recomendado |
|---|---|
| Dinero / finanzas | Enteros en centavos + `toFixed(2)` al mostrar |
| Estadísticas generales | `mathjs` |
| Números muy grandes (>2⁵³) | `BigInt` |
| Álgebra / unidades | `mathjs.evaluate()` |
| Trigonometría / geometría | `Math.*` nativo (precisión suficiente) |
