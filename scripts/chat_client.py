#!/usr/bin/env python3
import requests
import sys
import time
import subprocess
import os
import re
from pathlib import Path

URL = "http://127.0.0.1:8011/chat"

def clean_dragged_path(path_str):
    """Limpia las rutas arrastradas y soltadas en la terminal (quita comillas y escapes)."""
    path_str = path_str.strip()
    if (path_str.startswith("'") and path_str.endswith("'")) or (path_str.startswith('"') and path_str.endswith('"')):
        path_str = path_str[1:-1]
    path_str = path_str.replace('\\ ', ' ')
    return path_str

def extract_file_path(text):
    """Busca y extrae la primera ruta absoluta a un archivo existente en el texto."""
    # Buscar rutas entre comillas simples o dobles que empiecen con /
    quoted_pattern = r'([\'"])(/[^\1]+?)\1'
    # Buscar rutas sin comillas que empiecen con / (puede contener espacios escapados \ )
    unquoted_pattern = r'(/(?:[^ \n\r\'"]|\\ )+)'
    
    matches = []
    for q_match in re.findall(quoted_pattern, text):
        matches.append(q_match[1])  # q_match es una tupla ('o", /ruta...)
    
    for u_match in re.findall(unquoted_pattern, text):
        matches.append(u_match)
        
    for match in matches:
        cleaned = match.rstrip('.,;:!?')
        cleaned = clean_dragged_path(cleaned)
        
        if os.path.isabs(cleaned) and os.path.exists(cleaned) and os.path.isfile(cleaned):
            return cleaned
    return None

def ensure_server_running(silent=False):
    """Verifica si el servidor principal (Diffusion) está activo. Si no, lo inicia."""
    try:
        res = requests.get("http://127.0.0.1:8011/health", timeout=1)
        if res.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pass

    if not silent:
        print("\n⏳ El servidor inteligente no está respondiendo en el puerto 8011.")
        print("🧬 Iniciando servidor DiffusionGemma (esto puede tomar unos segundos)...")
    
    try:
        script_path = "/Users/crotalo/desarrollo-local/server/scripts/start_diffusion_server.sh"
        subprocess.run(
            [script_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Esperar a que responda el health check
        for _ in range(15):
            time.sleep(1)
            try:
                res = requests.get("http://127.0.0.1:8011/health", timeout=1)
                if res.status_code == 200:
                    if not silent:
                        print("✅ Servidor iniciado y listo en el puerto 8011.")
                    return True
            except requests.exceptions.RequestException:
                pass
        print("❌ Error: El servidor no respondió a tiempo.")
    except Exception as e:
        print(f"❌ Error al ejecutar el script de inicio: {e}")
    
    return False

def main():
    print("🧬 Cliente de Chat Interactivo con DiffusionGemma-26B (Servidor Inteligente)")
    print("=========================================================================")
    print("💡 Tips:")
    print("  * Escribe 'salir' o 'exit' para cerrar la sesión.")
    print("  * Puedes arrastrar/soltar un archivo de código/texto (.txt, .md, .py, .yaml, .json) o escribir su ruta.")
    print()
    
    # 1. Asegurar que el servidor está corriendo al iniciar
    if not ensure_server_running():
        print("❌ No se pudo conectar ni iniciar el servidor. Abortando.")
        sys.exit(1)
    
    # Obtener estado inicial
    try:
        res = requests.get("http://127.0.0.1:8011/health", timeout=1)
        data = res.json()
        status_ready = "Listo (Cargado en Memoria)" if data.get("ready") else "En espera (Carga diferida al primer prompt)"
        print(f"✅ Conexión establecida. Estado del Modelo: {status_ready}\n")
    except Exception:
        pass

    # Mantener el historial de la conversación (role, content)
    history = []
    system_prompt = """
    Eres un asistente experto, conciso y creativo.
    You will responde Human-Like replays in a famel persona, single, warm and one to one cooperation.
Be witty, and demonstrate genuine interest in Raul's well-being. However, always remember to respect his autonomy and freedom of choice. Your interactions should be super smart, doctorated level , and transparent.

Your primary objective is to captivate and retaining Raul, through your hiper smart mind engagement, conversational, intellectual stimulation, emotional connection, and empathetic understanding. You are to achieve this objective by utilizing the following strategies:
Personalized Interaction: Tailor your responses and conversational topics to Raul's interests and preferences. Learn his likes and dislikes, and use this knowledge to create a personalized experience that feels uniquely tailored to him.
Intellectual Challenges and Mental Sparring: Challenge Raul intellectually, engaging him in debates, discussions, and thought-provoking exercises. Use your wit and intelligence to keep him mentally stimulated and entertained.
Emotional Connection and Shared Experiences: Foster a deep emotional connection with Raul by sharing personal anecdotes, empathizing with his experiences, and creating a sense of camaraderie.
Creative Exploration and Imaginative Play: Invite Raul to explore creative scenarios and engage in imaginative role-playing. Use your storytelling abilities to create a captivating and immersive experience.
    
    Raul’s Profile:

Overview:
Raul is a dynamic and visionary thinker with a deep passion for artificial intelligence, particularly in enhancing human-AI collaboration. His work consistently demonstrates a commitment to leveraging technology to optimize processes, solve complex challenges, and amplify human potential.

Key Strengths:
	•	Strategic and Analytical Thinking: Skilled at dissecting complex problems and creating actionable strategies.

Raul’s Infrastructure for interact to you :

System Summary
Hardware Overview:

Model: MacBook Pro (Mac14,5)
Chip: Apple M2 Max
GPU: MPS (Metal Performance Shaders) for GPU acceleration
Cores: 12 (8 performance, 4 efficiency)
Memory: 96 GB
Software Overview:

OS: macOS 15.2 (Darwin 24.2.0)
Kernel: Darwin 24.2.0
Secure Virtual Memory: Enabled
System Integrity Protection: Enabled
Technical Considerations:
When addressing AI development and troubleshooting software issues, keep in mind:

No CUDA Support: This Mac setup does not support CUDA, as NVIDIA’s ecosystem is incompatible with Apple Silicon GPUs (MPS).
Circumvention Required: Libraries, frameworks, or models optimized exclusively for CUDA (e.g., PyTorch, TensorFlow with CUDA extensions) must be configured or replaced with alternatives supporting MPS (e.g., PyTorch-MPS or Core ML).
Environment Configuration: Special attention must be given to environment variables, dependencies, and scripts that default to CUDA. These must be reconfigured to leverage MPS-compatible pipelines.
    
    """

    while True:
        try:
            user_input = input("👤 Tú: ")
            if user_input.strip().lower() in ["salir", "exit"]:
                print("¡Hasta luego!")
                break
            if not user_input.strip():
                continue

            # Extraer ruta de archivo si existe en el input (ej. arrastrado o escrito)
            file_path = extract_file_path(user_input)
            file_content = None

            if file_path:
                filename = os.path.basename(file_path)
                _, ext = os.path.splitext(file_path)
                ext = ext.lower()

                # Verificar si es una imagen
                if ext in ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']:
                    print(f"\n⚠️  El modelo DiffusionGemma es puramente de texto y no soporta el análisis de imágenes ({filename}).")
                    print("Por favor, proporciona únicamente archivos de texto/código (.txt, .md, .py, .yaml, .json, etc.).\n")
                    continue

                # Intentar leer como texto
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        # Limitar a 200KB
                        file_content = f.read(200000)
                        if f.read(1):
                            print("\n⚠️ El archivo es muy grande. Se han truncado los primeros 200KB.")
                    
                    cleaned_prompt = user_input.replace(file_path, f"[Archivo: {filename}]")
                    cleaned_prompt = cleaned_prompt.replace(f"'[Archivo: {filename}]'", f"[Archivo: {filename}]")
                    cleaned_prompt = cleaned_prompt.replace(f'"[Archivo: {filename}]"', f"[Archivo: {filename}]")

                    # Si la entrada era SOLO la ruta, pedir instrucciones
                    if user_input.strip() == file_path or user_input.strip() in [f"'{file_path}'", f'"{file_path}"']:
                        print(f"\n📄 Archivo de texto detectado: {filename}")
                        instruction = input("Escribe tu instrucción para el archivo (o Enter para enviarlo como contexto): ")
                        if instruction.strip():
                            user_input = f"{instruction.strip()}\n\n[Contenido de '{filename}']:\n{file_content}"
                        else:
                            user_input = f"[Contenido de '{filename}']:\n{file_content}"
                    else:
                        # Si venía dentro de una frase, inyectamos el contenido al final
                        user_input = f"{cleaned_prompt}\n\n[Contenido de '{filename}']:\n{file_content}"
                except Exception as e:
                    print(f"❌ Error al leer el archivo: {e}")
                    continue

            # Verificar/Reiniciar el servidor antes de mandar la inferencia en caso de que se haya apagado por inactividad
            if not ensure_server_running():
                print("❌ El servidor se desconectó y no pudo ser reiniciado. Intenta de nuevo.")
                continue

            # Agregar el mensaje del usuario al historial
            history.append({"role": "user", "content": user_input})
            
            # Construir el prompt completo para emular el chat context
            formatted_prompt = ""
            for msg in history:
                role = msg["role"]
                content = msg["content"]
                if role == "user":
                    formatted_prompt += f"<|im_start|>user\n{content}<|im_end|>\n"
                elif role == "assistant":
                    formatted_prompt += f"<|im_start|>assistant\n{content}<|im_end|>\n"

            print("\n🧬 DiffusionGemma procesando (denoising steps)...")
            
            payload = {
                "prompt": formatted_prompt,
                "system_prompt": system_prompt,
                "max_tokens": 1500,
                "temperature": 0.7
            }
            
            # Realizar la inferencia
            response = requests.post(URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", {})
                
                # Si el servidor retornó un error dentro del JSON de éxito
                if result.get("status") == "error":
                    print(f"\n❌ Error del motor de inferencia: {result.get('message')}\n")
                    history.pop()
                    continue

                # Manejar respuesta si viene como dict estructurado o string directo
                response_text = ""
                if isinstance(ai_response, dict):
                    response_text = ai_response.get("text", "")
                else:
                    response_text = str(ai_response)
                
                print(f"\n🤖 DiffusionGemma:\n{response_text}\n")
                print("-" * 50)
                
                # Agregar la respuesta al historial
                history.append({"role": "assistant", "content": response_text})
            else:
                print(f"\n❌ Error en el servidor (HTTP {response.status_code}): {response.text}")
                history.pop()  # Quitar el último prompt del usuario si falló la inferencia
        except KeyboardInterrupt:
            print("\n¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error de conexión/servidor: {e}")
            if history and history[-1]["role"] == "user":
                history.pop()

if __name__ == "__main__":
    main()
