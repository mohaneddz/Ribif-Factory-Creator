'use client';

import { useState, useCallback } from 'react';
import ErrorDisplay from '@/components/ErrorDisplay';

interface UseErrorHandlerReturn {
    error: Error | null;
    setError: (error: Error | null) => void;
    clearError: () => void;
    handleError: (error: unknown) => void;
    ErrorComponent: React.FC | null;
}

export function useErrorHandler(): UseErrorHandlerReturn {
    const [error, setError] = useState<Error | null>(null);

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    const handleError = useCallback((error: unknown) => {
        if (error instanceof Error) {
            setError(error);
        } else if (typeof error === 'string') {
            setError(new Error(error));
        } else {
            setError(new Error('An unknown error occurred'));
        }
    }, []);

    const ErrorComponent = error
        ? () => (
              <ErrorDisplay
                  error={error}
                  onReset={clearError}
                  title="Operation Failed"
                  message="An error occurred during the operation. Please try again."
              />
          )
        : null;

    return {
        error,
        setError,
        clearError,
        handleError,
        ErrorComponent,
    };
}

interface AsyncOperationOptions<T> {
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
    errorMessage?: string;
}

export function useAsyncError() {
    const { handleError, error, clearError } = useErrorHandler();
    const [isLoading, setIsLoading] = useState(false);

    const executeAsync = useCallback(
        async <T,>(
            asyncFn: () => Promise<T>,
            options?: AsyncOperationOptions<T>
        ): Promise<T | null> => {
            setIsLoading(true);
            clearError();

            try {
                const result = await asyncFn();
                options?.onSuccess?.(result);
                return result;
            } catch (err) {
                const error =
                    err instanceof Error
                        ? err
                        : new Error(options?.errorMessage || 'Operation failed');
                handleError(error);
                options?.onError?.(error);
                return null;
            } finally {
                setIsLoading(false);
            }
        },
        [handleError, clearError]
    );

    return {
        executeAsync,
        error,
        clearError,
        isLoading,
    };
}
