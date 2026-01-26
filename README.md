# 🌐 Infraestructura de Servidores Inteligentes (v6.8)

Repositorio unificado para la gestión de servicios de IA local en Apple Silicon.

## 📁 Estructura del Proyecto

```text
server/
├── tts/              # Audio (Text-to-Speech)
│   └── engine-mlx/      | Motor Kokoro (MLX) - Puerto 8007
├── image/            # Imagen (Generación/Edición)
│   └── engine-ollama/   | Z-Image / Flux2 - Puerto 8010
├── text/             # Texto y Visión (LLM/VLM)
│   └── engine-ollama/   | Qwen3 / Granite - Puerto 8009
├── logs/             # Registros centralizados
├── scripts/          # Utilidades de control
└── vision/outputs/   # Galería de resultados
```

## 🛠️ Herramientas de Control (Carpeta `scripts/`)

1. **`emergency_stop.sh` (Botón Rojo):** Detiene todos los servidores y vacía la VRAM de Ollama inmediatamente.
2. **`monitor_resources.sh`:** Monitor térmico y de memoria en tiempo real con alertas acústicas.

## 🚀 Criterios Operativos (Estrategia Industrial)

* **Prioridad Térmica:** Procesamiento serializado para mantener la temperatura bajo control.
* **Gestión de Inventario:** Colas dinámicas con límites de seguridad (max 10 imágenes/textos).
* **Balance Calidad/Costo:**
  * **Imagen:** Arista máx 720px | 4 Steps default.
  * **Modelos:** T2I (Z-Image) | I2I+Text (Flux2) | Análisis (Qwen3-VL).

## 📝 Historial de Casos de Éxito

* **Simulación Natural:** Generación exitosa de retrato "Joven Pirata" con integración de datos de sistema y texto multilingüe.

---
**Estado:** Producción Optimizada. 🏆
