import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { MyRuntimeProvider } from "./MyRuntimeProvider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Job Guardian",
  description: "Your AI-powered job application assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <MyRuntimeProvider>{children}</MyRuntimeProvider>
      </body>
    </html>
  );
}
