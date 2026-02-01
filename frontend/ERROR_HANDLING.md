# Error Handling Guide

## Overview

The application now includes comprehensive error handling with user-friendly error displays, error details toggle, and retry functionality.

## Components

### 1. ErrorBoundary
A React Error Boundary that catches JavaScript errors anywhere in the component tree.

**Location:** `src/components/ErrorBoundary.tsx`

**Usage:**
```tsx
import ErrorBoundary from '@/components/ErrorBoundary';

<ErrorBoundary>
  <YourComponent />
</ErrorBoundary>
```

### 2. ErrorDisplay
A reusable error display component with:
- User-friendly error message
- Collapsible error details
- Retry button (refreshes or resets)
- Go Home button
- Dark mode support

**Location:** `src/components/ErrorDisplay.tsx`

**Usage:**
```tsx
import ErrorDisplay from '@/components/ErrorDisplay';

<ErrorDisplay
  error={error}
  onReset={() => console.log('Reset')}
  title="Custom Title"
  message="Custom message"
/>
```

### 3. Error Pages

#### App-level Error (`error.tsx`)
Catches errors in page components and layouts.

**Location:** `src/app/error.tsx`

#### Global Error (`global-error.tsx`)
Catches critical errors including those in the root layout.

**Location:** `src/app/global-error.tsx`

## Hooks

### useErrorHandler
Handle errors in functional components with state management.

```tsx
import { useErrorHandler } from '@/hooks/useErrorHandler';

function MyComponent() {
  const { error, handleError, clearError, ErrorComponent } = useErrorHandler();

  const doSomething = async () => {
    try {
      // Your code
    } catch (err) {
      handleError(err);
    }
  };

  if (ErrorComponent) {
    return <ErrorComponent />;
  }

  return <div>Your content</div>;
}
```

### useAsyncError
Handle async operations with automatic error handling and loading states.

```tsx
import { useAsyncError } from '@/hooks/useErrorHandler';

function MyComponent() {
  const { executeAsync, error, isLoading, clearError } = useAsyncError();

  const fetchData = async () => {
    const data = await executeAsync(
      async () => {
        const response = await fetch('/api/data');
        if (!response.ok) throw new Error('Failed to fetch');
        return response.json();
      },
      {
        onSuccess: (data) => console.log('Success:', data),
        onError: (error) => console.error('Error:', error),
        errorMessage: 'Failed to load data',
      }
    );
  };

  if (error) {
    return <ErrorDisplay error={error} onReset={clearError} />;
  }

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return <button onClick={fetchData}>Fetch Data</button>;
}
```

## Features

### Error Details Toggle
Users can expand/collapse technical error details including:
- Error message
- Stack trace
- Component stack (when available)

### Retry Functionality
- **Retry Button**: Reloads the page or resets error state
- **Go Home Button**: Navigates to the home page

### Dark Mode Support
All error components automatically adapt to dark/light theme.

## Integration

Error handling is automatically integrated at the root level via:
- `ErrorBoundary` wrapping in `layout.tsx`
- Next.js error pages (`error.tsx`, `global-error.tsx`)

## Best Practices

1. **Wrap risky components**: Use `ErrorBoundary` around components that might fail
2. **Use hooks for API calls**: Use `useAsyncError` for cleaner async error handling
3. **Provide context**: Pass meaningful error messages to `ErrorDisplay`
4. **Log errors**: Always log errors for debugging (already done by ErrorBoundary)
5. **Test error states**: Verify error handling works by simulating failures

## Example: API Call with Error Handling

```tsx
'use client';

import { useAsyncError } from '@/hooks/useErrorHandler';
import ErrorDisplay from '@/components/ErrorDisplay';

export default function DataFetcher() {
  const { executeAsync, error, isLoading, clearError } = useAsyncError();
  const [data, setData] = useState(null);

  const loadData = async () => {
    const result = await executeAsync(
      async () => {
        const res = await fetch('/api/endpoint');
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
      },
      {
        onSuccess: setData,
        errorMessage: 'Failed to load data from the server',
      }
    );
  };

  if (error) {
    return <ErrorDisplay error={error} onReset={clearError} />;
  }

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <button onClick={loadData}>Load Data</button>
      {data && <pre>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}
```

## Styling

Error components use Tailwind CSS with:
- Responsive design
- Gradient backgrounds
- Smooth transitions
- Proper contrast for accessibility
- Dark mode support via `dark:` utilities

## Troubleshooting

**Error boundary not catching errors:**
- Error boundaries only catch errors in child components during rendering
- They don't catch errors in event handlers (use try-catch or hooks)
- They don't catch async errors (use try-catch or useAsyncError)

**Error display not showing:**
- Check if error state is properly set
- Verify ErrorDisplay component is imported correctly
- Check console for any rendering errors
