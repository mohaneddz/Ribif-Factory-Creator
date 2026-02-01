'use client';

import ErrorDisplay from '@/components/ErrorDisplay';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <ErrorDisplay
            error={error}
            onReset={reset}
            title="Page Error"
            message="An error occurred while loading this page. Please try again."
        />
    );
}
