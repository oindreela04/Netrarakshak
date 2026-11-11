import type { Metadata } from "next";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "NetraRakshak — AI-assisted retinal screening", template: "%s · NetraRakshak" },
  description: "See beyond the retina. Detect earlier. Protect vision. Clinician-supervised retinal screening for hospitals and eye clinics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-IN">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=Saira:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Public+Sans:wght@400;500;600;700&display=swap"
        />
      </head>
      <body>
        {children}
        <Toaster position="top-right" richColors closeButton />
      </body>
    </html>
  );
}
