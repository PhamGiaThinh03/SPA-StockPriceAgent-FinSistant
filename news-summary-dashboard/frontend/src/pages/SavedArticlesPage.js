import React from "react";
import { Box, Heading, useToast } from "@chakra-ui/react";
import { useBookmarkContext } from "../contexts/BookmarkContext";
import BookmarkNewsTable from "../components/dashboard/BookmarkNewsTable";

const SavedArticlesPage = () => {
  const { bookmarks, loading, error, removeBookmark } = useBookmarkContext();
  const toast = useToast();

  const handleRemoveBookmark = async (bookmarkId) => {
    try {
      await removeBookmark(bookmarkId);
      toast({
        title: "Đã xóa bookmark",
        description: "Bài báo đã được xóa khỏi danh sách lưu",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: "Lỗi",
        description: error.message,
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  // Transform bookmarks data for the table
  const transformedBookmarks = bookmarks.map((bookmark) => ({
    ...bookmark.article_data,
    bookmark_id: bookmark.id,
  }));

  return (
    <Box>
      <Heading mb={8}>
        Bài báo đã lưu 
        {bookmarks.length > 0 && (
          <Box as="span" color="blue.500" fontSize="lg" ml={2}>
            ({bookmarks.length})
          </Box>
        )}
      </Heading>
      
      <BookmarkNewsTable
        bookmarksData={transformedBookmarks}
        loading={loading}
        error={error}
        onRemoveBookmark={handleRemoveBookmark}
      />
    </Box>
  );
};

export default SavedArticlesPage;
