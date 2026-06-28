import os
import sys
import time
import json
import uuid
import logging
import asyncio
import fnmatch
import subprocess
import threading
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

# Usamos stdlib para evitar dependencias externas adicionales, 
# confiando en fastapi/uvicorn/pydantic que ya están en el conda env.
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# =============================================================================
# Logging & Configuration
# =============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FASTCONTEXT_SERVER")

PORT = 8015
LOG_DIR = "/Users/crotalo/desarrollo-local/server/logs/fastcontext"
os.makedirs(LOG_DIR, exist_ok=True)
SERVER_LOG = os.path.join(LOG_DIR, "server.log")

# =============================================================================
# State Management & Inactivity Timer
# =============================================================================
active_tasks: Dict[str, Dict[str, Any]] = {}
last_request_time = time.time()
idle_timeout_seconds = 1200  # 20 minutos

def inactivity_checker():
    """Apaga el servidor si ha estado inactivo durante más de 20 minutos."""
    global last_request_time
    while True:
        time.sleep(30)
        elapsed = time.time() - last_request_time
        if elapsed > idle_timeout_seconds and not any(task.get("status") == "running" for task in active_tasks.values()):
            logger.info("⏱️  Servidor inactivo por 20 minutos. Matando SGLang y forzando suicidio controlado.")
            # Matar el servidor de SGLang (liberar VRAM)
            os.system("pkill -f sglang.launch_server")
            # Forzar cierre inmediato del arnés
            os._exit(0)

# Iniciar checker de inactividad
threading.Thread(target=inactivity_checker, daemon=True).start()

# =============================================================================
# API Models
# =============================================================================
class ExploreRequest(BaseModel):
    repo_path: str
    query: str
    architecture: Optional[str] = None
    file_patterns: Optional[List[str]] = None
    max_tokens_budget: Optional[int] = 100000

class OntologyRequest(BaseModel):
    repo_path: str
    architecture: Optional[str] = None

# =============================================================================
# Módulo de Ontología (AST / Heurísticas)
# =============================================================================
class OntologyBuilder:
    @staticmethod
    def get_ontology(repo_path: str, user_arch: Optional[str] = None) -> str:
        """Genera el mapa mental del proyecto (Vista de Pájaro)."""
        if not os.path.isdir(repo_path):
            raise ValueError(f"La ruta del repositorio no es válida: {repo_path}")

        # 1. Identificar librerías del proyecto
        manifests = {}
        for root, _, files in os.walk(repo_path):
            if any(p in root for p in [".git", "node_modules", "venv", ".venv", "__pycache__"]):
                continue
            for f in files:
                if f in ["requirements.txt", "package.json", "setup.py", "Cargo.toml", "go.mod"]:
                    full_path = os.path.join(root, f)
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as file:
                            content = file.read(4000)  # Leer primeras líneas
                            manifests[f] = content
                    except Exception as e:
                        manifests[f] = f"Error leyendo archivo: {e}"

        # 2. Heurísticas de Hardware
        hardware_libs = []
        for content in manifests.values():
            if "mlx" in content.lower():
                hardware_libs.append("Apple Silicon MLX")
            if "torch" in content.lower() or "pytorch" in content.lower():
                hardware_libs.append("PyTorch (MPS/CUDA)")
            if "tensorflow" in content.lower():
                hardware_libs.append("TensorFlow")

        # 3. Analizar código (AST Python, regex simples para otros)
        files_overview = []
        import ast
        import re

        py_class_func = {}
        other_files = []

        for root, dirs, files in os.walk(repo_path):
            # Ignorar directorios comunes
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"]]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar.gz", ".exe", ".dll", ".so", ".dylib", ".pyc", ".db", ".sqlite"]:
                    continue
                
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, repo_path)
                
                # Tamaño y tokens estimados
                try:
                    sz = os.path.getsize(full_path)
                except OSError:
                    sz = 0
                est_tokens = int(sz / 4)

                if ext == ".py":
                    classes_found = []
                    funcs_found = []
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                            tree = ast.parse(fp.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                classes_found.append(node.name)
                            elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                                funcs_found.append(node.name)
                    except Exception:
                        pass
                    py_class_func[rel_path] = {
                        "classes": classes_found[:5], 
                        "functions": funcs_found[:10],
                        "tokens": est_tokens
                    }
                elif ext in [".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".cpp", ".h"]:
                    # Regex simple para encontrar funciones/clases en otros lenguajes
                    classes_found = []
                    funcs_found = []
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                            text = fp.read()
                            # Clases
                            classes_found = re.findall(r'(?:class|struct)\s+(\w+)', text)[:5]
                            # Funciones comunes
                            funcs_found = re.findall(r'(?:function|fn|def)\s+(\w+)\(', text)[:10]
                    except Exception:
                        pass
                    py_class_func[rel_path] = {
                        "classes": classes_found,
                        "functions": funcs_found,
                        "tokens": est_tokens
                    }
                else:
                    other_files.append((rel_path, est_tokens))

        # Estructurar reporte local (Markdown)
        report_lines = []
        report_lines.append("# 🌐 Reporte de Ontología y Vista de Pájaro")
        report_lines.append(f"**Ruta del Proyecto:** `{repo_path}`")
        if hardware_libs:
            report_lines.append(f"**Hardware Detectado:** {', '.join(hardware_libs)}")
        
        if user_arch:
            report_lines.append(f"\n## 🏛️ Arquitectura Suministrada por el Usuario\n{user_arch}")

        report_lines.append("\n## 📦 Manifiestos y Dependencias")
        for fn, content in manifests.items():
            report_lines.append(f"### `{fn}`")
            report_lines.append("```text")
            report_lines.append(content[:1000] + ("\n... [Truncado]" if len(content) > 1000 else ""))
            report_lines.append("```")

        report_lines.append("\n## 🏛️ Clases y Funciones Clave")
        for rp, meta in py_class_func.items():
            if not meta["classes"] and not meta["functions"]:
                continue
            report_lines.append(f"### File: `{rp}` (Est. Tokens: {meta['tokens']})")
            if meta["classes"]:
                report_lines.append(f"- **Clases:** {', '.join(meta['classes'])}")
            if meta["functions"]:
                report_lines.append(f"- **Funciones:** {', '.join(meta['functions'])}")

        report_lines.append("\n## 📁 Otros Archivos Relevantes")
        for rp, tks in other_files[:20]:
            report_lines.append(f"- `{rp}` (Est. Tokens: {tks})")

        raw_ontology = "\n".join(report_lines)

        # Si hay GEMINI_API_KEY, pulir con Gemini
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                import urllib.request
                gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
                headers = {"Content-Type": "application/json"}
                prompt = (
                    "Toma esta ontología cruda de un repositorio de código y redacta un reporte de arquitectura "
                    "impecable en Markdown para un desarrollador senior. Destaca la estructura principal, frameworks, "
                    "flujos del código y dependencias. Mantén el formato ordenado.\n\n"
                    f"Ontología Cruda:\n{raw_ontology}"
                )
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                req = urllib.request.Request(
                    f"{gemini_url}?key={api_key}",
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    text = res_body['candidates'][0]['content']['parts'][0]['text']
                    return text
            except Exception as e:
                logger.error(f"Error llamando a Gemini para pulir ontología: {e}")
                return raw_ontology + f"\n\n*(Nota: No se pudo pulir con Gemini por error: {e})*"
        
        return raw_ontology

# =============================================================================
# Motor de Herramientas Locales (READ, GLOB, GREP)
# =============================================================================
class LocalToolsEngine:
    def __init__(self, repo_path: str, file_patterns: Optional[List[str]] = None):
        self.repo_path = repo_path
        self.file_patterns = file_patterns

    def is_allowed_file(self, rel_path: str) -> bool:
        """Verifica si el archivo coincide con los patrones solicitados (si existen)."""
        if not self.file_patterns:
            return True
        for pattern in self.file_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
        return False

    def READ(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """Lee el contenido de un archivo con numeración de líneas y límites preventivos."""
        # Resolver ruta absoluta y validar seguridad
        abs_path = os.path.abspath(os.path.join(self.repo_path, path))
        if not abs_path.startswith(os.path.abspath(self.repo_path)):
            return f"Error: Acceso denegado (fuera del repositorio)."

        if not os.path.isfile(abs_path):
            return f"Error: El archivo '{path}' no existe o no es un archivo válido."

        if not self.is_allowed_file(path):
            return f"Error: El archivo '{path}' no coincide con los patrones de archivo filtrados."

        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error leyendo el archivo: {e}"

        total_lines = len(lines)

        # Límite preventivo de truncado
        if start_line is None and end_line is None:
            if total_lines > 1000:
                return (
                    f"Error: El archivo '{path}' es demasiado grande ({total_lines} líneas).\n"
                    f"Por seguridad de contexto/VRAM, se ha bloqueado la lectura completa.\n"
                    f"Por favor usa la herramienta especificado los parámetros start_line y end_line "
                    f"(ej. start_line=1, end_line=500)."
                )
            start_line = 1
            end_line = total_lines

        start = max(1, start_line or 1)
        end = min(total_lines, end_line or total_lines)

        output = []
        for i in range(start - 1, end):
            output.append(f"{i + 1}: {lines[i]}")

        # Retornar texto numerado
        header = f"--- [Leyendo {path} | Líneas {start}-{end} de {total_lines}] ---\n"
        return header + "".join(output)

    def GLOB(self, pattern: str) -> List[str]:
        """Busca archivos que coincidan con un patrón glob recursivo."""
        matches = []
        # Normalizar patrón si inicia con **/
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"]]
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, self.repo_path)
                
                # Check filter patterns
                if not self.is_allowed_file(rel_path):
                    continue

                # Coincidir con el patrón glob enviado por la IA
                if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(f, pattern) or fnmatch.fnmatch(rel_path, f"**/{pattern}"):
                    matches.append(rel_path)

        return sorted(list(set(matches)))[:100]  # Limitar a los primeros 100 resultados

    def GREP(self, query_regex: str) -> str:
        """Búsqueda por expresión regular usando ripgrep o fallback de Python."""
        # Intentar ejecutar con ripgrep para máxima velocidad en la Mac
        try:
            # -n: line number, -I: ignore binary files, -H: show filename, --max-count: limit matches per file
            cmd = ["rg", "-n", "-H", "-I", "--max-count", "20", query_regex, self.repo_path]
            # Ejecutar con timeout para evitar colgarse
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, errors="ignore")
            if result.returncode in [0, 1]:  # 0 = matches, 1 = no matches
                lines = result.stdout.strip().split("\n")
                cleaned_lines = []
                for line in lines:
                    if not line:
                        continue
                    # Reemplazar la ruta absoluta por la relativa en el output
                    cleaned_line = line.replace(self.repo_path + "/", "")
                    cleaned_lines.append(cleaned_line)
                
                # Filtrar con is_allowed_file
                final_lines = []
                for cl in cleaned_lines:
                    parts = cl.split(":", 1)
                    if len(parts) > 0 and self.is_allowed_file(parts[0]):
                        final_lines.append(cl)

                if not final_lines:
                    return "No se encontraron coincidencias."
                return "\n".join(final_lines[:150])  # Limitar tamaño de salida
        except (FileNotFoundError, subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.info(f"Fallback a Python Regex Grep por error en ripgrep: {e}")

        # Fallback nativo en Python usando expresiones regulares
        import re
        try:
            pattern = re.compile(query_regex, re.IGNORECASE)
        except re.error as e:
            return f"Error: Patrón regex inválido: {e}"

        matches = []
        match_count = 0
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"]]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".tar.gz", ".exe", ".dll", ".so", ".dylib", ".pyc"]:
                    continue

                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, self.repo_path)
                
                if not self.is_allowed_file(rel_path):
                    continue

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                        for l_idx, line in enumerate(fp):
                            if pattern.search(line):
                                matches.append(f"{rel_path}:{l_idx+1}:{line.strip()}")
                                match_count += 1
                                if match_count >= 150:
                                    break
                except Exception:
                    pass
                if match_count >= 150:
                    break
            if match_count >= 150:
                break

        if not matches:
            return "No se encontraron coincidencias."
        return "\n".join(matches)

# =============================================================================
# Orquestador del Modelo 4B
# =============================================================================
class FastContextOrchestrator:
    def __init__(self, task_id: str, repo_path: str, query: str, architecture: Optional[str] = None, file_patterns: Optional[List[str]] = None):
        self.task_id = task_id
        self.repo_path = repo_path
        self.query = query
        self.architecture = architecture
        self.tools = LocalToolsEngine(repo_path, file_patterns)
        
        # Cargar configuración desde el entorno (con fallback a 8080 para MPS PyTorch nativo)
        self.api_base = os.environ.get("FASTCONTEXT_API_BASE", "http://localhost:8080/v1")
        self.model_name = os.environ.get("FASTCONTEXT_MODEL", "FastContext-1.0-4B-SFT")
        
        # Historial de exploración
        self.exploration_log = []

    def log(self, text: str):
        logger.info(f"[{self.task_id}] {text}")
        self.exploration_log.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text}")

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Ejecuta una herramienta en local y la formatea."""
        self.log(f"🔧 Ejecutando herramienta local: {name} con argumentos {args}")
        if name == "READ":
            path = args.get("path")
            start = args.get("start_line")
            end = args.get("end_line")
            # Soporte para alias de parámetros
            if start is None: start = args.get("start")
            if end is None: end = args.get("end")
            res = self.tools.READ(path, start, end)
            # Truncar visualización en el log de auditoría
            self.log(f"   ↳ [READ] {path}: Leídas {len(res.splitlines())} líneas.")
            return res
        elif name == "GLOB":
            pattern = args.get("pattern")
            res = self.tools.GLOB(pattern)
            self.log(f"   ↳ [GLOB] {pattern}: Encontrados {len(res)} archivos.")
            return json.dumps(res)
        elif name == "GREP":
            query_regex = args.get("query") or args.get("pattern")
            res = self.tools.GREP(query_regex)
            self.log(f"   ↳ [GREP] '{query_regex}': Encontradas {len(res.splitlines())} coincidencias.")
            return res
        else:
            self.log(f"   ↳ [ERROR] Herramienta desconocida: {name}")
            return f"Error: Herramienta desconocida '{name}'."

    def check_cancellation(self):
        """Revisa si el usuario solicitó abortar la tarea."""
        if active_tasks.get(self.task_id, {}).get("cancelled", False):
            self.log("⚠️  Cancelación activa detectada. Abortando inferencia...")
            raise asyncio.CancelledError("Inferencia cancelada por el usuario.")

    def parse_plain_text_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Parsea llamadas a herramientas emitidas en formato XML-JSON por FastContext-4B.
        Ejemplo:
        <tool_call>
        {"name": "GLOB", "arguments": {"pattern": "**/*.py"}}
        </tool_call>
        """
        import re
        import json
        calls = []
        
        # Detectar el bloque de tool_call explícito (entrenamiento RL)
        matches = re.finditer(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', text, re.DOTALL)
        for m in matches:
            try:
                tc_json = json.loads(m.group(1))
                name = tc_json.get("name")
                arguments = tc_json.get("arguments", {})
                if name:
                    calls.append({"name": name, "arguments": arguments})
            except Exception as e:
                self.log(f"Error parseando JSON de tool_call: {e}")

        # Fallback histórico para otros formatos (opcional)
        if not calls:
            special_matches = re.finditer(r'✿FUNCTION✿:\s*(\w+)\s*\n✿ARGS✿:\s*(\{.*?\})', text, re.DOTALL)
            for m in special_matches:
                try:
                    args = json.loads(m.group(2).strip())
                    calls.append({"name": m.group(1).strip(), "arguments": args})
                except Exception:
                    pass

        return calls

    async def run_exploration_loop(self) -> Dict[str, Any]:
        """Bucle principal de exploración del Sub-Agente FastContext-4B."""
        start_time = time.perf_counter()
        
        # 1. Obtener Ontología del Proyecto para iniciar con contexto estructurado
        self.log("Scaneando arquitectura inicial del proyecto...")
        ontology = OntologyBuilder.get_ontology(self.repo_path, self.architecture)
        
        # Definición de herramientas para la API de OpenAI
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": "READ",
                    "description": "Devuelve el contenido del archivo con líneas numeradas. El tamaño está estrictamente truncado a 1000 líneas si no especificas rango.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Ruta relativa del archivo (ej. src/auth.py)"},
                            "start_line": {"type": "integer", "description": "Línea inicial para paginar (1-indexed)"},
                            "end_line": {"type": "integer", "description": "Línea final para paginar (1-indexed)"}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "GLOB",
                    "description": "Descubre archivos en el proyecto mediante un patrón glob recursivo (ej. **/auth/*.py o *.json).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "El patrón de coincidencia (ej. **/database.py)"}
                        },
                        "required": ["pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "GREP",
                    "description": "Busca coincidencias exactas o regex en todo el contenido de los archivos usando ripgrep local (rápido).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Patrón regex o texto plano a buscar"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        # 2. Historial de la conversación con el Sub-Agente (strictly in English for optimal RL tool-calling)
        system_prompt = (
            "You are an expert repository explorer agent (FastContext-4B). Your sole objective is to locate "
            "the code fragments, files, and line ranges relevant to the user's query.\n"
            "You have access to 3 read-only tools: READ, GLOB, GREP.\n"
            "KEY INSTRUCTIONS:\n"
            "1. Start by analyzing the repository's architectural map and issue tools to explore.\n"
            "2. When you find the definitive answer, output a formatted '<final_answer>' block containing exact files and line ranges.\n"
            "3. DO NOT attempt to solve coding problems; only locate the evidence so the main agent can solve it.\n"
            "4. Respect context limits. If reading files, use constrained line ranges."
        )

        user_prompt = (
            f"Search Query: \"{self.query}\"\n\n"
            f"Repository Architecture Ontology:\n{ontology}\n\n"
            "Begin your exploration by calling the appropriate tools."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Límite máximo de iteraciones para evitar bucles infinitos
        max_turns = 12
        final_response_text = ""
        tokens_consumed = 0

        self.log(f"Iniciando bucle de exploración con modelo {self.model_name} en API {self.api_base}...")

        # Guardar en active_tasks para poder cancelar peticiones HTTP activas
        active_tasks[self.task_id]["status"] = "running"

        import urllib.request
        import urllib.error

        for turn in range(max_turns):
            self.check_cancellation()
            self.log(f"--- Turno {turn + 1} de {max_turns} ---")

            # Construir payload para endpoint compatible con OpenAI
            payload = {
                "model": self.model_name,
                "messages": messages,
                "tools": openai_tools,
                "tool_choice": "auto",
                "temperature": 0.2
            }

            req_url = f"{self.api_base}/chat/completions"
            req = urllib.request.Request(
                req_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            # Guardar referencia del Request activo para permitir cancelaciones si fuera necesario
            active_tasks[self.task_id]["active_req"] = req

            try:
                # Realizar llamada asíncrona simulada en ejecutor
                def call_endpoint():
                    with urllib.request.urlopen(req, timeout=120) as response:
                        return json.loads(response.read().decode("utf-8"))

                self.log("Esperando respuesta del modelo local...")
                # Correr en un hilo separado para que no bloquee el loop asíncrono y podamos cancelar
                loop = asyncio.get_running_loop()
                response_body = await loop.run_in_executor(None, call_endpoint)
                
            except urllib.error.URLError as e:
                self.log(f"💥 Error conectando a FastContext API ({req_url}): {e}")
                
                # Mock fallback de emergencia para pruebas locales si el modelo no está prendido
                # Permite desarrollo y pruebas con mock funcional
                if "mock" in self.model_name.lower() or os.environ.get("FASTCONTEXT_MOCK") == "true":
                    self.log("🔧 Ejecutando simulación Mock de FastContext para pruebas...")
                    response_body = self._generate_mock_turn(turn, messages)
                else:
                    raise HTTPException(
                        status_code=502, 
                        detail=f"No se pudo contactar con la API del modelo local FastContext-4B en {req_url}. "
                               f"Asegúrate de que está activo. Detalle: {e}"
                    )
            except Exception as e:
                self.log(f"💥 Error inesperado en llamada API: {e}")
                raise e

            self.check_cancellation()

            # Extraer mensaje y tokens
            choice = response_body["choices"][0]
            msg = choice["message"]
            content = msg.get("content") or ""
            tool_calls = msg.get("tool_calls") or []
            
            # Registrar uso de tokens estimado
            usage = response_body.get("usage", {})
            tokens_consumed += usage.get("total_tokens", 0) or int((len(content) + len(json.dumps(tool_calls))) / 4)

            # Agregar respuesta de la IA al historial
            messages.append(msg)

            # 3. Procesar llamadas de herramientas
            tool_results = []
            
            # Si no devolvió llamadas nativas pero es un modelo Qwen en crudo, 
            # intentar parsear llamadas en texto plano
            is_plain_text_tool = False
            if not tool_calls and content:
                parsed_calls = self.parse_plain_text_tool_calls(content)
                if parsed_calls:
                    self.log(f"🔍 Detectadas {len(parsed_calls)} llamadas a herramientas en texto plano.")
                    is_plain_text_tool = True
                    for p_call in parsed_calls:
                        # Convertir a formato
                        tool_calls.append({
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": p_call
                        })

            if tool_calls:
                for tc in tool_calls:
                    self.check_cancellation()
                    func = tc["function"]
                    name = func["name"]
                    call_id = tc.get("id", "call_123")
                    
                    # Parsear argumentos
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}

                    # Ejecutar herramienta
                    tool_output = self.execute_tool(name, args)
                    
                    # MUY IMPORTANTE: Empaquetar y enviar de regreso como User para continuar la conversación
                    if is_plain_text_tool:
                        messages.append({
                            "role": "user",
                            "content": f"Tool result:\n{tool_output}"
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": name,
                            "content": tool_output
                        })
            else:
                # No hay llamadas a herramientas, la IA terminó su análisis
                self.log("El sub-agente completó la exploración.")
                final_response_text = content
                break

        # Si llegó al límite sin terminar
        if not final_response_text:
            final_response_text = messages[-1].get("content") or "El sub-agente excedió el número de turnos."

        duration = time.perf_counter() - start_time
        
        # 4. Formatear y empaquetar reporte de logs
        self.log(f"Exploración terminada con éxito en {duration:.2f}s. Consumo de tokens: {tokens_consumed}")
        
        # Extraer el bloque <final_answer>
        import re
        final_answer = ""
        fa_match = re.search(r'(<final_answer>.*?</final_answer>)', final_response_text, re.DOTALL | re.IGNORECASE)
        if fa_match:
            final_answer = fa_match.group(1)
        else:
            # Si no usó etiquetas exactas, tomar todo
            final_answer = f"<final_answer>\n{final_response_text}\n</final_answer>"

        report = self._compile_markdown_report(final_answer, duration, tokens_consumed)
        
        # Guardar logs a archivo físico para auditoría
        self._write_audit_log(report, tokens_consumed)

        return {
            "status": "success",
            "task_id": self.task_id,
            "duration_seconds": round(duration, 2),
            "tokens_consumed": tokens_consumed,
            "final_answer": final_answer,
            "report": report
        }

    def _compile_markdown_report(self, final_answer: str, duration: float, tokens: int) -> str:
        """Genera un reporte de auditoría estructurado para el Agente Principal."""
        lines = [
            "# 🔍 FASTCONTEXT REPORT - EXPLORACIÓN DE CÓDIGO",
            f"**Task ID:** `{self.task_id}`",
            f"**Repositorio:** `{self.repo_path}`",
            f"**Inferencia:** `{self.model_name}`",
            f"**Métricas:** {duration:.2f}s | {tokens} tokens consumidos",
            "---",
            "## 🧭 Historial de Exploración (Auditoría)",
            "```text"
        ]
        for log_entry in self.exploration_log:
            lines.append(log_entry)
        lines.append("```")
        lines.append("---")
        lines.append("## 📍 Evidencia Encontrada")
        lines.append(final_answer)
        return "\n".join(lines)

    def _write_audit_log(self, report: str, tokens_consumed: int = 0):
        """Escribe el reporte a logs/fastcontext/audit_<task_id>.md y el accounting en server.log."""
        try:
            audit_file = os.path.join(LOG_DIR, f"audit_{self.task_id}.md")
            with open(audit_file, "w", encoding="utf-8") as f:
                f.write(report)

            # Escribir accounting básico en log central (JSONL)
            entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "task_id": self.task_id,
                "model": self.model_name,
                "repo_path": self.repo_path,
                "tokens": tokens_consumed
            }
            with open(SERVER_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"No se pudo escribir audit log: {e}")

    def _generate_mock_turn(self, turn: int, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mock fallback para testing del arnés sin cargar el LLM."""
        # Respuestas mock simulando un flujo de exploración para test
        if turn == 0:
            # Pide GLOB para buscar archivos clave
            tool_call = {
                "id": "call_mock_0",
                "type": "function",
                "function": {
                    "name": "GLOB",
                    "arguments": json.dumps({"pattern": "*.py"})
                }
            }
            return {
                "choices": [{"message": {"role": "assistant", "content": "Buscando archivos python...", "tool_calls": [tool_call]}}],
                "usage": {"total_tokens": 150}
            }
        elif turn == 1:
            # Pide GREP de algo
            tool_call = {
                "id": "call_mock_1",
                "type": "function",
                "function": {
                    "name": "GREP",
                    "arguments": json.dumps({"query": "def|class"})
                }
            }
            return {
                "choices": [{"message": {"role": "assistant", "content": "Buscando definiciones...", "tool_calls": [tool_call]}}],
                "usage": {"total_tokens": 200}
            }
        elif turn == 2:
            # Pide leer el primer archivo que encuentre (usaremos de prueba locate_smart_client.py o similar)
            tool_call = {
                "id": "call_mock_2",
                "type": "function",
                "function": {
                    "name": "READ",
                    "arguments": json.dumps({"path": "locate_smart_client.py", "start_line": 1, "end_line": 30})
                }
            }
            return {
                "choices": [{"message": {"role": "assistant", "content": "Leyendo archivo...", "tool_calls": [tool_call]}}],
                "usage": {"total_tokens": 250}
            }
        else:
            # Termina
            final_content = (
                "He completado la exploración del repositorio.\n"
                "<final_answer>\n"
                "- **locate_smart_client.py** (Líneas 1-30): Contiene el cliente MCP local y el control de arranque del servidor.\n"
                "</final_answer>"
            )
            return {
                "choices": [{"message": {"role": "assistant", "content": final_content, "tool_calls": []}}],
                "usage": {"total_tokens": 100}
            }

# =============================================================================
# Queue Manager (FIFO Serializada)
# =============================================================================
class FCQueueManager:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=10)
        self.executor = ThreadPoolExecutor(max_workers=1)  # Máxima calma térmica
        self.is_processing = False
        self.worker_task = None

    def start_worker(self):
        self.worker_task = asyncio.create_task(self._worker_loop())

    async def _worker_loop(self):
        logger.info("⚙️  Bucle de Cola FIFO de FastContext activo.")
        while True:
            try:
                task = await self.queue.get()
                self.is_processing = True
                req, task_id, fut = task
                
                # Iniciar la exploración
                try:
                    orchestrator = FastContextOrchestrator(
                        task_id=task_id,
                        repo_path=req.repo_path,
                        query=req.query,
                        architecture=req.architecture,
                        file_patterns=req.file_patterns
                    )
                    # Correr la exploración asíncrona
                    res = await orchestrator.run_exploration_loop()
                    if not fut.done():
                        fut.set_result(res)
                except Exception as e:
                    logger.error(f"💥 Error ejecutando tarea {task_id}: {e}")
                    if not fut.done():
                        fut.set_exception(e)
                finally:
                    self.queue.task_done()
                    self.is_processing = False
                    # Registrar fin de actividad para temporizador
                    global last_request_time
                    last_request_time = time.time()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en bucle FIFO: {e}")
                await asyncio.sleep(1)

    async def cancel_task(self, task_id: str):
        """Marca una tarea como cancelada."""
        if task_id in active_tasks:
            active_tasks[task_id]["cancelled"] = True
            active_tasks[task_id]["status"] = "cancelled"
            logger.info(f"🛑 Tarea {task_id} marcada para cancelación activa.")

# =============================================================================
# FastAPI Routes
# =============================================================================
app = FastAPI(title="FastContext Local Smart Server", version="1.0.0")
queue_mgr = FCQueueManager()

@app.on_event("startup")
async def startup():
    queue_mgr.start_worker()

@app.get("/health")
async def health():
    global last_request_time
    last_request_time = time.time()
    return {"status": "ok", "active_tasks": len(active_tasks)}

@app.post("/ontology")
async def get_ontology(request: OntologyRequest):
    global last_request_time
    last_request_time = time.time()
    try:
        report = OntologyBuilder.get_ontology(request.repo_path, request.architecture)
        return {"status": "success", "report": report}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/explore")
async def explore(request: ExploreRequest):
    global last_request_time
    last_request_time = time.time()
    
    # Validar que el directorio exista antes de encolar
    if not os.path.isdir(request.repo_path):
        raise HTTPException(status_code=400, detail=f"Repositorio no encontrado: '{request.repo_path}'")

    task_id = str(uuid.uuid4())[:8]
    active_tasks[task_id] = {
        "cancelled": False,
        "status": "queued",
        "active_req": None
    }

    # Futuro para esperar el resultado de la cola
    fut = asyncio.get_running_loop().create_future()
    
    try:
        # Intentar encolar (bloquea si la cola está llena, max 10)
        await asyncio.wait_for(queue_mgr.queue.put((request, task_id, fut)), timeout=5.0)
    except asyncio.TimeoutError:
        active_tasks.pop(task_id, None)
        raise HTTPException(status_code=503, detail="Cola saturada (límite FIFO de 10 posiciones alcanzado). Intenta más tarde.")

    try:
        result = await fut
        return result
    except asyncio.CancelledError:
        # Captura si el cliente aborta la conexión HTTP directamente
        logger.info(f"La conexión HTTP de {task_id} fue cerrada por el cliente. Cancelando...")
        await queue_mgr.cancel_task(task_id)
        raise HTTPException(status_code=499, detail="Client Closed Request")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    global last_request_time
    last_request_time = time.time()
    
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail=f"Tarea {task_id} no encontrada.")
    
    await queue_mgr.cancel_task(task_id)
    return {"status": "cancelled", "task_id": task_id}

if __name__ == "__main__":
    import uvicorn
    # Correr servidor localmente
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")
