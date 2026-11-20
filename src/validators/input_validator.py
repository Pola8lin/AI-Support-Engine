from src.models.response import AnalyzeRequest, AnalysisMode


MAX_MESSAGE_LENGTH = 5000


def validate_input(request: AnalyzeRequest) -> AnalyzeRequest:
    """
    Valida el mensaje y el modo de análisis recibido.
    """

    message = request.message

    # Evitar mensajes vacíos o con espacios.
    if not message or not message.strip():
        raise ValueError("El mensaje no puede estar vacío.")

    # Evitar mensajes demasiado largos.
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"El mensaje no puede superar "
            f"{MAX_MESSAGE_LENGTH} caracteres."
        )

    # Comprobar que el modo sea válido.
    if request.mode not in (
        AnalysisMode.TRADITIONAL,
        AnalysisMode.GENERATIVE,
    ):
        raise ValueError("El modo de análisis no es válido.")

    return request.model_copy(
        update={"message": message.strip()}
    )
