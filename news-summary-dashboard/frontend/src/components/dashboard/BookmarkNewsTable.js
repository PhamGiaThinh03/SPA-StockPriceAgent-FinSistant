import React, { useState } from "react";
import {
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
    Tooltip,
    useToast,
} from "@chakra-ui/react";
import { keyframes } from "@emotion/react";
import { FaTrash, FaBuilding } from "react-icons/fa";
import { StarIcon, CalendarIcon, ExternalLinkIcon } from '@chakra-ui/icons';

const BookmarkNewsTable = ({ bookmarksData, loading, error, onRemoveBookmark }) => {
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 5;
    const { isOpen, onOpen, onClose } = useDisclosure();
    const [selectedNews, setSelectedNews] = useState(null);
    const toast = useToast();

    const handleRemoveBookmark = async (bookmarkId) => {
        try {
        await onRemoveBookmark(bookmarkId);
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

    const handleRowClick = (newsItem) => {
        setSelectedNews(newsItem);
        onOpen();
    };

    // Loading state
    const spin = keyframes`
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    `;

    const pulse = keyframes`
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    `;

    if (loading) {
        return (
        <Flex
            justify="center"
            align="center"
            height="400px"
            flexDirection="column"
            gap={6}
        >
            <Box position="relative" w="80px" h="80px">
            <Box
                position="absolute"
                top="0"
                left="0"
                w="100%"
                h="100%"
                borderRadius="full"
                border="4px solid"
                borderColor="transparent"
                borderTopColor="blue.400"
                animation={`${spin} 1s linear infinite`}
            />
            </Box>
            <Text
            fontSize="xl"
            fontWeight="medium"
            bgGradient="linear(to-r, blue.400, purple.500)"
            bgClip="text"
            animation={`${pulse} 1.5s ease-in-out infinite`}
            >
            Đang tải dữ liệu...
            </Text>
        </Flex>
        );
    }

    if (error) {
        return (
        <Flex justify="center" align="center" height="400px" color="red.500">
            <Text fontSize="lg">{error}</Text>
        </Flex>
        );
    }

    if (!bookmarksData || bookmarksData.length === 0) {
        return (
        <Flex justify="center" align="center" height="400px">
            <VStack spacing={4}>
            <Text fontSize="lg" color="gray.500">
                Bạn chưa lưu bài báo nào
            </Text>
            <Text fontSize="sm" color="gray.400">
                Hãy thêm bookmark vào các bài báo mà bạn quan tâm
            </Text>
            </VStack>
        </Flex>
        );
    }

    const totalPages = Math.ceil(bookmarksData.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const currentData = bookmarksData.slice(startIndex, endIndex);

    const formatPageNumber = (number) => {
        return String(number).padStart(2, "0");
    };

    return (
        <Box>
        <Box overflowX="auto">
            <Table variant="simple" width="100%" tableLayout="fixed">
            <Thead>
                <Tr bg="gray.100">
                <Th w="8%" fontSize="lg" fontWeight="bold" textTransform="none">
                    Hành động
                </Th>
                <Th w="10%" fontSize="lg" fontWeight="bold" textTransform="none">
                    Ngày
                </Th>
                <Th w="12%" fontSize="lg" fontWeight="bold" textTransform="none">
                    Ngành
                </Th>
                <Th w="30%" fontSize="lg" fontWeight="bold" textTransform="none">
                    Tiêu đề
                </Th>
                <Th w="30%" fontSize="lg" fontWeight="bold" textTransform="none">
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
                    key={row.bookmark_id || idx}
                    _hover={{ bg: "gray.50", cursor: "pointer" }}
                    height="90px"
                    minHeight="90px"
                    onClick={() => handleRowClick(row)}
                >
                    {/* Remove Button */}
                    <Td w="8%" textAlign="center">
                    <IconButton
                        icon={<FaTrash />}
                        colorScheme="red"
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveBookmark(row.bookmark_id);
                        }}
                        aria-label="Xóa bookmark"
                        _hover={{
                        bg: "red.100",
                        color: "red.600"
                        }}
                    />
                    </Td>
                    
                    {/* Date */}
                    <Td w="10%">{row.date}</Td>
                    
                    {/* Industry */}
                    <Td w="12%">
                    <Tooltip
                        label={Array.isArray(row.industry) ? row.industry.join(", ") : row.industry}
                        placement="right"
                        openDelay={300}
                    >
                        <Box cursor="pointer">
                        <Flex direction="column" gap={1} align="flex-start" color="blue.500">
                            {(Array.isArray(row.industry) ? row.industry.slice(0, 2) : [row.industry]).map((item, i) => (
                            <Text key={i} fontWeight="medium" isTruncated>
                                {item}
                            </Text>
                            ))}
                            {Array.isArray(row.industry) && row.industry.length > 2 && (
                            <Text fontSize="sm" color="gray.500">
                                +{row.industry.length - 2}
                            </Text>
                            )}
                        </Flex>
                        </Box>
                    </Tooltip>
                    </Td>
                    
                    {/* Title */}
                    <Td w="30%">
                    <Tooltip
                        label={row.news_title || row.title}
                        isDisabled={(row.news_title || row.title || "").length <= 60}
                        placement="top-start"
                    >
                        <Text fontWeight="medium" noOfLines={2}>
                        {row.news_title || row.title}
                        </Text>
                    </Tooltip>
                    </Td>
                    
                    {/* Summary */}
                    <Td w="30%">
                    <Tooltip
                        label={row.news_content || row.summary}
                        isDisabled={(row.news_content || row.summary || "").length <= 80}
                        placement="top-start"
                    >
                        <Text color="gray.600" noOfLines={2}>
                        {row.news_content || row.summary}
                        </Text>
                    </Tooltip>
                    </Td>
                    
                    {/* Influence */}
                    <Td w="10%">
                    <Tooltip
                        label={Array.isArray(row.influence) ? row.influence.join(" ") : ""}
                        placement="right"
                    >
                        <Box cursor="pointer">
                        <Flex direction="column" gap={1} align="flex-start">
                            {Array.isArray(row.influence) && row.influence.slice(0, 2).map((tag, i) => (
                            <Tag key={i} size="sm" colorScheme="blue" variant="subtle">
                                {tag}
                            </Tag>
                            ))}
                            {Array.isArray(row.influence) && row.influence.length > 2 && (
                            <Tag size="sm" colorScheme="gray" variant="subtle">
                                +{row.influence.length - 2}
                            </Tag>
                            )}
                        </Flex>
                        </Box>
                    </Tooltip>
                    </Td>
                </Tr>
                ))}
                
                {/* Empty rows for consistent height */}
                {Array(itemsPerPage - currentData.length).fill("").map((_, i) => (
                <Tr key={"empty-" + i} height="90px" minHeight="90px">
                    <Td colSpan={6} />
                </Tr>
                ))}
            </Tbody>
            </Table>
        </Box>

        {/* Pagination */}
        {totalPages > 1 && (
            <Flex justify="center" mt={4} gap={2}>
            <Button
                onClick={() => setCurrentPage(1)}
                isDisabled={currentPage === 1}
                size="sm"
            >
                Trang đầu
            </Button>
            <Button
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                isDisabled={currentPage === 1}
                size="sm"
            >
                Trang trước
            </Button>
            <Text alignSelf="center">
                Trang {formatPageNumber(currentPage)} / {formatPageNumber(totalPages)}
            </Text>
            <Button
                onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                isDisabled={currentPage === totalPages}
                size="sm"
            >
                Trang sau
            </Button>
            </Flex>
        )}

        {/* Detail Modal */}
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
                    <Heading size="xl">{selectedNews.news_title || selectedNews.title}</Heading>
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
                        <Text fontWeight="600" color="gray.600">Ngày:</Text>
                        <Text color="gray.800">{selectedNews.date}</Text>
                    </HStack>

                    <HStack spacing={2} align="center">
                        <Icon as={FaBuilding} color="green.500" boxSize={5} />
                        <Text fontWeight="600" color="gray.600">Ngành:</Text>
                        <Text color="gray.800">
                        {Array.isArray(selectedNews.industry) 
                            ? selectedNews.industry.join(", ") 
                            : selectedNews.industry}
                        </Text>
                    </HStack>

                    <HStack spacing={2} align="center">
                        <Icon as={StarIcon} color="orange.500" boxSize={5} />
                        <Text fontWeight="600" color="gray.600">Ảnh hưởng:</Text>
                        <Text color="gray.800">
                        {Array.isArray(selectedNews.influence) 
                            ? selectedNews.influence.join(", ") 
                            : selectedNews.influence}
                        </Text>
                    </HStack>
                    </Flex>

                    {/* Content */}
                    <Box w="full">
                    <Heading size="md" mb={3} color="blue.700" display="flex" alignItems="center">
                        <Box w="4px" h="22px" bg="blue.500" mr={2} borderRadius="full" />
                        Nội dung bài báo
                    </Heading>
                    <Text
                        bg="blue.50"
                        p={4}
                        borderRadius="lg"
                        borderLeft="4px solid"
                        borderColor="blue.500"
                        color="gray.700"
                        lineHeight="tall"
                    >
                        {selectedNews.news_content || selectedNews.summary || "Không có nội dung"}
                    </Text>
                    </Box>

                    {/* Link if available */}
                    {(selectedNews.link || selectedNews.source) && (
                    <Box w="full">
                        <Heading size="md" mb={3} color="blue.700" display="flex" alignItems="center">
                        <Box w="4px" h="22px" bg="blue.500" mr={2} borderRadius="full" />
                        Nguồn
                        </Heading>
                        <Box bg="gray.50" p={4} borderRadius="lg">
                        <Link
                            href={selectedNews.link || selectedNews.source}
                            isExternal
                            color="blue.500"
                            fontWeight="600"
                            _hover={{ textDecoration: "underline", color: "blue.600" }}
                        >
                            <HStack align="center">
                            <ExternalLinkIcon mr={2} />
                            <Text>{selectedNews.source || "Xem bài báo gốc"}</Text>
                            </HStack>
                        </Link>
                        </Box>
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

export default BookmarkNewsTable;
