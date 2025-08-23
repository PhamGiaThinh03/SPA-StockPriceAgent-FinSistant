import React, { useState, useEffect } from "react";
import {
    Box,
    Button,
    Alert,
    AlertIcon,
    SimpleGrid,
    Text,
    Center,
    Spinner,
    VStack,
    HStack,
    useColorModeValue,
    Flex,
    Switch,
} from "@chakra-ui/react";
import PriceChart from "../components/stocks/PriceChart";
import { useStockData } from "../hooks/useApi";

// Định nghĩa các hằng số để dễ quản lý
const tickers = ["FPT", "IMP", "VCB", "GAS"];
const timeRanges = [
    { key: "all", label: "Tất cả" },
    { key: "1M", label: "1 Tháng" },
    { key: "3M", label: "3 Tháng" },
    { key: "1Y", label: "1 Năm" },
    { key: "5Y", label: "5 Năm" },
];

const StockAnalysisPage = () => {
    // State cho các bộ lọc
    const [selectedTicker, setSelectedTicker] = useState("FPT");
    const [selectedTimeRange, setSelectedTimeRange] = useState("1M");
    const [showPrediction, setShowPrediction] = useState(false);

    // Color scheme cho theme
    const bgFilter = useColorModeValue("white", "gray.800");
    const borderColor = useColorModeValue("gray.200", "gray.600");
    const shadowColor = useColorModeValue("sm", "dark-lg");

    // Sử dụng custom hook
    const {
        stockData,
        loading: isLoading,
        error,
    } = useStockData(selectedTicker, selectedTimeRange);

    // State cho dữ liệu chart được xử lý
    const [chartData, setChartData] = useState(null);

    // Xử lý dữ liệu cho chart khi stockData thay đổi
    useEffect(() => {
        if (stockData && stockData.length > 0) {
        // TẠO BẢN SAO VÀ SẮP XẾP DỮ LIỆU
        const sortedData = [...stockData].sort(
            (a, b) => new Date(a.date) - new Date(b.date)
        );

        // Sử dụng dữ liệu đã được sắp xếp (sortedData) để cập nhật state
        setChartData({
            rawData: sortedData,
            labels: sortedData.map((item) => item.date),
            datasets: [
            {
                label: `Giá đóng cửa của ${selectedTicker}`,
                data: sortedData.map((item) => item.close_price),
            },
            ],
        });
        } else {
        setChartData(null);
        }
    }, [stockData, selectedTicker]);

    const renderContent = () => {
        if (isLoading) {
        return (
            <Center minH="400px">
            <Spinner size="xl" />
            </Center>
        );
        }
        if (error) {
        return (
            <Alert status="error" mt={4}>
            <AlertIcon />
            {error}
            </Alert>
        );
        }
        if (chartData) {
        return <PriceChart chartData={chartData} timeRange={selectedTimeRange} showPrediction={showPrediction} />;
        }
        return (
        <Center minH="400px">
            <Text>Không có dữ liệu biểu đồ để hiển thị.</Text>
        </Center>
        );
    };

    return (
        <Box>
        {/* Container cho các filter */}
        <Box
            bg={bgFilter}
            borderRadius="xl"
            border="1px"
            borderColor={borderColor}
            shadow={shadowColor}
            p={6}
            mb={8}
        >
            <VStack spacing={6} align="stretch">
            {/* Nhóm nút chọn Công ty */}
            <Box>
                <Text fontSize="sm" fontWeight="semibold" color="gray.600" mb={3}>
                Chọn cổ phiếu
                </Text>
                <Flex wrap="wrap" gap={3}>
                {tickers.map((ticker) => (
                    <Button
                    key={ticker}
                    size="md"
                    variant={selectedTicker === ticker ? "solid" : "outline"}
                    colorScheme={selectedTicker === ticker ? "blue" : "gray"}
                    borderRadius="lg"
                    px={6}
                    py={3}
                    onClick={() => setSelectedTicker(ticker)}
                    >
                    {ticker}
                    </Button>
                ))}
                </Flex>
            </Box>

            {/* Nhóm nút chọn Khung thời gian */}
            <Box>
                <Text fontSize="sm" fontWeight="semibold" color="gray.600" mb={3}>
                Khung thời gian
                </Text>
                <VStack spacing={3} align="stretch">
                <HStack spacing={2} wrap="wrap">
                    {timeRanges.map((range) => (
                    <Button
                        key={range.key}
                        size="sm"
                        variant={selectedTimeRange === range.key ? "solid" : "ghost"}
                        colorScheme={
                        selectedTimeRange === range.key ? "teal" : "gray"
                        }
                        borderRadius="full"
                        px={4}
                        py={2}
                        onClick={() => setSelectedTimeRange(range.key)}
                    >
                        {range.label}
                    </Button>
                    ))}
                </HStack>
                
                {/* Button toggle prediction cho 1M và 3M */}
                {(selectedTimeRange === "1M" || selectedTimeRange === "3M") && (
                    <HStack spacing={2}>
                    <Text fontSize="sm" color="gray.600">
                        Hiển thị dự đoán:
                    </Text>
                    <Switch
                        colorScheme="teal"
                        isChecked={showPrediction}
                        onChange={(e) => setShowPrediction(e.target.checked)}
                    />
                    </HStack>
                )}
                </VStack>
            </Box>
            </VStack>
        </Box>

        <SimpleGrid columns={{ base: 1 }} spacing={6}>
            {renderContent()}
        </SimpleGrid>
        </Box>
    );
};

export default StockAnalysisPage;
