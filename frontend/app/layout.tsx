import type { Metadata } from "next";
import "./globals.css";

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
            <body className=" min-h-screen ">
                <main className="">{children}</main>
            </body>
        </html>
    );
}