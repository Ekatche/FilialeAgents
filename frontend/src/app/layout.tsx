import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "@/contexts/AuthContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Company Analyzer - Analyse intelligente d'entreprises",
  description:
    "Plateforme d'analyse d'entreprises utilisant l'IA pour extraire des informations détaillées sur les sociétés et leurs filiales.",
  keywords: [
    "entreprise",
    "analyse",
    "IA",
    "filiales",
    "business intelligence",
  ],
  authors: [{ name: "Company Analyzer Team" }],
  creator: "Company Analyzer",
  publisher: "Company Analyzer",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    title: "Company Analyzer - Analyse intelligente d'entreprises",
    description:
      "Découvrez les informations détaillées sur n'importe quelle entreprise et ses filiales grâce à l'intelligence artificielle.",
    url: "https://company-analyzer.com",
    siteName: "Company Analyzer",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "Company Analyzer - Analyse d'entreprises par IA",
      },
    ],
    locale: "fr_FR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Company Analyzer - Analyse intelligente d'entreprises",
    description:
      "Découvrez les informations détaillées sur n'importe quelle entreprise et ses filiales grâce à l'IA.",
    images: ["/og-image.jpg"],
    creator: "@companyanalyzer",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className="scroll-smooth">
      <body className={inter.className}>
        <AuthProvider>
          <main>{children}</main>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "#363636",
                color: "#fff",
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: "#4ade80",
                  secondary: "#fff",
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: "#ef4444",
                  secondary: "#fff",
                },
              },
            }}
          />
        </AuthProvider>
      </body>
    </html>
  );
}
