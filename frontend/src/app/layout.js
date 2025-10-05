import './globals.css'
import Providers from '@/lib/providers'

export const metadata = {
  title: 'SOP RAG System',
  description: 'Standard Operating Procedures RAG Application',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
