import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Morocco Market Intel",
  description: "Daily bestsellers from Jumia & Marjane",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
