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
      {/* Based on the user, decide which interface to display */}
      {!user ? (
        // If not logged in, only show the Auth page
        <Routes>
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          {/* All other routes will redirect to the Auth page */}
          <Route path="*" element={<Navigate to="/auth" />} />
        </Routes>
      ) : (
        // If logged in, show the main interface
        <Flex minH="100vh" bg="gray.50">
          <Sidebar />
          <Box flex="1" p={8}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/analytics" element={<StockAnalysisPage />} />
              <Route path="/saved-articles" element={<SavedArticlesPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              {/* Any unmatched routes will redirect to the home page */}
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
