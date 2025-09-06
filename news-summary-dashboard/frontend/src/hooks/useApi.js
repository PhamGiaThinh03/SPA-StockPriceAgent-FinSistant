import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://hviet-be-for-spa.hf.space';

// Custom hook for fetching news data
export const useNews = (filters = {}) => {
    const [news, setNews] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchNews = useCallback(async (newFilters = {}) => {
        setLoading(true);
        setError(null);
        
        try {
        const params = { ...filters, ...newFilters };
        const response = await axios.get(`${API_BASE_URL}/api/news`, { params });
        setNews(response.data);
        } catch (err) {
        setError(err.response?.data?.error || 'Unable to load news data');
        } finally {
        setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        fetchNews();
    }, [fetchNews]);

    return { news, loading, error, refetch: fetchNews };
};

// Custom hook for Dashboard with advanced filtering logic and pagination
export const useDashboardNews = () => {
    const [news, setNews] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [pagination, setPagination] = useState({
        total: 0,
        page: 1,
        limit: 5,
        total_pages: 0,
        has_next: false,
        has_prev: false
    });

    const fetchNews = useCallback(async (filters = {}, paginationParams = {}) => {
        setLoading(true);
        setError(null);

        // Industry and sentiment mapping
        const industryMap = {
            "Công nghệ": "Technology",
            "Sức khỏe": "Healthcare", 
            "Tài chính": "Finance",
            "Năng lượng": "Energy",
            "Khác": "Other"
        };

        const sentimentMap = {
            "Positive": "Tích_cực",
            "Negative": "Tiêu_cực", 
            "Neutral": "Trung_tính",
        };

        const translateIndustryToEnglish = (vietnameseName) => 
            industryMap[vietnameseName] || vietnameseName;

        const translateSentiment = (sentimentValue) =>
            sentimentMap[sentimentValue] || sentimentValue;

        const params = new URLSearchParams();

        // **STANDARD LOGIC: Prioritize company filter**
        const key = filters.company || translateIndustryToEnglish(filters.industry);
        if (key) {
            params.append("industry", key);
        }

        // Other filters
        const sentimentTranslated = translateSentiment(filters.sentiment);
        if (sentimentTranslated) params.append("sentiment", sentimentTranslated);
        if (filters.date) params.append("date", filters.date);

        // Pagination parameters - use passed params or current state
        const page = paginationParams.page || 1;
        const limit = paginationParams.limit || 5;
        params.append("page", page);
        params.append("limit", limit);

        const apiUrl = `${API_BASE_URL}/api/news?${params.toString()}`;

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) throw new Error("Network error or server not responding");
            const data = await response.json();
            
            // Handle both old format (array) and new format (object with pagination)
            if (Array.isArray(data)) {
                // Old format - convert to new format for backward compatibility
                setNews(data);
                setPagination({
                    total: data.length,
                    page: 1,
                    limit: data.length,
                    total_pages: 1,
                    has_next: false,
                    has_prev: false
                });
            } else {
                // New format with pagination
                setNews(data.items || []);
                setPagination({
                    total: data.total || 0,
                    page: data.page || 1,
                    limit: data.limit || 5,
                    total_pages: data.total_pages || 0,
                    has_next: data.has_next || false,
                    has_prev: data.has_prev || false
                });
            }
        } catch (err) {
            console.error("Error fetching dashboard news:", err.message);
            setError("Unable to load news data.");
            setNews([]);
            setPagination({
                total: 0,
                page: 1,
                limit: 5,
                total_pages: 0,
                has_next: false,
                has_prev: false
            });
        } finally {
            setLoading(false);
        }
    }, []); // Empty dependency array to prevent re-creation

    return { news, loading, error, pagination, fetchNews };
};

// Custom hook for managing bookmarks
export const useBookmarks = () => {
    const [bookmarks, setBookmarks] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const { session } = useAuth();

    const fetchBookmarks = useCallback(async () => {
        if (!session?.access_token) return;
        
        setLoading(true);
        setError(null);
        
        try {
        const response = await axios.get(`${API_BASE_URL}/api/bookmarks`, {
            headers: {
                Authorization: `Bearer ${session.access_token}`,
            },
        });
        setBookmarks(response.data);
        } catch (err) {
        setError(err.response?.data?.error || 'Unable to load bookmarks list');
        } finally {
        setLoading(false);
        }
    }, [session?.access_token]); // Only depend on access_token

    const addBookmark = useCallback(async (articleData) => {
        if (!session?.access_token) throw new Error('Not logged in');
        
        try {
        const response = await axios.post(
            `${API_BASE_URL}/api/bookmarks`,
            articleData,
            { 
                headers: {
                    Authorization: `Bearer ${session.access_token}`,
                }
            }
        );
        setBookmarks(prev => [response.data, ...prev]);
        return response.data;
        } catch (err) {
        throw new Error(err.response?.data?.error || 'Unable to add bookmark');
        }
    }, [session?.access_token]);

    const removeBookmark = useCallback(async (bookmarkId) => {
        if (!session?.access_token) throw new Error('Not logged in');
        
        try {
        await axios.delete(`${API_BASE_URL}/api/bookmarks/${bookmarkId}`, {
            headers: {
                Authorization: `Bearer ${session.access_token}`,
            },
        });
        setBookmarks(prev => prev.filter(bookmark => bookmark.id !== bookmarkId));
        } catch (err) {
        throw new Error(err.response?.data?.error || 'Unable to remove bookmark');
        }
    }, [session?.access_token]);

    useEffect(() => {
        fetchBookmarks();
    }, [fetchBookmarks]);

    return { 
        bookmarks, 
        loading, 
        error, 
        addBookmark, 
        removeBookmark, 
        refetch: fetchBookmarks 
    };
};

// Lightweight hook for bookmark actions only (no data fetching)
export const useBookmarkActions = () => {
    const { session } = useAuth();

    const toggleBookmark = useCallback(async (articleData, articleId = null) => {
        if (!session?.access_token) throw new Error('Not logged in');
        
        try {
        const response = await axios.post(
            `${API_BASE_URL}/api/bookmarks/toggle`,
            { 
                ...articleData,
                article_id: articleId || articleData.id || articleData.news_id 
            },
            { 
                headers: {
                    Authorization: `Bearer ${session.access_token}`,
                }
            }
        );
        return response.data;
        } catch (err) {
        throw new Error(err.response?.data?.error || 'Unable to toggle bookmark');
        }
    }, [session?.access_token]);

    const addBookmark = useCallback(async (articleData) => {
        if (!session?.access_token) throw new Error('Not logged in');
        
        try {
        const response = await axios.post(
            `${API_BASE_URL}/api/bookmarks`,
            articleData,
            { 
                headers: {
                    Authorization: `Bearer ${session.access_token}`,
                }
            }
        );
        return response.data;
        } catch (err) {
        throw new Error(err.response?.data?.error || 'Unable to add bookmark');
        }
    }, [session?.access_token]);

    const removeBookmark = useCallback(async (bookmarkId) => {
        if (!session?.access_token) throw new Error('Not logged in');
        
        try {
        await axios.delete(`${API_BASE_URL}/api/bookmarks/${bookmarkId}`, {
            headers: {
                Authorization: `Bearer ${session.access_token}`,
            },
        });
        } catch (err) {
        throw new Error(err.response?.data?.error || 'Unable to remove bookmark');
        }
    }, [session?.access_token]);

    return { toggleBookmark, addBookmark, removeBookmark };
};

// Custom hook for stock data
export const useStockData = (ticker, timeRange = 'all') => {
    const [stockData, setStockData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchStockData = useCallback(async (newTicker = ticker, newTimeRange = timeRange) => {
        if (!newTicker) return;
        
        setLoading(true);
        setError(null);
        
        try {
        const response = await axios.get(
            `${API_BASE_URL}/api/stocks/${newTicker}/history`,
            { params: { range: newTimeRange } }
        );
        setStockData(response.data);
        } catch (err) {
        setError(err.response?.data?.error || 'Unable to load stock data');
        } finally {
        setLoading(false);
        }
    }, [ticker, timeRange]);

    useEffect(() => {
        fetchStockData();
    }, [fetchStockData]);

    return { stockData, loading, error, refetch: fetchStockData };
};

// Custom hook for local storage
export const useLocalStorage = (key, initialValue) => {
    const [storedValue, setStoredValue] = useState(() => {
        try {
        const item = window.localStorage.getItem(key);
        return item ? JSON.parse(item) : initialValue;
        } catch (error) {
        console.error(`Error reading localStorage key "${key}":`, error);
        return initialValue;
        }
    });

    const setValue = (value) => {
        try {
        const valueToStore = value instanceof Function ? value(storedValue) : value;
        setStoredValue(valueToStore);
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
        } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error);
        }
    };

    return [storedValue, setValue];
};
