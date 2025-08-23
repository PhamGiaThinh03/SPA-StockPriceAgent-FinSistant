// Application constants

export const API_ENDPOINTS = {
    NEWS: '/api/news',
    BOOKMARKS: '/api/bookmarks',
    STOCKS: '/api/stocks',
};

export const ROUTES = {
    HOME: '/',
    ANALYTICS: '/analytics',
    SAVED_ARTICLES: '/saved-articles',
    SETTINGS: '/settings',
    AUTH: '/auth',
};

export const INDUSTRIES = [
    'Technology',
    'Finance',
    'Healthcare',
    'Energy',
    'Others'
];

export const SENTIMENTS = [
    { value: 'positive', label: 'Tích cực', color: 'green' },
    { value: 'negative', label: 'Tiêu cực', color: 'red' },
    { value: 'neutral', label: 'Trung tính', color: 'gray' }
];

export const TIME_RANGES = [
    { value: '1D', label: '1 Ngày' },
    { value: '1W', label: '1 Tuần' },
    { value: '1M', label: '1 Tháng' },
    { value: '3M', label: '3 Tháng' },
    { value: '6M', label: '6 Tháng' },
    { value: '1Y', label: '1 Năm' },
    { value: 'all', label: 'Tất cả' }
];

export const CHART_COLORS = {
    PRIMARY: '#3182CE',
    SUCCESS: '#38A169',
    WARNING: '#D69E2E',
    DANGER: '#E53E3E',
    INFO: '#805AD5',
    SECONDARY: '#718096'
};

export const DEFAULT_PAGINATION = {
    PAGE_SIZE: 10,
    INITIAL_PAGE: 1
};

export const LOCAL_STORAGE_KEYS = {
    USER_PREFERENCES: 'user_preferences',
    THEME: 'theme',
    DASHBOARD_FILTERS: 'dashboard_filters'
};

export const ERROR_MESSAGES = {
    NETWORK_ERROR: 'Lỗi kết nối mạng',
    AUTH_REQUIRED: 'Vui lòng đăng nhập',
    INVALID_CREDENTIALS: 'Thông tin đăng nhập không hợp lệ',
    GENERIC_ERROR: 'Đã xảy ra lỗi, vui lòng thử lại'
};

export const SUCCESS_MESSAGES = {
    BOOKMARK_ADDED: 'Đã thêm vào danh sách lưu',
    BOOKMARK_REMOVED: 'Đã xóa khỏi danh sách lưu',
    DATA_UPDATED: 'Dữ liệu đã được cập nhật',
    SETTINGS_SAVED: 'Đã lưu cài đặt'
};
