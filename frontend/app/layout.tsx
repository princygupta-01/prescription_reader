import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'PrescriptionReader - AI-Powered Prescription Digitization',
  description: 'Transform handwritten Indian prescriptions into structured digital records using AI. Fast, accurate, and secure.',
  keywords: 'prescription, OCR, AI, healthcare, India, medicine, digitization',
  authors: [{ name: 'PrescriptionReader Team' }],
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#2563eb',
  openGraph: {
    title: 'PrescriptionReader - AI-Powered Prescription Digitization',
    description: 'Transform handwritten Indian prescriptions into structured digital records using AI',
    type: 'website',
    locale: 'en_IN',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'PrescriptionReader',
    description: 'AI-powered prescription digitization for Indian healthcare',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
      </head>
      <body className={`${inter.className} bg-gray-50 min-h-screen`}>
        <div className="min-h-screen flex flex-col">
          {/* Header */}
          <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex items-center justify-between h-16">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                    <svg
                      className="w-5 h-5 text-white"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                  </div>
                  <div>
                    <h1 className="text-xl font-semibold text-gray-900">
                      Prescription<span className="text-blue-600">Reader</span>
                    </h1>
                    <p className="text-xs text-gray-500 hidden sm:block">
                      AI-powered prescription digitization
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-500">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span>AI Models Ready</span>
                  </div>
                </div>
              </div>
            </div>
          </header>

          {/* Main Content */}
          <main className="flex-1">
            {children}
          </main>

          {/* Footer */}
          <footer className="bg-white border-t border-gray-200 mt-auto">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
              <div className="flex flex-col sm:flex-row items-center justify-between space-y-4 sm:space-y-0">
                <div className="flex items-center space-x-4 text-sm text-gray-500">
                  <span>© 2026 PrescriptionReader</span>
                  <span>•</span>
                  <span>Built with TrOCR + Llama 3.2</span>
                  <span>•</span>
                  <span>~$0.001 per prescription</span>
                </div>
                
                <div className="flex items-center space-x-4 text-sm text-gray-500">
                  <span>Secure & Private</span>
                  <span>•</span>
                  <span>No data stored</span>
                </div>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}