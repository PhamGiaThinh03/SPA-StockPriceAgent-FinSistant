// Utility functions for the frontend

/**
 * Format date to Vietnamese format
 */
export const formatDate = (dateString) => {
  if (!dateString) return '';
  
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  } catch (error) {
    return dateString;
  }
};

/**
 * Format number with thousands separator
 */
export const formatNumber = (number, decimals = 2) => {
  if (typeof number !== 'number') return number;
  
  return new Intl.NumberFormat('vi-VN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(number);
};

/**
 * Format currency in VND
 */
export const formatCurrency = (amount) => {
  if (typeof amount !== 'number') return amount;
  
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND'
  }).format(amount);
};

/**
 * Truncate text to specified length
 */
export const truncateText = (text, maxLength = 100) => {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

/**
 * Get sentiment color for badges
 */
export const getSentimentColor = (sentiment) => {
  const colors = {
    'positive': 'green',
    'negative': 'red',
    'neutral': 'gray',
    'tích cực': 'green',
    'tiêu cực': 'red',
    'trung tính': 'gray'
  };
  
  return colors[sentiment?.toLowerCase()] || 'gray';
};

/**
 * Get industry color for charts
 */
export const getIndustryColor = (industry, index = 0) => {
  const colors = [
    '#3182CE', '#38A169', '#D69E2E', '#E53E3E', '#805AD5',
    '#DD6B20', '#319795', '#C53030', '#9F7AEA', '#2B6CB0'
  ];
  
  // Try to get consistent color for known industries
  const industryColors = {
    'Technology': '#3182CE',
    'Finance': '#38A169',
    'Healthcare': '#E53E3E',
    'Energy': '#D69E2E',
    'Retail': '#805AD5'
  };
  
  return industryColors[industry] || colors[index % colors.length];
};

/**
 * Debounce function for search inputs
 */
export const debounce = (func, wait, immediate) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      timeout = null;
      if (!immediate) func(...args);
    };
    const callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) func(...args);
  };
};

/**
 * Check if user is on mobile device
 */
export const isMobileDevice = () => {
  return window.innerWidth <= 768;
};

/**
 * Validate email format
 */
export const isValidEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

/**
 * Generate random ID
 */
export const generateId = () => {
  return Math.random().toString(36).substr(2, 9);
};

/**
 * Download data as JSON file
 */
export const downloadJSON = (data, filename = 'data.json') => {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json'
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Copy text to clipboard
 */
export const copyToClipboard = async (text) => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    return true;
  }
};

/**
 * Get relative time (e.g., "2 hours ago")
 */
export const getRelativeTime = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffInMs = now - date;
  const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
  const diffInHours = Math.floor(diffInMinutes / 60);
  const diffInDays = Math.floor(diffInHours / 24);
  
  if (diffInMinutes < 1) return 'Vừa xong';
  if (diffInMinutes < 60) return `${diffInMinutes} phút trước`;
  if (diffInHours < 24) return `${diffInHours} giờ trước`;
  if (diffInDays < 7) return `${diffInDays} ngày trước`;
  
  return formatDate(dateString);
};
