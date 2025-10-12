import type { ReactNode } from "react";
import { MyRuntimeProvider } from "@/app/MyRuntimeProvider";
import "./globals.css";

export const metadata = {
  title: "Job Guardian Assistant",
  description: "🦉 A local assistant powered by @assistant-ui/react",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="zh-Hant">
      <body>
        <MyRuntimeProvider>{children}</MyRuntimeProvider>
      </body>
    </html>
  );
}
