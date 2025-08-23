import React from "react";
import {
  Box,
  Heading,
  VStack,
  HStack,
  Text,
  useColorModeValue
} from "@chakra-ui/react";

const IndustryDistributionChart = () => {
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const textColor = useColorModeValue("gray.600", "gray.400");

  const bars = [
    { value: 62, label: "Tech", color: "blue.400" },
    { value: 45, label: "Health", color: "green.400" },
    { value: 81, label: "Finance", color: "purple.400" },
    { value: 48, label: "Energy", color: "orange.400" }
  ];

  const maxValue = Math.max(...bars.map(bar => bar.value));

  return (
    <Box
      p={6}
      bg={bgColor}
      borderRadius="lg"
      borderWidth="1px"
      borderColor={borderColor}
      flex="1"
      position="relative"
    >
      <Heading size="md" mb={6}>Industry News Distribution</Heading>
      
      {/* Y-axis labels */}
      <Box position="absolute" left={6} top={12} bottom={6} width="30px">
        {[100, 75, 50, 25, 0].map((value, i) => (
          <Text
            key={i}
            position="absolute"
            right="100%"
            top={`${(100 - value) * 0.7}%`}
            fontSize="xs"
            color={textColor}
            mr={2}
          >
            {value}
          </Text>
        ))}
      </Box>

      <HStack spacing={4} h="180px" align="flex-end" pl={8}>
        {bars.map((bar, index) => (
          <VStack key={index} flex="1" spacing={2} h="full" justify="flex-end">
            <Box
              w="full"
              h={`${(bar.value / maxValue) * 100}%`}
              bg={bar.color}
              borderRadius="md"
              position="relative"
              transition="all 0.3s"
              _hover={{
                transform: "scaleY(1.05)",
                filter: "brightness(1.1)",
                cursor: "pointer"
              }}
            >
              <Text
                position="absolute"
                top="-25px"
                left="50%"
                transform="translateX(-50%)"
                fontSize="sm"
                fontWeight="bold"
                color={textColor}
              >
                {bar.value}
              </Text>
            </Box>
            <Text fontSize="sm" color={textColor} fontWeight="medium">
              {bar.label}
            </Text>
          </VStack>
        ))}
      </HStack>
    </Box>
  );
};

export default IndustryDistributionChart; 