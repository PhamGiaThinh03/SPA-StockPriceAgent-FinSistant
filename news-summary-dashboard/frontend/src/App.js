import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Flex, Box, Spinner, Center } from '@chakra-ui/react';

import { AuthProvider, useAuth } from './contexts/AuthContext';
import { BookmarkProvider } from './contexts/BookmarkContext';
import Sidebar from './components/layout/Sidebar';
import DashboardPage from './pages/DashboardPage';
import AuthPage from './pages/AuthPage';
import AuthCallbackPage from './pages/AuthCallbackPage';
import SettingsPage from "./pages/SettingsPage";
import SavedArticlesPage from "./pages/SavedArticlesPage";
import StockAnalysisPage from "./pages/StockAnalysisPage";

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  return (
    <Router>
      {/* Dựa vào user để quyết định hiển thị giao diện nào */}
      {!user ? (
        // Nếu chưa đăng nhập, chỉ hiển thị trang Auth
        <Routes>
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          {/* Mọi đường dẫn khác đều chuyển về trang auth */}
          <Route path="*" element={<Navigate to="/auth" />} />
        </Routes>
      ) : (
        // Nếu đã đăng nhập, hiển thị giao diện chính
        <Flex minH="100vh" bg="gray.50">
          <Sidebar />
          <Box flex="1" p={8}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/analytics" element={<StockAnalysisPage />} />
              <Route path="/saved-articles" element={<SavedArticlesPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              {/* Mọi đường dẫn không khớp sẽ chuyển về trang chủ */}
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </Box>
        </Flex>
      )}
    </Router>
  );
}

function App() {
  return (
    <AuthProvider>
      <BookmarkProvider>
        <AppContent />
      </BookmarkProvider>
    </AuthProvider>
  );
}

export default App;
