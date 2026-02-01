'use client';

import ErrorDisplay from '@/components/ErrorDisplay';

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    return (
        <html>
            <body>
                <ErrorDisplay
                    error={error}
                    onReset={reset}
                    title="Application Error"
                    message="A critical error has occurred. The application needs to be restarted."
                />
            </body>
        </html>
    );
}
