import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VN Tax Copilot | Tax Research Workspace",
  description:
    "Nền tảng nghiên cứu và hỗ trợ tra cứu pháp luật thuế Việt Nam.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="vi" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
