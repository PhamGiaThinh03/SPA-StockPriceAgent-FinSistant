import React, { useState, useEffect } from "react";
import {
  Tooltip,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Box,
  Text,
  HStack,
  Tag,
  IconButton,
  Button,
  Flex,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  VStack,
  Heading,
  Icon,
  Link,
  useToast,
} from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { FaRegBookmark, FaBookmark, FaBuilding } from "react-icons/fa";
import { StarIcon, CalendarIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import { useBookmarkContext } from "../../contexts/BookmarkContext";
import { useAuth } from "../../contexts/AuthContext";

const NewsTable = ({ newsData, loading, error, pagination, onPageChange }) => {
  // Use optimized bookmark context
  const { toggleBookmark, isBookmarked } = useBookmarkContext();
  const { user } = useAuth();
  const toast = useToast();
  
  // State for UI interactions - Remove local pagination since it's now server-side
  const [currentPage, setCurrentPage] = useState(1);

  // Modal state
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedNews, setSelectedNews] = useState(null);

  // Update current page when pagination changes
  useEffect(() => {
    if (pagination?.page) {
      setCurrentPage(pagination.page);
    }
  }, [pagination?.page]);

  // Handle page change
  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    if (onPageChange) {
      onPageChange(newPage);
    }
  };

  // Helper function to generate consistent article ID
  const getArticleId = (newsItem, index = null) => {
    // Priority order for unique identification
    if (newsItem.id) return `id-${newsItem.id}`;
    if (newsItem.news_id) return `news-${newsItem.news_id}`;
    
    // Create composite ID from multiple fields for uniqueness
    const title = newsItem.title || newsItem.news_title || '';
    const date = newsItem.date || '';
    const content = (newsItem.news_content || newsItem.summary || '').slice(0, 20);
    
    // Use index as last resort to ensure uniqueness
    const fallbackId = `${date}-${title.slice(0, 20)}-${content}`.replace(/\s+/g, '-');
    return index !== null ? `${fallbackId}-idx-${index}` : fallbackId;
  };

  // Check if a news item is bookmarked using context
  const isNewsBookmarked = (newsItem, index = null) => {
    const articleId = getArticleId(newsItem, index);
    
    // Use context to check bookmark status
    const contextBookmarked = isBookmarked(articleId);
    
    // Fallback to server data if context doesn't have the info
    return contextBookmarked || (newsItem.bookmark_id != null && newsItem.bookmark_id !== undefined);
  };

  // Handle bookmark toggle with optimized context
  const handleBookmark = async (e, newsItem, index) => {
    e.stopPropagation();

    if (!user) {
      toast({
        title: "Cần đăng nhập",
        description: "Vui lòng đăng nhập để sử dụng tính năng bookmark",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    const articleId = getArticleId(newsItem, index);

    try {
      const result = await toggleBookmark(newsItem, articleId);
      
      // Show success notification
      toast({
        title: result.action === 'added' ? "Đã thêm bookmark" : "Đã xóa bookmark",
        description: result.action === 'added' 
          ? "Bài báo đã được thêm vào danh sách lưu" 
          : "Bài báo đã được xóa khỏi danh sách lưu",
        status: "success",
        duration: 2000,
        isClosable: true,
      });

    } catch (err) {
      // Show error notification
      toast({
        title: "Lỗi",
        description: err.message,
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };
  
  // Handle row click for modal
  const handleRowClick = (newsItem) => {
    setSelectedNews(newsItem);
    onOpen();
  };

  // Server-side pagination - use data directly from API
  const currentData = newsData || [];
  const totalPages = pagination?.total_pages || 1;
  const totalItems = pagination?.total || 0;

  const formatPageNumber = (number) => {
    return String(number).padStart(2, "0");
  };

  // Helper function to safely get field values
  const getFieldValue = (item, field, fallback = '') => {
    return item?.[field] || fallback;
  };

  // Helper function to handle array fields
  const getArrayFieldValue = (item, field, maxItems = 2) => {
    const value = item?.[field];
    if (!value) return [];
    return Array.isArray(value) ? value : [value];
  };


  // --- Render logic ---
  const spin = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
  `;

  if (loading) {
    return (
      <Box>
        {/* Show table header while loading */}
        <Box overflowX="auto">
          <Table variant="simple" width="100%" tableLayout="fixed">
            <Thead>
              <Tr bg="gray.100">
                <Th w="2%"></Th>
                <Th w="10%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Ngày
                </Th>
                <Th w="12%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Ngành
                </Th>
                <Th w="28%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Tiêu đề
                </Th>
                <Th w="38%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Tóm tắt
                </Th>
                <Th w="10%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Ảnh hưởng
                </Th>
              </Tr>
            </Thead>
            <Tbody>
              {/* Show 5 skeleton rows to match actual table height */}
              {Array(5).fill("").map((_, i) => (
                <Tr key={`skeleton-${i}`} height="80px" minHeight="80px">
                  <Td colSpan={6}>
                    <Flex justify="center" align="center" height="100%">
                      {i === 2 && ( // Only show loading indicator in middle row
                        <Flex align="center" gap={3}>
                          <Box position="relative" w="40px" h="40px">
                            <Box
                              position="absolute"
                              top="0"
                              left="0"
                              w="100%"
                              h="100%"
                              borderRadius="full"
                              border="3px solid"
                              borderColor="transparent"
                              borderTopColor="blue.400"
                              animation={`${spin} 1s linear infinite`}
                            />
                          </Box>
                          <Text
                            fontSize="md"
                            fontWeight="medium"
                            color="blue.500"
                          >
                            Đang tải dữ liệu...
                          </Text>
                        </Flex>
                      )}
                    </Flex>
                  </Td>
                  </Tr>
                ))}
            </Tbody>
          </Table>
        </Box>
        
        {/* Pagination placeholder */}
        <Flex justify="space-between" align="center" mt={4} px={2}>
          <Text fontSize="sm" color="gray.400">
            Đang tải...
          </Text>
          <Flex justify="center" gap={2}>
            <Button size="sm" variant="outline" isDisabled>
              Trang đầu
            </Button>
            <Button size="sm" variant="outline" isDisabled>
              Trang trước
            </Button>
            <Flex align="center" mx={4}>
              <Text fontSize="sm" fontWeight="medium" color="gray.400">
                Trang -- / --
              </Text>
            </Flex>
            <Button size="sm" variant="outline" isDisabled>
              Trang sau
            </Button>
            <Button size="sm" variant="outline" isDisabled>
              Trang cuối
            </Button>
          </Flex>
        </Flex>
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        {/* Show table header even on error */}
        <Box overflowX="auto">
          <Table variant="simple" width="100%" tableLayout="fixed">
            <Thead>
              <Tr bg="gray.100">
                <Th w="2%"></Th>
                <Th w="10%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Ngày
                </Th>
                <Th w="12%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Ngành
                </Th>
                <Th w="28%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Tiêu đề
                </Th>
                <Th w="38%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Tóm tắt
                </Th>
                <Th w="10%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Ảnh hưởng
                </Th>
              </Tr>
            </Thead>
            <Tbody>
              {/* Show 5 empty rows to match table height */}
              {Array(5).fill("").map((_, i) => (
                <Tr key={`error-${i}`} height="80px" minHeight="80px">
                  <Td colSpan={6}>
                    {i === 2 && ( // Only show error message in middle row
                      <Flex justify="center" align="center" height="100%" flexDirection="column" gap={2}>
                        <Text fontSize="md" fontWeight="medium" color="red.500">{error}</Text>
                        <Text fontSize="sm" color="gray.500">Vui lòng thử lại sau</Text>
                      </Flex>
                    )}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
        
        {/* Pagination placeholder */}
        <Flex justify="space-between" align="center" mt={4} px={2}>
          <Text fontSize="sm" color="gray.400">
            Không có dữ liệu
          </Text>
          <Flex justify="center" gap={2}>
            <Button size="sm" variant="outline" isDisabled>
              Trang đầu
            </Button>
            <Button size="sm" variant="outline" isDisabled>
              Trang trước
            </Button>
            <Flex align="center" mx={4}>
              <Text fontSize="sm" fontWeight="medium" color="gray.400">
                Trang 01 / 01
              </Text>
            </Flex>
            <Button size="sm" variant="outline" isDisabled>
              Trang sau
            </Button>
            <Button size="sm" variant="outline" isDisabled>
              Trang cuối
            </Button>
          </Flex>
        </Flex>
      </Box>
    );
  }

  if (!newsData || newsData.length === 0) {
    return (
      <Box>
        {/* Show table header even when empty */}
        <Box overflowX="auto">
          <Table variant="simple" width="100%" tableLayout="fixed">
            <Thead>
              <Tr bg="gray.100">
                <Th w="2%"></Th>
                <Th w="10%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Ngày
                </Th>
                <Th w="12%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Ngành
                </Th>
                <Th w="28%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Tiêu đề
                </Th>
                <Th w="38%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Tóm tắt
                </Th>
                <Th w="10%" fontSize="lg" fontWeight="bold" textTransform="none">
                  Ảnh hưởng
                </Th>
              </Tr>
            </Thead>
            <Tbody>
              {/* Show 5 empty rows to match table height */}
              {Array(5).fill("").map((_, i) => (
                <Tr key={`empty-${i}`} height="80px" minHeight="80px">
                  <Td colSpan={6}>
                    {i === 2 && ( // Only show empty message in middle row
                      <Flex justify="center" align="center" height="100%" flexDirection="column" gap={2}>
                        <Text fontSize="md" color="gray.500">
                          Không có dữ liệu tin tức
                        </Text>
                        <Text fontSize="sm" color="gray.400">
                          Hãy thử thay đổi bộ lọc hoặc tải lại trang
                        </Text>
                      </Flex>
                    )}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
        
        {/* Pagination placeholder */}
        <Flex justify="space-between" align="center" mt={4} px={2}>
          <Text fontSize="sm" color="gray.400">
            Hiển thị 0 trên tổng 0 bài báo
          </Text>
          <Flex justify="center" gap={2}>
            <Button size="sm" variant="outline" isDisabled>
              Trang đầu
            </Button>
            <Button size="sm" variant="outline" isDisabled>
              Trang trước
            </Button>
            <Flex align="center" mx={4}>
              <Text fontSize="sm" fontWeight="medium" color="gray.400">
                Trang 01 / 01
              </Text>
            </Flex>
            <Button size="sm" variant="outline" isDisabled>
              Trang sau
            </Button>
            <Button size="sm" variant="outline" isDisabled>
              Trang cuối
            </Button>
          </Flex>
        </Flex>
      </Box>
    );
  }

  return (
    <Box>
      {/* Table container with dynamic height */}
      <Box overflowX="auto">
        <Table variant="simple" width="100%" tableLayout="fixed">
          <Thead>
            <Tr bg="gray.100">
              <Th w="2%"></Th>
              <Th w="10%" fontSize="lg" fontWeight="bold" textTransform="none">
                Ngày
              </Th>
              <Th w="12%" fontSize="lg" fontWeight="bold" textTransform="none">
                Ngành
              </Th>
              <Th w="28%" fontSize="lg" fontWeight="bold" textTransform="none">
                Tiêu đề
              </Th>
              <Th w="38%" fontSize="lg" fontWeight="bold" textTransform="none">
                Tóm tắt
              </Th>
              <Th w="10%" fontSize="lg" fontWeight="bold" textTransform="none">
                Ảnh hưởng
              </Th>
            </Tr>
          </Thead>
          <Tbody>
            {currentData.map((row, idx) => (
              <Tr
                key={row.id || idx}
                _hover={{ bg: "gray.50", cursor: "pointer" }}
                height="80px"
                minHeight="80px"
                onClick={() => handleRowClick(row)}
              >
                {/* Bookmark */}
                <Td w="2%" textAlign="center">
                  <IconButton
                    icon={
                      isNewsBookmarked(row, idx) ? (
                        <FaBookmark />
                      ) : (
                        <FaRegBookmark />
                      )
                    }
                    color={
                      isNewsBookmarked(row, idx) ? "yellow.400" : "blue.500"
                    }
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleBookmark(e, row, idx)}
                    aria-label={
                      isNewsBookmarked(row, idx)
                        ? "Bỏ bookmark"
                        : "Đánh dấu bookmark"
                    }
                    _hover={{
                      bg: isNewsBookmarked(row, idx) ? "yellow.100" : "blue.100",
                      transform: "scale(1.1)"
                    }}
                    transition="all 0.2s"
                  />
                </Td>
                {/* Date */}
                <Td w="10%">{getFieldValue(row, 'date')}</Td>
                
                {/* Industry */}
                <Td w="12%">
                  <Tooltip
                    label={getArrayFieldValue(row, 'industry').join(", ")}
                    placement="right"
                    openDelay={300}
                    bg="blue.100"
                    color="gray.800"
                    borderRadius="md"
                    fontSize="sm"
                    px={4}
                    py={2}
                  >
                    <Box cursor="pointer">
                      <Flex
                        direction="column"
                        gap={1}
                        align="flex-start"
                        color="blue.500"
                      >
                        {getArrayFieldValue(row, 'industry').slice(0, 2).map((item, i) => (
                          <Text
                            key={i}
                            userSelect="none"
                            fontWeight="medium"
                            isTruncated
                          >
                            {item}
                          </Text>
                        ))}
                        {getArrayFieldValue(row, 'industry').length > 2 && (
                          <Text
                            fontSize="sm"
                            color="gray.500"
                            width="fit-content"
                          >
                            +{getArrayFieldValue(row, 'industry').length - 2}
                          </Text>
                        )}
                      </Flex>
                    </Box>
                  </Tooltip>
                </Td>
                
                {/* Title */}
                <Td w="28%">
                  <Tooltip
                    label={getFieldValue(row, 'news_title') || getFieldValue(row, 'title')}
                    isDisabled={(getFieldValue(row, 'news_title') || getFieldValue(row, 'title')).length <= 50}
                    placement="top-start"
                    bg="blue.100"
                    color="gray.800"
                    borderRadius="md"
                    fontSize="sm"
                    px={4}
                    py={2}
                  >
                    <Text
                      fontWeight="medium"
                      noOfLines={2}
                      cursor={(getFieldValue(row, 'news_title') || getFieldValue(row, 'title')).length > 50 ? "pointer" : "default"}
                    >
                      {getFieldValue(row, 'news_title') || getFieldValue(row, 'title')}
                    </Text>
                  </Tooltip>
                </Td>
                
                {/* Summary */}
                <Td w="38%">
                  <Tooltip
                    label={getFieldValue(row, 'news_content') || getFieldValue(row, 'summary')}
                    isDisabled={(getFieldValue(row, 'news_content') || getFieldValue(row, 'summary')).length <= 80}
                    placement="top-start"
                    openDelay={300}
                    bg="blue.50"
                    color="gray.800"
                    borderRadius="md"
                    fontSize="sm"
                    px={4}
                    py={2}
                  >
                    <Text
                      color="gray.600"
                      noOfLines={2}
                      cursor={(getFieldValue(row, 'news_content') || getFieldValue(row, 'summary')).length > 80 ? "pointer" : "default"}
                    >
                      {getFieldValue(row, 'news_content') || getFieldValue(row, 'summary')}
                    </Text>
                  </Tooltip>
                </Td>
                
                {/* Influence */}
                <Td w="10%">
                  <Tooltip
                    label={getArrayFieldValue(row, 'influence').join(" ")}
                    placement="right"
                    openDelay={300}
                    bg="blue.100"
                    color="gray.800"
                    borderRadius="md"
                    fontSize="sm"
                    px={4}
                    py={2}
                  >
                    <Box cursor="pointer">
                      <Flex direction="column" gap={1} align="flex-start">
                        {getArrayFieldValue(row, 'influence').slice(0, 2).map((tag, i) => (
                          <Tag
                            key={i}
                            size="sm"
                            colorScheme="blue"
                            variant="subtle"
                            whiteSpace="nowrap"
                            userSelect="none"
                            width="fit-content"
                          >
                            {tag}
                          </Tag>
                        ))}
                        {getArrayFieldValue(row, 'influence').length > 2 && (
                          <Tag
                            size="sm"
                            colorScheme="gray"
                            variant="subtle"
                            whiteSpace="nowrap"
                            userSelect="none"
                            width="fit-content"
                          >
                            +{getArrayFieldValue(row, 'influence').length - 2}
                          </Tag>
                        )}
                      </Flex>
                    </Box>
                  </Tooltip>
                </Td>
              </Tr>
            ))}
            {/* No empty rows needed with pagination - let table height be dynamic */}
          </Tbody>
        </Table>
      </Box>
      {/* Pagination controls */}
      <Flex justify="space-between" align="center" mt={4} px={2}>
        <Text fontSize="sm" color="gray.600">
          Hiển thị {currentData.length} trên tổng {totalItems} bài báo
        </Text>
        
        <Flex justify="center" gap={2}>
          <Button
            onClick={() => handlePageChange(1)}
            isDisabled={currentPage === 1 || loading}
            size="sm"
            variant="outline"
          >
            Trang đầu
          </Button>
          <Button
            onClick={() => handlePageChange(currentPage - 1)}
            isDisabled={currentPage === 1 || loading}
            size="sm"
            variant="outline"
          >
            Trang trước
          </Button>
          
          <Flex align="center" mx={4}>
            <Text fontSize="sm" fontWeight="medium">
              Trang {formatPageNumber(currentPage)} / {formatPageNumber(totalPages)}
            </Text>
          </Flex>
          
          <Button
            onClick={() => handlePageChange(currentPage + 1)}
            isDisabled={currentPage === totalPages || totalPages === 0 || loading}
            size="sm"
            variant="outline"
          >
            Trang sau
          </Button>
          <Button
            onClick={() => handlePageChange(totalPages)}
            isDisabled={currentPage === totalPages || totalPages === 0 || loading}
            size="sm"
            variant="outline"
          >
            Trang cuối
          </Button>
        </Flex>
      </Flex>

      {/* 5. THÊM COMPONENT MODAL */}
      {selectedNews && (
        <Modal
          isOpen={isOpen}
          onClose={onClose}
          size="5xl"
          scrollBehavior="inside"
          motionPreset="scale"
          isCentered
        >
          <ModalOverlay bg="blackAlpha.700" backdropFilter="blur(2px)" />

          <ModalContent borderRadius="xl" overflow="hidden" boxShadow="xl">
            <Box bgGradient="linear(to-r, blue.600, blue.500)" px={6} py={4}>
              <ModalHeader color="white" px={0} pt={3}>
                <Heading size="xl">
                  {getFieldValue(selectedNews, 'news_title') || getFieldValue(selectedNews, 'title')}
                </Heading>
              </ModalHeader>

              <ModalCloseButton
                size="lg"
                color="white"
                _hover={{ bg: "blue.400" }}
              />
            </Box>

            <ModalBody py={6} px={{ base: 4, md: 8 }}>
              <VStack align="start" spacing={6}>
                {/* Meta Information */}
                <Flex
                  direction={{ base: "column", md: "row" }}
                  gap={4}
                  wrap="wrap"
                  pb={3}
                  borderBottom="1px solid"
                  borderColor="gray.100"
                  w="full"
                >
                  <HStack spacing={2} align="center">
                    <Icon as={CalendarIcon} color="blue.500" boxSize={5} />
                    <Text fontWeight="600" color="gray.600">
                      Ngày:
                    </Text>
                    <Text color="gray.800">{getFieldValue(selectedNews, 'date')}</Text>
                  </HStack>

                  <HStack spacing={2} align="center">
                    <Icon as={FaBuilding} color="green.500" boxSize={5} />
                    <Text fontWeight="600" color="gray.600">
                      Ngành:
                    </Text>
                    <Text color="gray.800">
                      {getArrayFieldValue(selectedNews, 'industry').join(", ")}
                    </Text>
                  </HStack>

                  <HStack spacing={2} align="center">
                    <Icon as={StarIcon} color="orange.500" boxSize={5} />
                    <Text fontWeight="600" color="gray.600">
                      Ảnh hưởng:
                    </Text>
                    <Text color="gray.800">
                      {getArrayFieldValue(selectedNews, 'influence').join(", ")}
                    </Text>
                  </HStack>
                </Flex>

                {/* Summary/Content */}
                <Box w="full">
                  <Heading
                    size="md"
                    mb={3}
                    color="blue.700"
                    display="flex"
                    alignItems="center"
                  >
                    <Box
                      w="4px"
                      h="22px"
                      bg="blue.500"
                      mr={2}
                      borderRadius="full"
                    />
                    {getFieldValue(selectedNews, 'news_content') ? 'Nội dung' : 'Tóm tắt'}
                  </Heading>
                  <Text
                    bg="blue.50"
                    p={4}
                    borderRadius="lg"
                    borderLeft="4px solid"
                    borderColor="blue.500"
                    fontStyle="italic"
                    color="gray.700"
                    fontSize="lg"
                    lineHeight="tall"
                  >
                    {getFieldValue(selectedNews, 'news_content') || getFieldValue(selectedNews, 'summary')}
                  </Text>
                </Box>

                {/* Link/Source */}
                {(getFieldValue(selectedNews, 'link') || getFieldValue(selectedNews, 'source')) && (
                  <Box w="full">
                    <Heading
                      size="md"
                      mb={3}
                      color="blue.700"
                      display="flex"
                      alignItems="center"
                    >
                      <Box
                        w="4px"
                        h="22px"
                        bg="blue.500"
                        mr={2}
                        borderRadius="full"
                      />
                      Nguồn
                    </Heading>
                    <Box bg="gray.50" p={4} borderRadius="lg">
                      <Link
                        href={getFieldValue(selectedNews, 'link') || getFieldValue(selectedNews, 'source')}
                        isExternal
                        color="blue.500"
                        fontWeight="600"
                        wordBreak="break-all"
                        _hover={{
                          textDecoration: "underline",
                          color: "blue.600",
                        }}
                      >
                        <HStack align="center">
                          <ExternalLinkIcon mr={2} />
                          <Text>
                            {getFieldValue(selectedNews, 'source') || "Xem bài báo gốc"}
                          </Text>
                        </HStack>
                      </Link>
                    </Box>
                  </Box>
                )}

                {/* Influence Tags */}
                {getArrayFieldValue(selectedNews, 'influence').length > 0 && (
                  <Box w="full">
                    <Heading
                      size="md"
                      mb={3}
                      color="blue.700"
                      display="flex"
                      alignItems="center"
                    >
                      <Box
                        w="4px"
                        h="22px"
                        bg="blue.500"
                        mr={2}
                        borderRadius="full"
                      />
                      Ảnh hưởng
                    </Heading>
                    <Flex wrap="wrap" gap={2}>
                      {getArrayFieldValue(selectedNews, 'influence').map((tag, i) => (
                        <Tag
                          key={i}
                          size="md"
                          colorScheme="blue"
                          variant="solid"
                          borderRadius="full"
                          px={4}
                          py={1.5}
                          fontWeight="600"
                        >
                          #{tag}
                        </Tag>
                      ))}
                    </Flex>
                  </Box>
                )}
              </VStack>
            </ModalBody>

            <ModalFooter borderTop="1px solid" borderColor="gray.100">
              <Button
                onClick={onClose}
                colorScheme="blue"
                size="lg"
                px={8}
                borderRadius="md"
                _hover={{ transform: "scale(1.02)" }}
                transition="all 0.2s"
              >
                Đóng
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      )}
    </Box>
  );
};

export default NewsTable;