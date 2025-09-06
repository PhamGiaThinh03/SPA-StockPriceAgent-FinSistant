import React, { useState, useEffect } from "react";
import {
  Box,
  Heading,
  Select,
  Input,
  Button,
  FormControl,
  FormLabel,
  useColorModeValue,
  Container,
  Flex,
  ButtonGroup
} from "@chakra-ui/react";
import NewsTable from "../components/dashboard/NewsTable";
import { useDashboardNews } from "../hooks/useApi";

const industries = ["Công nghệ", "Sức khỏe", "Tài chính", "Năng lượng", "Khác"];
const companies = ["FPT", "VCB", "IMP", "GAS"];

const DEFAULT_INDUSTRY = "";
const DEFAULT_COMPANY = "";
const DEFAULT_DATE = "";
const DEFAULT_SENTIMENT = "";

const DashboardPage = () => {
  // State for filters
  const [industry, setIndustry] = useState(DEFAULT_INDUSTRY);
  const [company, setCompany] = useState(DEFAULT_COMPANY);
  const [date, setDate] = useState(DEFAULT_DATE);
  const [sentiment, setSentiment] = useState(DEFAULT_SENTIMENT);

  // Use custom hook instead of duplicate logic
  const { news: newsData, loading, error, pagination, fetchNews } = useDashboardNews();
  
  // State for pagination settings
  const [itemsPerPage, setItemsPerPage] = useState(5);
  // =======================================================
  // --- NEW EVENT HANDLER FUNCTIONS ---
  const handleIndustryChange = (e) => {
    const newIndustry = e.target.value;
    setIndustry(newIndustry);
    // If the user selects a specific industry, reset the company filter
    if (newIndustry) {
      setCompany(DEFAULT_COMPANY);
    }
  };

  const handleCompanyChange = (e) => {
    const newCompany = e.target.value;
    setCompany(newCompany);
    // If the user selects a specific company, reset the industry filter
    if (newCompany) {
      setIndustry(DEFAULT_INDUSTRY);
    }
  };

  // Use hook instead of duplicate logic
  const handleApplyFilters = async () => {
    fetchNews({ industry, company, sentiment, date }, { page: 1, limit: itemsPerPage });
  };

  // Automatically call API when the page first loads
  useEffect(() => {
    fetchNews({ industry: "", company: "", sentiment: "", date: "" }, { page: 1, limit: 5 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Handle items per page change
  useEffect(() => {
    if (itemsPerPage !== 5) { // Only if changed from default
      fetchNews({ industry, company, sentiment, date }, { page: 1, limit: itemsPerPage });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemsPerPage]); // Only when itemsPerPage changes

  const handleReset = () => {
    setIndustry(DEFAULT_INDUSTRY);
    setCompany(DEFAULT_COMPANY);
    setDate(DEFAULT_DATE);
    setSentiment(DEFAULT_SENTIMENT);
    fetchNews({
      industry: DEFAULT_INDUSTRY,
      company: DEFAULT_COMPANY,
      sentiment: DEFAULT_SENTIMENT,
      date: DEFAULT_DATE,
    }, { page: 1, limit: itemsPerPage });
  };


  // Handle page changes
  const handlePageChange = (newPage) => {
    fetchNews({ industry, company, sentiment, date }, { page: newPage, limit: itemsPerPage });
  };

  const handleSentimentChange = (newSentiment) => {
    // If the clicked sentiment is the same as the current sentiment, cancel it
    if (sentiment === newSentiment) {
      setSentiment(""); // Reset to empty to cancel the filter
    } else {
      // Otherwise, set the new sentiment
      setSentiment(newSentiment);
    }
  };

  const bgColor = useColorModeValue("white", "gray.800");

  return (
    <Box
      borderRadius="3xl"
      boxShadow="xl"
      bg={bgColor}
      maxW="container.2xl"
      w="100%"
      mx="auto"
      px={[2, 4, 8]}
      py={6}
    >
      <Heading
        size="2xl"
        fontWeight="extrabold"
        color="gray.800"
        letterSpacing="tight"
        mb={8}
      >
        Tin tức tổng hợp
      </Heading>

      <Flex direction={{ base: "column", lg: "row" }} gap={6}>
        {/* Filters */}
        <Box p={6} bg={bgColor} borderRadius="lg" borderWidth="1px" w="full">
          <Container maxW="full" px={0} mb={10}>
            <Flex w="100%" align="flex-end" gap={2}>
              {/*-----------------Industry-----------------*/}
              <FormControl minW="220px" maxW="220px">
                <FormLabel fontSize="lg" mb={1}>
                  Ngành
                </FormLabel>
                <Select
                  value={industry}
                  // onChange={(e) => setIndustry(e.target.value)}
                  onChange={handleIndustryChange}
                  bg="white"
                  borderRadius="md"
                  fontWeight="semibold"
                  size="sm"
                  h="40px"
                  minH="40px"
                  maxH="40px"
                  placeholder="Tất cả"
                >
                  {industries.map((ind) => (
                    <option value={ind} key={ind}>
                      {ind}
                    </option>
                  ))}
                </Select>
              </FormControl>
              {/*-----------------Company-----------------*/}
              <FormControl minW="220px" maxW="220px">
                <FormLabel fontSize="lg" mb={1}>
                  Công ty
                </FormLabel>
                <Select
                  value={company}
                  // onChange={(e) => setCompany(e.target.value)}
                  onChange={handleCompanyChange}
                  bg="white"
                  borderRadius="md"
                  fontWeight="semibold"
                  size="sm"
                  h="40px"
                  minH="40px"
                  maxH="40px"
                  placeholder="Tất cả"
                >
                  {companies.map((ind) => (
                    <option value={ind} key={ind}>
                      {ind}
                    </option>
                  ))}
                </Select>
              </FormControl>
              {/*-----------------Date Range-----------------*/}
              <FormControl minW="220px" maxW="220px">
                <FormLabel fontSize="lg" mb={1}>
                  Ngày
                </FormLabel>
                <Input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  bg="white"
                  borderRadius="md"
                  size="sm"
                  h="40px"
                  minH="40px"
                  maxH="40px"
                />
              </FormControl>

              {/*-----------------Influence-----------------*/}
              <FormControl minW="280px" maxW="280px">
                <FormLabel fontSize="lg" mb={1}>
                  Ảnh hưởng
                </FormLabel>
                <ButtonGroup variant="outline" isAttached size="sm" h="40px">
                  {/* --- FIX onClick FOR BUTTONS --- */}
                  <Button
                    onClick={() => handleSentimentChange("Positive")}
                    isActive={sentiment === "Positive"}
                    _active={{ bg: "blue.500", color: "white" }}
                    minW="90px"
                    h="40px"
                  >
                    Tích cực
                  </Button>
                  <Button
                    onClick={() => handleSentimentChange("Negative")}
                    isActive={sentiment === "Negative"}
                    _active={{ bg: "blue.500", color: "white" }}
                    minW="90px"
                    h="40px"
                  >
                    Tiêu cực
                  </Button>
                  <Button
                    onClick={() => handleSentimentChange("Neutral")}
                    isActive={sentiment === "Neutral"}
                    _active={{ bg: "blue.500", color: "white" }}
                    minW="90px"
                    h="40px"
                  >
                    Trung tính
                  </Button>
                </ButtonGroup>
              </FormControl>
              {/* -----------------Search-----------------
              <FormControl minW="220px" maxW="300px">
                <FormLabel fontSize="sm" mb={1} color="transparent">
                  Search
                </FormLabel>
                <Input
                  placeholder="Search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  bg="white"
                  borderRadius="md"
                  size="sm"
                  h="40px"
                  minH="40px"
                  maxH="40px"
                />
              </FormControl> */}
              <Button
                colorScheme="blue"
                minW="90px"
                h="40px"
                fontWeight="bold"
                fontSize="md"
                bgGradient="linear(to-r, blue.500, blue.600)"
                transition="all 0.2s cubic-bezier(.08,.52,.52,1)"
                boxShadow="sm"
                _hover={{
                  bgGradient: "linear(to-r, blue.600, blue.500)",
                  boxShadow: "md",
                  transform: "translateY(-2px) scale(1.04)",
                }}
                _active={{ transform: "scale(0.96)", boxShadow: "xs" }}
                onClick={handleApplyFilters}
              >
                Áp dụng
              </Button>
              <Button
                variant="outline"
                minW="90px"
                h="40px"
                fontWeight="bold"
                fontSize="md"
                color="gray.700"
                borderColor="gray.200"
                transition="all 0.2s cubic-bezier(.08,.52,.52,1)"
                boxShadow="sm"
                _hover={{
                  bg: "gray.50",
                  borderColor: "gray.300",
                  boxShadow: "md",
                  transform: "translateY(-2px) scale(1.04)",
                }}
                _active={{ transform: "scale(0.96)", boxShadow: "xs" }}
                onClick={handleReset}
              >
                Đặt lại
              </Button>
              
              {/* Items per page selector */}
              <FormControl minW="120px" maxW="120px">
                <FormLabel fontSize="lg" mb={1}>
                  Rows
                </FormLabel>
                <Select
                  value={itemsPerPage}
                  onChange={(e) => setItemsPerPage(Number(e.target.value))}
                  bg="white"
                  borderRadius="md"
                  fontWeight="semibold"
                  size="sm"
                  h="40px"
                  minH="40px"
                  maxH="40px"
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </Select>
              </FormControl>
            </Flex>
          </Container>
          {/* News Table */}
          <NewsTable 
            newsData={newsData} 
            loading={loading} 
            error={error} 
            pagination={pagination}
            onPageChange={handlePageChange}
          />
        </Box>

        {/* --- Right column (Charts) --- */}
        {/* <VStack spacing={6} flex={{ base: "none", lg: 1 }} w="full">
          <IndustryDistributionChart />
          <InfluenceTrendsChart />
        </VStack> */}
      </Flex>
    </Box>
  );
};

export default DashboardPage; 
