-- Bookmark Database Schema Update
-- Add article_id column and unique constraint to prevent duplicate bookmarks

-- 1. Add article_id column if it doesn't exist
ALTER TABLE bookmarks 
ADD COLUMN IF NOT EXISTS article_id TEXT;

-- 2. Update existing records with article_id 
-- Extract ID from article_data JSON or create a hash
UPDATE bookmarks 
SET article_id = COALESCE(
    article_data->>'id',
    article_data->>'news_id', 
    md5(article_data::text)
)
WHERE article_id IS NULL;

-- 3. Create unique constraint to prevent duplicates
-- Drop existing constraint if it exists
ALTER TABLE bookmarks 
DROP CONSTRAINT IF EXISTS unique_user_article;

-- Create new unique constraint
ALTER TABLE bookmarks 
ADD CONSTRAINT unique_user_article 
UNIQUE (user_id, article_id);

-- 4. Create indexes to optimize query performance
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_article 
ON bookmarks (user_id, article_id);

CREATE INDEX IF NOT EXISTS idx_bookmarks_user_created 
ON bookmarks (user_id, created_at DESC);

-- 5. Verify schema
-- Check table structure
\d bookmarks;

-- Check for duplicates
SELECT user_id, article_id, COUNT(*) 
FROM bookmarks 
GROUP BY user_id, article_id 
HAVING COUNT(*) > 1;

-- Sample queries to test
-- Get bookmarks for a user
SELECT * FROM bookmarks WHERE user_id = 'test-user' ORDER BY created_at DESC;

-- Check if a specific article is bookmarked
SELECT EXISTS(
    SELECT 1 FROM bookmarks 
    WHERE user_id = 'test-user' AND article_id = 'test-article'
) as is_bookmarked;
