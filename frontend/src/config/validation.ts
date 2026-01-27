export const VALIDATION_CONFIG = {
  MIN_PDF_CHARACTERS: 1000,
  ALLOWED_FILE_TYPES: ['application/pdf'] as string[],
  MAX_FILE_SIZE_MB: 50,
  LLM_VALIDATION_ENDPOINT: '/api/validate-pdf'
} as const;
