---
name: js-web-fetch
description: Llamadas a APIs externas y web scraping con JavaScript/Deno. Requiere aplicar primero js-tool-general.
---

# Skill: js-web-fetch
**Llamadas a APIs externas y web scraping con JavaScript/Deno**

> **Requiere**: Aplicar primero `js-tool-general` para el formato de salida y manejo de errores.

---

## ¿Cuándo activar este skill?

- "llama a esta API", "obtén datos de esta URL"
- "extrae información de esta página web"
- Integración con servicios REST, JSON APIs
- Descargar y procesar contenido remoto

---

## Fetch básico (API REST con JSON)

```javascript
// GET simple
const response = await fetch("https://api.ejemplo.com/datos");
if (!response.ok) {
  throw new Error(`HTTP ${response.status}: ${response.statusText}`);
}
const data = await response.json();

// GET con headers (autenticación, etc.)
const resp = await fetch("https://api.ejemplo.com/endpoint", {
  headers: {
    "Authorization": "Bearer TU_TOKEN",
    "Content-Type": "application/json",
    "User-Agent": "Deno/1.0 LMStudio-Tool"
  }
});

// POST con body JSON
const postResp = await fetch("https://api.ejemplo.com/submit", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ clave: "valor" })
});
const respData = await postResp.json();
```

---

## Fetch con timeout (evitar colgarse)

```javascript
// AbortController para timeout manual
async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    return response;
  } finally {
    clearTimeout(timer);
  }
}

const resp = await fetchWithTimeout("https://api.ejemplo.com/lento", {}, 5000);
```

---

## Web scraping básico (parsear HTML)

Deno no tiene DOM nativo. Opciones:

```javascript
// Opción A: expresiones regulares para casos simples (texto plano, meta tags)
const html = await fetch("https://ejemplo.com").then(r => r.text());
const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
const title = titleMatch?.[1]?.trim();

// Opción B: con librería de parsing HTML (recomendado para scraping complejo)
import { DOMParser } from "https://deno.land/x/deno_dom@v0.1.45/deno-dom-wasm.ts";

const htmlText = await fetch("https://ejemplo.com").then(r => r.text());
const doc = new DOMParser().parseFromString(htmlText, "text/html");

// Usar selectores CSS
const links = [...doc.querySelectorAll("a[href]")]
  .map(a => ({ text: a.textContent?.trim(), href: a.getAttribute("href") }))
  .filter(l => l.href && !l.href.startsWith("#"));

const paragraphs = [...doc.querySelectorAll("article p")]
  .map(p => p.textContent?.trim())
  .filter(Boolean);
```

---

## Múltiples requests en paralelo

```javascript
// Fetch paralelo con Promise.all (cuidado con rate limits)
const urls = [
  "https://api.ejemplo.com/item/1",
  "https://api.ejemplo.com/item/2",
  "https://api.ejemplo.com/item/3"
];

const results = await Promise.all(
  urls.map(url => fetch(url).then(r => r.json()))
);

// Con pausa entre requests (respetar rate limits)
async function fetchSequential(urls, delayMs = 500) {
  const results = [];
  for (const url of urls) {
    const data = await fetch(url).then(r => r.json());
    results.push(data);
    await new Promise(r => setTimeout(r, delayMs));
  }
  return results;
}
```

---

## Manejo de respuestas no-JSON

```javascript
// Texto plano
const texto = await fetch(url).then(r => r.text());

// Verificar Content-Type antes de parsear
const resp = await fetch(url);
const contentType = resp.headers.get("content-type") || "";

let data;
if (contentType.includes("application/json")) {
  data = await resp.json();
} else if (contentType.includes("text/")) {
  data = await resp.text();
} else {
  // Binario: guardar o encodear
  const buffer = await resp.arrayBuffer();
  data = `[binary: ${buffer.byteLength} bytes]`;
}
```

---

## Formato de resultado recomendado para fetch

```javascript
const result = {
  status: "ok",
  source: url,
  fetched_at: new Date().toISOString(),
  http_status: response.status,
  data: extractedData
};
console.log(JSON.stringify(result, null, 2));
```

---

## Buenas prácticas

- **Siempre** valida `response.ok` antes de parsear
- **Agrega** `User-Agent` descriptivo en headers
- **Respeta** rate limits con pausas entre requests
- **No** hagas scraping agresivo; descarga solo lo necesario
- **Maneja** redirects (`fetch` los sigue automáticamente en Deno)
- Si la URL usa HTTPS y falla, verifica que no sea por certificado autofirmado
