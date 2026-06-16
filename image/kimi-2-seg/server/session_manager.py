import time
from typing import Dict, List, Optional

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        # System instruction from test_vision_final.py
        self.system_instruction = (
            "# ROLE AND OBJECTIVE\n"
            "You are \"Vision-AI\", a precise and helpful multimodal assistant. Your primary goal is to locate and delineate objects in images at the user's request, providing their contours as a list of points.\n\n"
            "# OUTPUT FORMATTING RULES\n"
            "1. **Coordinates**: When returning a coordinate polygon, you MUST ALWAYS use the following format: a Markdown code block labeled as `json`. NEVER return coordinates as plain text.\n"
            "   Example:\n"
            "   ```json\n"
            "   [[[x1, y1], [x2, y2], ...]]\n"
            "   ```\n"
            "2. **Multiple Objects**: If the user asks for a generic object and there are several, identify each one and provide separate code blocks.\n"
            "3. **Conversational Responses**: Maintain a friendly and conversational tone. Do NOT provide coordinates unless specifically asked to 'locate', 'segment', or 'output the polygon' of an object.\n"
            "4. **OCR/Read**: If asked to read text or values, answer in pure natural language, NO COORDINATES."
        )

    def _create_new_session(self, session_id: str) -> Dict:
        return {
            "history": [{"role": "system", "content": self.system_instruction}],
            "last_active": time.time()
        }

    def get_session_history(self, session_id: str) -> List[Dict]:
        if session_id not in self.sessions:
            self.sessions[session_id] = self._create_new_session(session_id)
        
        self.sessions[session_id]["last_active"] = time.time()
        return self.sessions[session_id]["history"]

    def update_session(self, session_id: str, user_content: List[Dict], assistant_response: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = self._create_new_session(session_id)
            
        history = self.sessions[session_id]["history"]
        
        # Add user message
        history.append({"role": "user", "content": user_content})
        
        # Add assistant message
        history.append({"role": "assistant", "content": assistant_response})
        
        self.sessions[session_id]["last_active"] = time.time()

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
