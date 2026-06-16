
---

## 🍎 **Apps Nativas de Apple con Soporte AppleScript Robusto**

### **Productividad y Gestión de Información**

| App | Capacidades Clave | Caso de Uso MCP |
|-----|-------------------|-----------------|
| **Finder** | Control total del sistema de archivos, ventanas, etiquetas | Navegación, búsqueda, organización de archivos por el LLM |
| **Mail** | Leer, enviar, organizar correos, gestionar buzones | "Resume mis correos no leídos", "Responde a Juan sobre..." |
| **Calendar** | Crear/editar eventos, buscar en calendario | Gestión de agenda, conflictos de horario |
| **Contacts** | Buscar, crear, editar contactos | "Busca el email de María", "Añade contacto..." |
| **Notes** | Crear, buscar, adjuntar en notas | Base de conocimiento persistente del LLM |
| **Reminders** | Crear/completar tareas, listar listas | Sistema de tareas del LLM |
| **Messages** | Enviar iMessage/SMS, leer conversaciones | Comunicación automatizada |

### **Media y Contenido**

| App | Capacidades Clave |
|-----|-------------------|
| **Photos** | Buscar, exportar, crear álbumes, obtener metadatos |
| **Preview** | Manipular PDFs, imágenes, anotaciones |
| **TV/Podcasts** | Control de reproducción, buscar contenido |

### **Navegación y Web**

| App | Capacidades Clave |
|-----|-------------------|
| **Safari** | Navegar, extraer contenido, llenar formularios, tabs |
| **Terminal** | Ejecutar comandos shell, scripts |

---

## 🔧 **Apps de Terceros con Excelente Soporte AppleScript**

### **Gestión de Tareas y Proyectos**

```
OmniFocus     → Proyectos, tareas, perspectivas, revisión
Things 3      → Tareas, áreas, proyectos con etiquetas
Todoist       → A través de URL schemes + AppleScript
```

### **Notas y Conocimiento**

```
Bear          → Notas, tags, exportar markdown
Obsidian      → A través de URI scheme + AppleScript
DEVONthink    → Búsqueda, importar, exportar, clasificar
Drafts        → Captura rápida, procesamiento de texto
Craft         → Documentos, bloques
```

### **Desarrollo y Texto**

```
BBEdit        → Edición de texto, búsquedas regex
VS Code       → A través de CLI + AppleScript
Sublime Text  → Similar a BBEdit
```

### **Comunicación**

```
Slack         → Mensajes, canales (limitado pero útil)
Zoom          → Iniciar reuniones, controlar llamadas
```

---

## 🎯 **Integraciones Especialmente Valiosas para LLMs**

### **1. System Events - Control de UI**

```applescript
-- Controlar cualquier app sin diccionario nativo
tell application "System Events"
    tell process "AppName"
        click menu item "Export" of menu "File" of menu bar 1
    end tell
end tell
```

*Permite controlar CUALQUIER aplicación vía UI automation*

### **2. Shortcuts App (macOS Monterey+)**

- Puente a más de 200 acciones del sistema
- Ejecutar atajos desde AppleScript
- Acceso a APIs que AppleScript nativo no tiene

```applescript
do shell script "shortcuts run 'NombreDelAtajo'"
```

### **3. shell + CLI Tools**

```applescript
-- Combinar AppleScript con herramientas CLI
do shell script "jq '.key' file.json"
do shell script "curl -s 'https://api.example.com'"
```

---

## 🌟 **Ideas de Hubs MCP Adicionales**

| Hub MCP | Descripción | Valor para LLM |
|---------|-------------|----------------|
| **FileManager Hub** | Finder + Preview + Terminal | Manipulación completa de archivos |
| **Communication Hub** | Mail + Messages + Contacts | Gestión de comunicaciones |
| **Productivity Hub** | Calendar + Reminders + Notes | Organización personal |
| **Knowledge Hub** | DEVONthink + Bear + Safari | Búsqueda en conocimiento personal |
| **System Hub** | System Events + Shortcuts | Control total del sistema |

---

## 💡 **Apps Menos Conocidas pero Muy Útiles**

1. **Script Editor** - Para depurar y explorar diccionarios AppleScript
2. **Automator** - Crear servicios y flujos que AppleScript puede invocar
3. **Image Events** - Procesamiento de imágenes sin abrir apps
4. **Database Events** - Trabajar con bases de datos SQLite
5. **Keychain Scripting** - Acceso seguro a contraseñas

---

## 🔍 **Cómo Descubrir Más Apps con AppleScript**

En **Script Editor** → **File** → **Open Dictionary** (⇧⌘O) verás todas las apps instaladas que tienen diccionario AppleScript.

---
