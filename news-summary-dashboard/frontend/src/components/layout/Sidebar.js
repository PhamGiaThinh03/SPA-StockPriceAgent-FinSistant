import React from "react";
import logoImage from "../../assets/icon_logo.png";
import {
  Box,
  HStack,
  Text,
  Icon,
  List,
  ListItem,
  useColorModeValue,
  Image,
} from "@chakra-ui/react";
import { NavLink } from "react-router-dom";
import {
  FiHome,
  FiBarChart2,
  FiBookmark,
  FiSettings,
  FiHelpCircle,
} from "react-icons/fi";

const Sidebar = ({ onQuickFilterClick }) => {
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const iconColor = "blue.500";
  const activeIconColor = useColorModeValue("blue.600", "blue.200");
  const activeTextColor = useColorModeValue("blue.700", "white");
  const normalTextColor = useColorModeValue("gray.700", "gray.200");
  const activeBgColor = useColorModeValue("blue.100", "blue.600");

  // NavLink sẽ tự động áp dụng style này khi URL khớp
  const activeLinkStyle = {
    textDecoration: "none",
  };

  return (
    <Box
      w="240px"
      minH="100vh"
      bg={bgColor}
      borderRight="1px"
      borderColor={borderColor}
      display="flex"
      flexDirection="column"
      py={2}
    >
      <HStack px={6} mb={6}>
        <Image 
          src={logoImage} 
          alt="FINsistant Logo" 
          boxSize="32px"
          objectFit="contain"
          fallback={
            <Box 
              boxSize="32px" 
              bg="blue.500" 
              borderRadius="md" 
              display="flex" 
              alignItems="center" 
              justifyContent="center"
            >
              <Text color="white" fontSize="lg" fontWeight="bold">F</Text>
            </Box>
          }
          onError={(e) => {
            console.log('Sidebar image failed to load:', e);
          }}
        />
        <Text fontSize="xl" fontWeight="bold" color="gray.700">
          FINsistant
        </Text>
      </HStack>

      <List spacing={1} px={4}>
        <ListItem>
          <NavLink
            to="/"
            style={({ isActive }) => (isActive ? activeLinkStyle : undefined)}
          >
            {({ isActive }) => (
              <HStack 
                px={4} 
                py={3} 
                cursor="pointer" 
                _hover={{ bg: isActive ? undefined : "gray.50" }}
                bg={isActive ? activeBgColor : "transparent"}
                borderRadius="md"
                fontWeight={isActive ? "bold" : "normal"}
              >
                <Icon 
                  as={FiHome} 
                  w={5} 
                  h={5} 
                  color={isActive ? activeIconColor : iconColor} 
                />
                <Text color={isActive ? activeTextColor : normalTextColor}>
                  Bảng tin
                </Text>
              </HStack>
            )}
          </NavLink>
        </ListItem>
        <ListItem>
          <NavLink
            to="/analytics"
            style={({ isActive }) => (isActive ? activeLinkStyle : undefined)}
          >
            {({ isActive }) => (
              <HStack 
                px={4} 
                py={3} 
                cursor="pointer" 
                _hover={{ bg: isActive ? undefined : "gray.50" }}
                bg={isActive ? activeBgColor : "transparent"}
                borderRadius="md"
                fontWeight={isActive ? "bold" : "normal"}
              >
                <Icon 
                  as={FiBarChart2} 
                  w={5} 
                  h={5} 
                  color={isActive ? activeIconColor : iconColor} 
                />
                <Text color={isActive ? activeTextColor : normalTextColor}>
                  Phân tích
                </Text>
              </HStack>
            )}
          </NavLink>
        </ListItem>
        <ListItem>
          <NavLink
            to="/saved-articles"
            style={({ isActive }) => (isActive ? activeLinkStyle : undefined)}
          >
            {({ isActive }) => (
              <HStack 
                px={4} 
                py={3} 
                cursor="pointer" 
                _hover={{ bg: isActive ? undefined : "gray.50" }}
                bg={isActive ? activeBgColor : "transparent"}
                borderRadius="md"
                fontWeight={isActive ? "bold" : "normal"}
              >
                <Icon 
                  as={FiBookmark} 
                  w={5} 
                  h={5} 
                  color={isActive ? activeIconColor : iconColor} 
                />
                <Text color={isActive ? activeTextColor : normalTextColor}>
                  Đã lưu
                </Text>
              </HStack>
            )}
          </NavLink>
        </ListItem>
        <ListItem>
          <NavLink
            to="/settings"
            style={({ isActive }) => (isActive ? activeLinkStyle : undefined)}
          >
            {({ isActive }) => (
              <HStack 
                px={4} 
                py={3} 
                cursor="pointer" 
                _hover={{ bg: isActive ? undefined : "gray.50" }}
                bg={isActive ? activeBgColor : "transparent"}
                borderRadius="md"
                fontWeight={isActive ? "bold" : "normal"}
              >
                <Icon 
                  as={FiSettings} 
                  w={5} 
                  h={5} 
                  color={isActive ? activeIconColor : iconColor} 
                />
                <Text color={isActive ? activeTextColor : normalTextColor}>
                  Cài đặt
                </Text>
              </HStack>
            )}
          </NavLink>
        </ListItem>
      </List>

      {/* --- Phần Help giữ nguyên --- */}
      <List px={4}>
        <ListItem>
          <HStack px={4} py={3} cursor="pointer" _hover={{ bg: "gray.50" }}>
            <Icon as={FiHelpCircle} w={5} h={5} color={iconColor} />
            <Text>Trợ giúp</Text>
          </HStack>
        </ListItem>
      </List>
    </Box>
  );
};

export default Sidebar;
