import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '@/lib/auth'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { AppShell } from '@/components/AppShell'
import { LoginPage } from '@/pages/LoginPage'
import { PortfolioPage } from '@/pages/PortfolioPage'
import { ProjectDetailPage } from '@/pages/ProjectDetailPage'
import { UploadPage } from '@/pages/UploadPage'
import { IngredientsPage } from '@/pages/IngredientsPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<PortfolioPage />} />
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/ingredients" element={<IngredientsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
