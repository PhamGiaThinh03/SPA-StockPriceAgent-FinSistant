import React from "react";
import { HStack, IconButton, Avatar } from "@chakra-ui/react";
import { FiSettings } from "react-icons/fi";

const TopbarIcons = () => (
  <HStack spacing={2}>
    <IconButton
      aria-label="User profile"
      icon={
        <Avatar
          size="sm"
          bg="blue.100"
          color="blue.500"
          fontWeight="bold"
        >
          U
        </Avatar>
      }
      variant="ghost"
      bg="gray.50"
      _hover={{ bg: "gray.100" }}
    />
    <IconButton
      aria-label="Settings"
      icon={<FiSettings />}
      variant="ghost"
      bg="gray.50"
      _hover={{ bg: "gray.100" }}
      color="blue.500"
      fontSize="xl"
    />
  </HStack>
);

export default TopbarIcons; 