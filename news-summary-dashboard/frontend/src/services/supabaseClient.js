// src/supabaseClient.js
import { createClient } from "@supabase/supabase-js";

// Get keys from environment variables for better security
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY;

// Validate required environment variables
if (!supabaseUrl || !supabaseAnonKey) {
    console.error('Missing Supabase environment variables:', {
        supabaseUrl: !!supabaseUrl,
        supabaseAnonKey: !!supabaseAnonKey
    });
}

// Detect current environment URL
const getRedirectURL = () => {
    // Get current URL for redirect
    const currentUrl = window.location.origin;
    
    // Production: use current domain
    if (process.env.NODE_ENV === 'production') {
        return currentUrl + '/auth/callback';
    }
    // Development: use localhost
    return 'http://localhost:3000/auth/callback';
};

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
        redirectTo: getRedirectURL(),
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true
    }
});
