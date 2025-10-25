import './globals.css'
import Providers from '@/lib/providers'
import { UserProvider } from '@/lib/contexts/UserContext';

export const metadata = {
  title: 'SOP RAG System',
  description: 'Standard Operating Procedures RAG Application',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <UserProvider>
            {children}
          </UserProvider>
        </Providers>
      </body>
    </html>
  )
}
