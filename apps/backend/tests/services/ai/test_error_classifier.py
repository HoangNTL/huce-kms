import unittest
import httpx

from api.services.ai.fallback.error_classifier import ErrorClassifier, extract_retry_delay
from api.services.ai.schemas.ai import AIErrorType, AIProviderError


class TestErrorClassifier(unittest.TestCase):
    def test_extract_retry_delay(self):
        err_msg1 = "{'error': {'message': 'Rate limit exceeded', 'details': [{\"retryDelay': '12.5s'\"}]}}"
        self.assertEqual(extract_retry_delay(err_msg1), 12.5)

        err_msg2 = "Please retry in 5s due to per-minute quota"
        self.assertEqual(extract_retry_delay(err_msg2), 5.0)

        err_msg3 = "Please try again in 3.2s."
        self.assertEqual(extract_retry_delay(err_msg3), 3.2)

        self.assertIsNone(extract_retry_delay("Generic error without delay"))

    def test_classify_daily_quota_exhausted(self):
        exc = Exception("Resource has been exhausted (e.g. check quota). Daily limit reached.")
        classified = ErrorClassifier.classify("gemini", exc)
        self.assertEqual(classified.error_type, AIErrorType.QUOTA_EXHAUSTED)
        self.assertEqual(classified.provider, "gemini")

    def test_classify_rate_limit_429(self):
        exc = Exception("429 Too Many Requests: Rate limit exceeded. Please retry in 4s.")
        classified = ErrorClassifier.classify("groq", exc)
        self.assertEqual(classified.error_type, AIErrorType.RATE_LIMIT_429)
        self.assertEqual(classified.retry_after, 4.0)

    def test_gemini_resource_exhausted_with_retry_delay_is_rate_limit(self):
        # Gemini sends RESOURCE_EXHAUSTED with retryDelay for short RPM rate limits
        exc = Exception("RESOURCE_EXHAUSTED: Resource has been exhausted (e.g. check quota). Please retry in 3s.")
        classified = ErrorClassifier.classify("gemini", exc)
        self.assertEqual(classified.error_type, AIErrorType.RATE_LIMIT_429)
        self.assertEqual(classified.retry_after, 3.0)

    def test_classify_auth_error_401(self):
        exc = Exception("401 Unauthorized: Invalid API key provided.")
        classified = ErrorClassifier.classify("openrouter", exc)
        self.assertEqual(classified.error_type, AIErrorType.AUTH_ERROR_401)

    def test_classify_server_error_5xx(self):
        exc = Exception("503 Service Unavailable: High server load.")
        classified = ErrorClassifier.classify("gemini", exc)
        self.assertEqual(classified.error_type, AIErrorType.SERVER_ERROR_5XX)

    def test_classify_timeout(self):
        exc = TimeoutError("Request timed out after 30 seconds")
        classified = ErrorClassifier.classify("jina", exc)
        self.assertEqual(classified.error_type, AIErrorType.TIMEOUT)

    def test_classify_invalid_request(self):
        exc = Exception("400 Bad Request: Prompt violated safety policies.")
        classified = ErrorClassifier.classify("gemini", exc)
        self.assertEqual(classified.error_type, AIErrorType.INVALID_REQUEST)


if __name__ == "__main__":
    unittest.main()
