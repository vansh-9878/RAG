from threading import Semaphore

GEMINI_CONCURRENCY_LIMIT = 25
gemini_semaphore = Semaphore(GEMINI_CONCURRENCY_LIMIT)
