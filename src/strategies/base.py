
from abc import ABC, abstractmethod
from src.models.response import AnalyzeResponse


class AnalysisStrategy(ABC):

    @abstractmethod
    def analyze(self, message: str) -> AnalyzeResponse:
        """
        Analiza un mensaje y devuelve una respuesta
        con el contrato establecido.
        """
        pass