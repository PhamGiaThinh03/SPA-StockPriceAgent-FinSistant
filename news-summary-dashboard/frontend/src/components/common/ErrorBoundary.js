import React from 'react';
import { Box, Heading, Text, Button, VStack } from '@chakra-ui/react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return (
        <Box 
          display="flex" 
          alignItems="center" 
          justifyContent="center" 
          minHeight="100vh"
          p={8}
        >
          <VStack spacing={4} textAlign="center">
            <Heading size="lg" color="red.500">
              Oops! Đã xảy ra lỗi
            </Heading>
            <Text color="gray.600">
              Ứng dụng đã gặp phải một lỗi không mong muốn. Vui lòng thử lại.
            </Text>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <Box 
                bg="red.50" 
                border="1px" 
                borderColor="red.200" 
                borderRadius="md" 
                p={4} 
                maxW="600px"
                overflow="auto"
              >
                <Text fontWeight="bold" color="red.700" mb={2}>
                  Error Details:
                </Text>
                <Text fontSize="sm" color="red.600" fontFamily="mono">
                  {this.state.error.toString()}
                </Text>
                {this.state.errorInfo && (
                  <Text fontSize="sm" color="red.600" fontFamily="mono" mt={2}>
                    {this.state.errorInfo.componentStack}
                  </Text>
                )}
              </Box>
            )}
            <Button 
              colorScheme="blue" 
              onClick={() => {
                this.setState({ hasError: false, error: null, errorInfo: null });
                window.location.reload();
              }}
            >
              Tải lại trang
            </Button>
          </VStack>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
