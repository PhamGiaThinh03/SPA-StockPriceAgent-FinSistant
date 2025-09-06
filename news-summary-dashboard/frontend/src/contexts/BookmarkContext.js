import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { useAuth } from './AuthContext';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://hviet-be-for-spa.hf.space';

// Bookmark Context
const BookmarkContext = createContext();

// Action types
const BOOKMARK_ACTIONS = {
    SET_LOADING: 'SET_LOADING',
    SET_BOOKMARKS: 'SET_BOOKMARKS',
    SET_ERROR: 'SET_ERROR',
    ADD_BOOKMARK_OPTIMISTIC: 'ADD_BOOKMARK_OPTIMISTIC',
    REMOVE_BOOKMARK_OPTIMISTIC: 'REMOVE_BOOKMARK_OPTIMISTIC',
    UPDATE_BOOKMARK_STATUS: 'UPDATE_BOOKMARK_STATUS',
    SYNC_BOOKMARK_STATE: 'SYNC_BOOKMARK_STATE'
};

// Initial state
const initialState = {
    bookmarks: [],
    bookmarkStates: {}, // articleId -> boolean mapping
    loading: false,
    error: null,
    initialized: false
};

// Reducer function
const bookmarkReducer = (state, action) => {
    switch (action.type) {
        case BOOKMARK_ACTIONS.SET_LOADING:
        return { ...state, loading: action.payload };

        case BOOKMARK_ACTIONS.SET_BOOKMARKS:
        const bookmarkStates = {};
        action.payload.forEach(bookmark => {
            const articleId = bookmark.article_id || bookmark.id;
            bookmarkStates[articleId] = true;
        });
        return {
            ...state,
            bookmarks: action.payload,
            bookmarkStates,
            loading: false,
            error: null,
            initialized: true
        };

        case BOOKMARK_ACTIONS.SET_ERROR:
        return { ...state, error: action.payload, loading: false };

        case BOOKMARK_ACTIONS.ADD_BOOKMARK_OPTIMISTIC:
        const { articleId: addId, bookmarkData } = action.payload;
        return {
            ...state,
            bookmarkStates: {
            ...state.bookmarkStates,
            [addId]: true
            },
            bookmarks: [bookmarkData, ...state.bookmarks]
        };

        case BOOKMARK_ACTIONS.REMOVE_BOOKMARK_OPTIMISTIC:
        const { articleId: removeId, bookmarkId } = action.payload;
        return {
            ...state,
            bookmarkStates: {
            ...state.bookmarkStates,
            [removeId]: false
            },
            bookmarks: state.bookmarks.filter(b => b.id !== bookmarkId)
        };

        case BOOKMARK_ACTIONS.UPDATE_BOOKMARK_STATUS:
        return {
            ...state,
            bookmarkStates: {
            ...state.bookmarkStates,
            [action.payload.articleId]: action.payload.isBookmarked
            }
        };

        case BOOKMARK_ACTIONS.SYNC_BOOKMARK_STATE:
        // Sync with server response
        const { articleId: syncId, serverData } = action.payload;
        if (serverData) {
            return {
            ...state,
            bookmarks: serverData.action === 'added' 
                ? [serverData.bookmark, ...state.bookmarks.filter(b => b.article_id !== syncId)]
                : state.bookmarks.filter(b => b.article_id !== syncId),
            bookmarkStates: {
                ...state.bookmarkStates,
                [syncId]: serverData.bookmarked
            }
            };
        }
        return state;

        default:
        return state;
    }
    };

    // Provider component
    export const BookmarkProvider = ({ children }) => {
    const [state, dispatch] = useReducer(bookmarkReducer, initialState);
    const { session, user } = useAuth();

    // Fetch bookmarks from server (only on first load)
    const fetchBookmarks = useCallback(async () => {
        if (!session?.access_token || state.initialized) return;

        dispatch({ type: BOOKMARK_ACTIONS.SET_LOADING, payload: true });

        try {
        const response = await axios.get(`${API_BASE_URL}/api/bookmarks`, {
            headers: { Authorization: `Bearer ${session.access_token}` }
        });
        dispatch({ type: BOOKMARK_ACTIONS.SET_BOOKMARKS, payload: response.data });
        } catch (error) {
        dispatch({ 
            type: BOOKMARK_ACTIONS.SET_ERROR, 
            payload: error.response?.data?.error || 'Unable to load bookmarks' 
        });
        }
    }, [session?.access_token, state.initialized]);

    // Toggle bookmark with Optimistic UI
    const toggleBookmark = useCallback(async (articleData, articleId) => {
        if (!session?.access_token) {
        throw new Error('Not logged in');
        }

        const isCurrentlyBookmarked = state.bookmarkStates[articleId] || false;
        const newState = !isCurrentlyBookmarked;

        // Optimistic update
        if (newState) {
        // Adding bookmark
        const optimisticBookmark = {
            id: `temp_${Date.now()}`, // temporary ID
            article_id: articleId,
            article_data: articleData,
            user_id: user?.id,
            created_at: new Date().toISOString()
        };
        dispatch({
            type: BOOKMARK_ACTIONS.ADD_BOOKMARK_OPTIMISTIC,
            payload: { articleId, bookmarkData: optimisticBookmark }
        });
        } else {
        // Removing bookmark
        const existingBookmark = state.bookmarks.find(b => b.article_id === articleId);
        dispatch({
            type: BOOKMARK_ACTIONS.REMOVE_BOOKMARK_OPTIMISTIC,
            payload: { articleId, bookmarkId: existingBookmark?.id }
        });
        }

        try {
        // API call
        const response = await axios.post(
            `${API_BASE_URL}/api/bookmarks/toggle`,
            { 
            ...articleData,
            article_id: articleId
            },
            { headers: { Authorization: `Bearer ${session.access_token}` } }
        );

        // Sync with server response
        dispatch({
            type: BOOKMARK_ACTIONS.SYNC_BOOKMARK_STATE,
            payload: { articleId, serverData: response.data }
        });

        return response.data;
        } catch (error) {
        // Revert optimistic update on error
        dispatch({
            type: BOOKMARK_ACTIONS.UPDATE_BOOKMARK_STATUS,
            payload: { articleId, isBookmarked: isCurrentlyBookmarked }
        });
        
        // Revert bookmarks list
        if (newState) {
            // Was trying to add, remove the optimistic one
            dispatch({
            type: BOOKMARK_ACTIONS.REMOVE_BOOKMARK_OPTIMISTIC,
            payload: { articleId, bookmarkId: `temp_${Date.now()}` }
            });
        } else {
            // Was trying to remove, add it back
            const originalBookmark = state.bookmarks.find(b => b.article_id === articleId);
            if (originalBookmark) {
            dispatch({
                type: BOOKMARK_ACTIONS.ADD_BOOKMARK_OPTIMISTIC,
                payload: { articleId, bookmarkData: originalBookmark }
            });
            }
        }
        
        throw new Error(error.response?.data?.error || 'Unable to change bookmark');
        }
    }, [session?.access_token, user?.id, state.bookmarkStates, state.bookmarks]);

    // Remove bookmark (for saved articles page)
    const removeBookmark = useCallback(async (bookmarkId) => {
        if (!session?.access_token) {
        throw new Error('Not logged in');
        }

        const bookmark = state.bookmarks.find(b => b.id === bookmarkId);
        const articleId = bookmark?.article_id;

        // Debug log to check articleId mapping
        console.log('RemoveBookmark Debug:', {
        bookmarkId,
        bookmark,
        articleId,
        currentBookmarkStates: state.bookmarkStates
        });

        // Optimistic update - update both bookmarks list and bookmark states
        if (articleId) {
        dispatch({
            type: BOOKMARK_ACTIONS.REMOVE_BOOKMARK_OPTIMISTIC,
            payload: { articleId, bookmarkId }
        });
        }

        try {
        await axios.delete(`${API_BASE_URL}/api/bookmarks/${bookmarkId}`, {
            headers: { Authorization: `Bearer ${session.access_token}` }
        });
        
        // Ensure bookmark state is also updated after successful deletion
        if (articleId) {
            dispatch({
            type: BOOKMARK_ACTIONS.UPDATE_BOOKMARK_STATUS,
            payload: { articleId, isBookmarked: false }
            });
        }
        
        console.log('Bookmark removed successfully, articleId:', articleId);
        } catch (error) {
        // Revert on error - restore both bookmark and state
        if (bookmark && articleId) {
            dispatch({
            type: BOOKMARK_ACTIONS.ADD_BOOKMARK_OPTIMISTIC,
            payload: { articleId, bookmarkData: bookmark }
            });
        }
        throw new Error(error.response?.data?.error || 'Unable to remove bookmark');
        }
    }, [session?.access_token, state.bookmarks, state.bookmarkStates]);

    // Check if article is bookmarked
    const isBookmarked = useCallback((articleId) => {
        const result = Boolean(state.bookmarkStates[articleId]);
        
        // Debug log 
        if (process.env.NODE_ENV === 'development') {
        console.log('isBookmarked check:', {
            articleId,
            bookmarkStates: state.bookmarkStates,
            result
        });
        }
        
        return result;
    }, [state.bookmarkStates]);

    // Load bookmarks on mount if user is logged in
    useEffect(() => {
        if (user && !state.initialized) {
        fetchBookmarks();
        }
    }, [user, fetchBookmarks, state.initialized]);

    // Sync bookmark states with bookmarks list whenever bookmarks change
    useEffect(() => {
        if (state.initialized) {
        const newBookmarkStates = {};
        state.bookmarks.forEach(bookmark => {
            const articleId = bookmark.article_id || bookmark.id;
            newBookmarkStates[articleId] = true;
        });
        
        // Only dispatch if states actually changed
        const currentStates = state.bookmarkStates;
        const hasChanges = Object.keys({...currentStates, ...newBookmarkStates}).some(
            key => currentStates[key] !== newBookmarkStates[key]
        );
        
        if (hasChanges) {
            console.log('Syncing bookmark states:', { old: currentStates, new: newBookmarkStates });
            dispatch({
            type: BOOKMARK_ACTIONS.SET_BOOKMARKS,
            payload: state.bookmarks
            });
        }
        }
    }, [state.bookmarks, state.initialized, state.bookmarkStates]);

    const value = {
        bookmarks: state.bookmarks,
        bookmarkStates: state.bookmarkStates,
        loading: state.loading,
        error: state.error,
        initialized: state.initialized,
        toggleBookmark,
        removeBookmark,
        isBookmarked,
        refetch: fetchBookmarks
    };

    return (
        <BookmarkContext.Provider value={value}>
        {children}
        </BookmarkContext.Provider>
    );
    };

    // Hook to use bookmark context
    export const useBookmarkContext = () => {
    const context = useContext(BookmarkContext);
    if (!context) {
        throw new Error('useBookmarkContext must be used within BookmarkProvider');
    }
    return context;
};
