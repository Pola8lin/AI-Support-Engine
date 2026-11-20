
from src.models.response import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisMode,
)
from src.strategies.generative import GenerativeStrategy
from src.strategies.traditional import TraditionalStrategy
from src.validators.input_validator import validate_input
from src.validators.response_validator import validate_and_enforce_response


class AnalyzerService:
    """Coordina la selección y ejecución de los motores."""

    def __init__(self, generative_strategy=None):
        self.traditional_strategy = TraditionalStrategy()
        self.generative_strategy = (
            generative_strategy
            if generative_strategy is not None
            else GenerativeStrategy()
        )

    def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """Valida la solicitud y ejecuta el motor correspondiente."""

        request = validate_input(request)

        if request.mode == AnalysisMode.TRADITIONAL:
            return self.traditional_strategy.analyze(request.message)

        elif request.mode == AnalysisMode.GENERATIVE:
            if self.generative_strategy is None:
                raise RuntimeError(
                    "El motor generativo no está configurado."
                )

            result = self.generative_strategy.analyze(request.message)
            return validate_and_enforce_response(
                raw_response=result,
                original_message=request.message,
                mode=AnalysisMode.GENERATIVE,
            )

        else:
            raise ValueError("Modo de análisis no válido.")
