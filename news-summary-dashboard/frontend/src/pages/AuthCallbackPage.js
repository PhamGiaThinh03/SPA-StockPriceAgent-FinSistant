import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Spinner, Center, Text } from '@chakra-ui/react';
import { supabase } from '../services/supabaseClient';

const AuthCallbackPage = () => {
    const navigate = useNavigate();

    useEffect(() => {
        const handleAuthCallback = async () => {
        try {
            // Get the current session
            const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
            
            if (sessionError) {
            console.error('Session error:', sessionError);
            navigate('/auth');
            return;
            }

            if (sessionData.session?.user) {
            // Successfully authenticated, redirect to dashboard
            navigate('/');
            } else {
            // No session, redirect to auth
            navigate('/auth');
            }
        } catch (error) {
            console.error('Unexpected error during auth callback:', error);
            navigate('/auth');
        }
        };

        // Add a small delay to ensure URL parameters are processed
        setTimeout(handleAuthCallback, 100);
    }, [navigate]);

    return (
        <Center h="100vh">
        <Box textAlign="center">
            <Spinner size="xl" mb={4} />
            <Text>Đang xử lý đăng nhập...</Text>
        </Box>
        </Center>
    );
};

export default AuthCallbackPage;
