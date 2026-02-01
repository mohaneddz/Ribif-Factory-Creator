export default function Loading() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-900 dark:to-gray-800">
            <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-600 dark:border-blue-400 mb-4"></div>
                <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">
                    Loading...
                </p>
            </div>
        </div>
    );
}
