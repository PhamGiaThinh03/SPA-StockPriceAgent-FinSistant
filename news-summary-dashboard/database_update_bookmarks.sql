-- Bookmark Database Schema Update
-- Thêm column article_id và unique constraint để tránh duplicate bookmark

-- 1. Thêm column article_id nếu chưa có
ALTER TABLE bookmarks 
ADD COLUMN IF NOT EXISTS article_id TEXT;

-- 2. Update existing records với article_id 
-- Extract ID từ article_data JSON hoặc tạo hash
UPDATE bookmarks 
SET article_id = COALESCE(
    article_data->>'id',
    article_data->>'news_id', 
    md5(article_data::text)
)
WHERE article_id IS NULL;

-- 3. Tạo unique constraint để tránh duplicate
-- Drop existing constraint nếu có
ALTER TABLE bookmarks 
DROP CONSTRAINT IF EXISTS unique_user_article;

-- Tạo unique constraint mới
ALTER TABLE bookmarks 
ADD CONSTRAINT unique_user_article 
UNIQUE (user_id, article_id);

-- 4. Tạo index để optimize query performance
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_article 
ON bookmarks (user_id, article_id);

CREATE INDEX IF NOT EXISTS idx_bookmarks_user_created 
ON bookmarks (user_id, created_at DESC);

-- 5. Verify schema
-- Check structure
\d bookmarks;

-- Check for duplicates
SELECT user_id, article_id, COUNT(*) 
FROM bookmarks 
GROUP BY user_id, article_id 
HAVING COUNT(*) > 1;

-- Sample queries to test
-- Get bookmarks for user
SELECT * FROM bookmarks WHERE user_id = 'test-user' ORDER BY created_at DESC;

-- Check if specific article is bookmarked
SELECT EXISTS(
    SELECT 1 FROM bookmarks 
    WHERE user_id = 'test-user' AND article_id = 'test-article'
) as is_bookmarked;
