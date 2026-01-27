import type { Metadata } from "next";
import { cookies } from "next/headers";
import "./globals.css";
import ThemeProvider from "@/components/ThemeProvider";
import ErrorBoundary from "@/components/ErrorBoundary";
import { THEME_COOKIE } from "@/utils/theme";

export const metadata: Metadata = {
    title: "ALLO MAISON - Digital Twin",
    description: "Industry 5.0 Dashboard",
};

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const cookieStore = await cookies();
    const theme = cookieStore.get(THEME_COOKIE)?.value || "light";

    return (
        <html lang="en" className={theme}>
            <body className={`min-h-screen `}>
                <ErrorBoundary>
                    <ThemeProvider>
                        <main className="">{children}</main>
                    </ThemeProvider>
                </ErrorBoundary>
            </body>
        </html>
    );
}
