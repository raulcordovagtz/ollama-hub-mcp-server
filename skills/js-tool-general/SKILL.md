---
name: js-tool-general
description: Meta-skill base para la herramienta run_javascript en LM Studio (entorno Deno). Úsalo siempre como base.
---

# Skill: js-tool-general
**Meta-skill base para la herramienta `run_javascript` en LM Studio (entorno Deno)**

---

## ¿Cuándo activar este skill?

Actívalo siempre que el usuario pida:
- "ejecuta este código", "calcula esto", "corre un script"
- Cualquier tarea que vaya a usar `run_javascript`
- Como capa base cuando usas cualquier otro skill JS específico

---

## Entorno de ejecución

La herramienta `run_javascript` usa **Deno**, NO Node.js. Diferencias clave:

| Característica | Node.js (NO disponible) | Deno (disponible) |
|---|---|---|
| Instalar paquetes | `npm install` | Import por URL o import maps |
| Módulos | `require()` | `import` ES Modules |
| APIs web | Emuladas | Nativas (`fetch`, `URL`, `crypto`) |
| Archivos | `fs` module | `Deno.readTextFile()` |

### Importar librerías externas en Deno

```javascript
// ✅ Correcto: importar por URL (preferir JSR o deno.land/x)
import { parse } from "https://deno.land/std/csv/mod.ts";
import * as mathjs from "https://esm.sh/mathjs";

// ❌ Incorrecto: esto NO funciona en Deno
const _ = require('lodash');
```

---

## Formato de salida estándar (OBLIGATORIO)

**Siempre** termina el script con `console.log(JSON.stringify(result))`.

```javascript
// ✅ Formato correcto
const result = {
  status: "ok",
  data: /* tu resultado aquí */,
  metadata: {
    computed_at: new Date().toISOString()
  }
};
console.log(JSON.stringify(result, null, 2));

// ❌ Evitar: salida de texto plano difícil de parsear
console.log("El resultado es: " + value);
```

---

## Manejo de errores estándar

Siempre envuelve el código principal en try/catch:

```javascript
try {
  // lógica principal aquí
  const result = { status: "ok", data: output };
  console.log(JSON.stringify(result, null, 2));

} catch (error) {
  const errorResult = {
    status: "error",
    message: error.message,
    stack: error.stack?.split('\n').slice(0, 3)
  };
  console.error(JSON.stringify(errorResult, null, 2));
  Deno.exit(1);
}
```

---

## Restricciones del entorno

1. **Script de un solo uso**: no dejes servidores, intervalos o procesos en background. El script debe ejecutar, producir output y terminar.
2. **Timeout**: el script tiene un límite de tiempo. Para operaciones largas, optimiza antes de ejecutar.
3. **No persistencia**: no hay estado entre ejecuciones. Cada llamada a `run_javascript` es aislada.
4. **Sin UI**: no intentes abrir ventanas, browsers o interfaces gráficas.

```javascript
// ❌ Incorrecto: proceso en background
setInterval(() => console.log("tick"), 1000);

// ✅ Correcto: ejecutar y terminar
const result = await computeSomething();
console.log(JSON.stringify(result));
```

---

## Plantilla base (copiar y adaptar)

```javascript
// Importaciones (si necesitas librerías externas)
// import { algo } from "https://...";

async function main() {
  // Tu lógica aquí
  const data = /* ... */;
  
  return {
    status: "ok",
    data: data,
    metadata: {
      computed_at: new Date().toISOString()
    }
  };
}

try {
  const result = await main();
  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  console.error(JSON.stringify({
    status: "error",
    message: error.message
  }, null, 2));
  Deno.exit(1);
}
```

---

## Checklist antes de llamar a `run_javascript`

- [ ] ¿El script termina con `console.log(JSON.stringify(...))`?
- [ ] ¿Tiene try/catch con error en formato JSON?
- [ ] ¿Usa imports de URL (no `require` ni `npm`)?
- [ ] ¿No deja procesos en background?
- [ ] ¿Se puede ejecutar en un solo paso sin input interactivo?
