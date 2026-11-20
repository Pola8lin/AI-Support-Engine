
from src.models.response import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisMode,
)
from src.strategies.traditional import TraditionalStrategy
from src.validators.input_validator import validate_input


class AnalyzerService:
    """Coordina la selección y ejecución de los motores."""

    def __init__(self, generative_strategy=None):
        self.traditional_strategy = TraditionalStrategy()
        self.generative_strategy = generative_strategy

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """Valida la solicitud y ejecuta el motor correspondiente."""

        request = validate_input(request)

        if request.mode == AnalysisMode.TRADITIONAL:
            strategy = self.traditional_strategy

        elif request.mode == AnalysisMode.GENERATIVE:
            if self.generative_strategy is None:
                raise RuntimeError(
                    "El motor generativo no está configurado."
                )

            strategy = self.generative_strategy

        else:
            raise ValueError("Modo de análisis no válido.")

        return strategy.analyze(request.message)
