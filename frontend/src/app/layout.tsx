import type { Metadata } from "next";
import "./globals.css";
import ThemeProvider from "@/components/ThemeProvider";

export const metadata: Metadata = {
    title: "ALLO MAISON - Digital Twin",
    description: "Industry 5.0 Dashboard",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={`min-h-screen `}>
                <ThemeProvider>
                    <main className="">{children}</main>
                </ThemeProvider>
            </body>
        </html>
    );
}
