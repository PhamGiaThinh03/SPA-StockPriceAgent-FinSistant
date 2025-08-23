import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../services/supabaseClient';

const AuthContext = createContext({});

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [session, setSession] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Get initial session
        const getSession = async () => {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (error) {
            console.error('Error getting session:', error);
        } else {
            setSession(session);
            setUser(session?.user ?? null);
        }
        setLoading(false);
        };

        getSession();

        // Listen for auth changes
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
        async (event, session) => {
            setSession(session);
            setUser(session?.user ?? null);
            setLoading(false);
        }
        );

        return () => subscription.unsubscribe();
    }, []);

    const signIn = async (email, password) => {
        const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
        });
        return { data, error };
    };

    const signUp = async (email, password) => {
        const { data, error } = await supabase.auth.signUp({
        email,
        password,
        });
        return { data, error };
    };

    const signOut = async () => {
        const { error } = await supabase.auth.signOut();
        return { error };
    };

    const resetPassword = async (email) => {
        const { data, error } = await supabase.auth.resetPasswordForEmail(email);
        return { data, error };
    };

    const value = {
        user,
        session,
        loading,
        signIn,
        signUp,
        signOut,
        resetPassword,
    };

    return (
        <AuthContext.Provider value={value}>
        {children}
        </AuthContext.Provider>
    );
};
