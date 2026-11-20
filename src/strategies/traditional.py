import unicodedata

from src.models.response import (
    AnalyzeResponse,
    Category,
    Priority,
    AnalysisMode,
)
from src.strategies.base import AnalysisStrategy


class TraditionalStrategy(AnalysisStrategy):
    """Motor tradicional basado en reglas y palabras clave."""

    KEYWORDS = {
        Category.SECURITY: [
            "vulnerabilidad",
            "hackeo",
            "hackear",
            "ataque",
            "robo de datos",
            "filtracion",
            "acceso no autorizado",
            "actividad sospechosa",
            "malware",
            "ransomware",
            "phishing",
            "brecha de seguridad",
        ],
        Category.ACCESS: [
            "iniciar sesion",
            "no puedo entrar",
            "no puedo acceder",
            "contrasena",
            "password",
            "cuenta bloqueada",
            "recuperar cuenta",
            "problema de acceso",
            "usuario bloqueado",
            "login",
        ],
        Category.BUG: [
            "error",
            "falla",
            "fallo",
            "no funciona",
            "se cierra",
            "se congela",
            "crash",
            "bug",
            "no carga",
            "pantalla en blanco",
            "comportamiento inesperado",
        ],
        Category.FEATURE: [
            "nueva funcion",
            "nueva característica",
            "agregar",
            "anadir",
            "implementar",
            "mejora",
            "me gustaria",
            "seria util",
            "solicito una funcion",
            "opcion para",
        ],
    }

    RESPONSES = {
        Category.ACCESS:
            "Hemos identificado un problema relacionado con el acceso. "
            "Nuestro equipo puede ayudarte a recuperar el acceso a tu cuenta.",

        Category.BUG:
            "Hemos recibido tu reporte de error. "
            "Revisaremos el problema para identificar su causa y solucionarlo.",

        Category.FEATURE:
            "Hemos recibido tu solicitud de mejora. "
            "La propuesta será evaluada por nuestro equipo de desarrollo.",

        Category.SECURITY:
            "Se ha identificado un posible incidente de seguridad. "
            "El caso requiere revisión inmediata por parte del equipo especializado.",
    }

    def _normalize(self, text: str) -> str:
        """Convierte el texto a minúsculas y elimina acentos."""
        text = text.lower()
        text = unicodedata.normalize("NFD", text)
        return "".join(
            char for char in text
            if unicodedata.category(char) != "Mn"
        )

    def _classify(self, message: str) -> Category:
        """Clasifica el mensaje utilizando palabras clave."""

        normalized = self._normalize(message)

        # La seguridad tiene prioridad sobre las demás categorías.
        for keyword in self.KEYWORDS[Category.SECURITY]:
            if self._normalize(keyword) in normalized:
                return Category.SECURITY

        for category in (
            Category.ACCESS,
            Category.BUG,
            Category.FEATURE,
        ):
            for keyword in self.KEYWORDS[category]:
                if self._normalize(keyword) in normalized:
                    return category

        # Categoría predeterminada cuando no hay coincidencias.
        return Category.BUG

    def _get_priority(
        self,
        category: Category,
        message: str
    ) -> Priority:
        """Determina la prioridad según la categoría y el mensaje."""

        normalized = self._normalize(message)

        critical_keywords = [
            "robo de datos",
            "filtracion de datos",
            "datos comprometidos",
            "cuenta comprometida",
            "sistema caido",
            "perdida de datos",
            "ransomware",
        ]

        high_keywords = [
            "urgente",
            "no puedo trabajar",
            "servicio caido",
            "todos los usuarios",
            "no funciona para nadie",
        ]

        if any(word in normalized for word in critical_keywords):
            return Priority.CRITICAL

        if category == Category.SECURITY:
            return Priority.HIGH

        if any(word in normalized for word in high_keywords):
            return Priority.HIGH

        if category == Category.ACCESS:
            return Priority.HIGH

        if category == Category.BUG:
            return Priority.MEDIUM

        if category == Category.FEATURE:
            return Priority.LOW

        return Priority.MEDIUM

    def analyze(self, message: str) -> AnalyzeResponse:
        """Analiza una solicitud y genera una respuesta estructurada."""

        category = self._classify(message)
        priority = self._get_priority(category, message)

        return AnalyzeResponse(
            category=category,
            priority=priority,
            response=self.RESPONSES[category],
            requiresHumanReview=(category == Category.SECURITY),
            mode=AnalysisMode.TRADITIONAL,
        )
    