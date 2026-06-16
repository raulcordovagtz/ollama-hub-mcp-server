# 🧬 Guía Maestra de Difusión de Texto (MLX Infrastructure)

Este documento detalla la operación del servidor de inferencia por difusión discreta para generación de texto.

---

## 🚀 Perfil del Modelo

### `diffusiongemma-26B-A4B-it-4bit`

**Especialidad:** Generación de Texto por Difusión Discreta (Block-Autoregressive Denoising).

* **Perfil:** El "Motor de Difusión Textual".
* **Arquitectura:** Encoder-Decoder con Mixture-of-Experts (MoE). 26B parámetros totales, **3.8B activos** (8 expertos activos de 128 totales + 1 compartido).
* **Cuantización:** 4-bit (affine) con capas selectas en 8-bit para estabilidad.
* **Canvas:** Genera bloques de **256 tokens en paralelo** mediante denoising iterativo (hasta 48 pasos).
* **Contexto:** Hasta 256K tokens.
* **Motor:** `mlx-vlm` v0.6.3 sobre Apple Silicon (MLX).

### ¿Qué es la Difusión de Texto?

A diferencia de los modelos autorregresivos (token a token), DiffusionGemma:

1. **Inicializa** un canvas de 256 tokens aleatorios.
2. **Desruida (denoise)** iterativamente todo el bloque en paralelo.
3. Los tokens de alta confianza ayudan a resolver posiciones adyacentes.
4. Una vez completo, el bloque se consolida y se inicia el siguiente canvas.

**Ventaja principal:** Auto-corrección bidireccional. El modelo puede "arreglar" errores previos porque ve todo el contexto simultáneamente.

---

## ⚙️ Arquitectura del Servidor (v1.0)

El servidor en el puerto **8011** gestiona la inteligencia por difusión:

1. **Carga Lazy:** El modelo se carga solo cuando llega la primera petición (~15 GB en memoria unificada).
2. **Accounting:** Registra cada inferencia en `/logs/diffusion/inference.log` con duración y configuración.
3. **Serialización:** Cola de 5 posiciones, 1 worker. Procesa 1 a 1 para proteger la CPU/GPU del MacBook.
4. **Auto-apagado:** 1200s de inactividad apaga el servidor para liberar memoria.

---

## 🔧 Parámetros de Sampling Recomendados

Basados en la guía oficial de Google DeepMind:

| Parámetro | Valor | Descripción |
|---|---|---|
| Max Denoising Steps | 48 | Máximo de pasos de denoising por canvas |
| Temperature (t_max → t_min) | 0.8 → 0.4 | Decaimiento lineal para logit shaping |
| Entropy Bound | 0.1 | Umbral de selección de tokens por información mutua |
| Confidence Threshold | 0.005 | Entropía promedio mínima para early stopping |
| Stability Threshold | 1 | Predicciones idénticas en 2 pasos consecutivos |

---

## 🧠 Thinking Mode

DiffusionGemma soporta modo de razonamiento:

* **Activar:** Incluir `<|think|>` al inicio del system prompt.
* **Salida:** `<|channel>thought\n[razonamiento]<channel|>` seguido de la respuesta final.
* **Desactivar:** Omitir el token `<|think|>`.

---

## ⚠️ Notas de Hardware

* **Consumo:** ~15 GB de memoria unificada con la versión 4-bit.
* **Costo Térmico:** Alto durante la carga inicial. Moderado en inferencia gracias al MoE (solo 3.8B activos).
* **Recomendación:** No cargar simultáneamente con modelos de imagen pesados (z-image 12GB).
* **Monitoreo:** Obligatorio usar `monitor_resources.sh` en sesiones largas.

---
**Estado:** Producción Experimental. 🧬
