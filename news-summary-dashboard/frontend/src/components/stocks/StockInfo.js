import React from "react";
import {
    Box,
    Heading,
    Text,
    Flex,
    Tag,
    Spinner,
    Stat,
    StatNumber,
    StatHelpText,
    StatArrow,
    useColorModeValue,
} from "@chakra-ui/react";

const StockInfo = ({ quote, profile, isLoading }) => {
    const cardBg = useColorModeValue("white", "gray.700");

    if (isLoading) {
        return (
        <Box p={5} shadow="md" borderWidth="1px" borderRadius="md" bg={cardBg}>
            <Spinner />
        </Box>
        );
    }

    if (!quote || !profile) {
        return (
        <Box p={5} shadow="md" borderWidth="1px" borderRadius="md" bg={cardBg}>
            <Text>Không có dữ liệu. Vui lòng chọn một mã cổ phiếu.</Text>
        </Box>
        );
    }

    const isPositive = quote.d > 0;

    return (
        <Box p={5} shadow="md" borderWidth="1px" borderRadius="md" bg={cardBg}>
        <Flex align="center" justify="space-between">
            <Box>
            <Heading size="lg">{profile.ticker}</Heading>
            <Text fontSize="md" color="gray.500">
                {profile.name}
            </Text>
            </Box>
            <Tag colorScheme="blue" size="lg">
            {profile.finnhubIndustry}
            </Tag>
        </Flex>
        <Stat mt={4}>
            <StatNumber fontSize="3xl">${quote.c?.toFixed(2)}</StatNumber>
            <StatHelpText fontSize="md">
            <StatArrow type={isPositive ? "increase" : "decrease"} />
            {quote.d?.toFixed(2)} ({quote.dp?.toFixed(2)}%)
            </StatHelpText>
        </Stat>
        </Box>
    );
};

export default StockInfo;
