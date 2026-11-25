from api.services.ai.fallback.cooldown_tracker import CooldownTracker, cooldown_tracker
from api.services.ai.fallback.error_classifier import ErrorClassifier
from api.services.ai.interfaces.embedding import BaseEmbeddingProvider
from api.services.ai.interfaces.generation import BaseGenerationProvider
from api.services.ai.interfaces.ocr import BaseOCRProvider, OCRBlockedError
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.ai.managers.generation_manager import GenerationManager
from api.services.ai.managers.ocr_manager import VisionOCRManager, ocr_manager
from api.services.ai.schemas.ai import (
    AIErrorType,
    AIProviderError,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
    StreamToken,
)

__all__ = [
    "AIErrorType",
    "AIProviderError",
    "GenerationRequest",
    "GenerationResult",
    "StreamToken",
    "EmbeddingResult",
    "BaseGenerationProvider",
    "BaseEmbeddingProvider",
    "BaseOCRProvider",
    "OCRBlockedError",
    "ErrorClassifier",
    "CooldownTracker",
    "cooldown_tracker",
    "GenerationManager",
    "EmbeddingManager",
    "VisionOCRManager",
    "ocr_manager",
]
