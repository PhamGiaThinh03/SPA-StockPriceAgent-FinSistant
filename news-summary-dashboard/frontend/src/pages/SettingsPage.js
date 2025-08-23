import React, { useState, useEffect } from "react";
import { supabase } from "../services/supabaseClient";
import {
    Box,
    Heading,
    VStack,
    Tabs,
    TabList,
    TabPanels,
    Tab,
    TabPanel,
    FormControl,
    FormLabel,
    Input,
    Button,
    useToast,
    Text,
    Switch,
    Checkbox,
    CheckboxGroup,
    Avatar,
    useColorModeValue,
    Card,
    CardBody,
    CardHeader,
    Flex,
    Icon,
    SimpleGrid,
    Container,
} from "@chakra-ui/react";
import { 
    FiUser, 
    FiBell, 
    FiSettings, 
    FiShield, 
    FiCamera,
    FiMail,
    FiLock,
    FiTrash2,
    FiLogOut,
    FiSave
} from "react-icons/fi";
import { useNavigate } from "react-router-dom";

const industries = ["Công nghệ", "Sức khỏe", "Tài chính", "Năng lượng", "Khác"];

const SettingsPage = () => {
    const toast = useToast();
    const navigate = useNavigate();

    // Theme colors
    const cardBg = useColorModeValue("white", "gray.800");
    const borderColor = useColorModeValue("gray.200", "gray.600");

    // Profile States
    const [fullName, setFullName] = useState("");
    const [avatarUrl, setAvatarUrl] = useState(null);
    const [email, setEmail] = useState("");

    // Notification States
    const [notificationsEnabled, setNotificationsEnabled] = useState(true);
    const [interestedIndustries, setInterestedIndustries] = useState([]);

    // Password States
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    useEffect(() => {
        const fetchProfile = async () => {
        const {
            data: { user },
        } = await supabase.auth.getUser();

        if (user) {
            setEmail(user.email);
            const { data, error } = await supabase
            .from("profiles")
            .select("full_name, avatar_url, notification_preferences")
            .eq("id", user.id)
            .single();

            if (error) {
            console.error("Error fetching profile:", error);
            } else if (data) {
            setFullName(data.full_name || "");
            setAvatarUrl(data.avatar_url);
            // Giả sử notification_preferences có dạng { industries: ["Công nghệ", ...] }
            setInterestedIndustries(
                data.notification_preferences?.industries || []
            );
            }
        }
        };

        fetchProfile();
    }, []);

    const handleUpdateProfile = async () => {
        const {
        data: { user },
        } = await supabase.auth.getUser();
        if (!user) return;

        const updates = {
        id: user.id,
        full_name: fullName,
        notification_preferences: { industries: interestedIndustries },
        updated_at: new Date(),
        };

        const { error } = await supabase.from("profiles").upsert(updates);

        if (error) {
        toast({
            title: "Lỗi cập nhật hồ sơ",
            description: error.message,
            status: "error",
        });
        } else {
        toast({ title: "Hồ sơ đã được cập nhật!", status: "success" });
        }
    };

    const handlePasswordChange = async () => {
        if (password !== confirmPassword) {
        toast({ title: "Mật khẩu không khớp", status: "error" });
        return;
        }
        if (password.length < 6) {
        toast({ title: "Mật khẩu phải có ít nhất 6 ký tự", status: "warning" });
        return;
        }

        const { error } = await supabase.auth.updateUser({ password: password });
        if (error) {
        toast({
            title: "Lỗi đổi mật khẩu",
            description: error.message,
            status: "error",
        });
        } else {
        toast({ title: "Đổi mật khẩu thành công!", status: "success" });
        setPassword("");
        setConfirmPassword("");
        }
    };

    const handleSignOut = async () => {
        await supabase.auth.signOut();
        navigate("/auth");
    };

    return (
        <Container maxW="6xl" py={8}>
            <VStack spacing={8} align="stretch">
                {/* Header */}
                <Box textAlign="center">
                    <Heading size="xl" mb={2}>
                        Cài đặt tài khoản
                    </Heading>
                    <Text color="gray.600">
                        Quản lý thông tin cá nhân và cài đặt ứng dụng
                    </Text>
                </Box>

                {/* Tabs với design mới */}
                <Tabs variant="unstyled" colorScheme="blue" isFitted>
                    <TabList 
                        bg={cardBg} 
                        borderRadius="xl" 
                        p={1.5} 
                        shadow="sm"
                        border="1px"
                        borderColor={borderColor}
                    >
                        <Tab 
                            borderRadius="lg" 
                            fontWeight="semibold"
                            _selected={{ 
                                bg: "blue.500", 
                                color: "white",
                                shadow: "md"
                            }}
                            transition="all 0.3s"
                        >
                            <Icon as={FiUser} mr={2} />
                            Hồ sơ
                        </Tab>
                        <Tab 
                            borderRadius="lg" 
                            fontWeight="semibold"
                            _selected={{ 
                                bg: "blue.500", 
                                color: "white",
                                shadow: "md"
                            }}
                            transition="all 0.3s"
                        >
                            <Icon as={FiBell} mr={2} />
                            Thông báo
                        </Tab>
                        <Tab 
                            borderRadius="lg" 
                            fontWeight="semibold"
                            _selected={{ 
                                bg: "blue.500", 
                                color: "white",
                                shadow: "md"
                            }}
                            transition="all 0.3s"
                        >
                            <Icon as={FiShield} mr={2} />
                            Bảo mật
                        </Tab>
                    </TabList>

                    <TabPanels mt={6}>
                        {/* Profile Panel */}
                        <TabPanel p={0}>
                            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
                                {/* Profile Info Card */}
                                <Card bg={cardBg} shadow="sm" borderColor={borderColor}>
                                    <CardHeader>
                                        <Flex align="center">
                                            <Icon as={FiUser} color="blue.500" mr={3} />
                                            <Heading size="md">Thông tin cá nhân</Heading>
                                        </Flex>
                                    </CardHeader>
                                    <CardBody>
                                        <VStack spacing={6}>
                                            <Flex direction="column" align="center">
                                                <Avatar 
                                                    size="2xl" 
                                                    name={fullName} 
                                                    src={avatarUrl}
                                                    shadow="lg"
                                                    border="4px solid"
                                                    borderColor="blue.100"
                                                />
                                                <Button 
                                                    size="sm" 
                                                    mt={4}
                                                    leftIcon={<Icon as={FiCamera} />}
                                                    variant="outline"
                                                    colorScheme="blue"
                                                >
                                                    Đổi ảnh đại diện
                                                </Button>
                                            </Flex>
                                            
                                            <VStack spacing={4} w="full">
                                                <FormControl>
                                                    <FormLabel fontWeight="semibold">
                                                        <Icon as={FiUser} mr={2} />
                                                        Tên đầy đủ
                                                    </FormLabel>
                                                    <Input
                                                        value={fullName}
                                                        onChange={(e) => setFullName(e.target.value)}
                                                        bg={useColorModeValue("white", "gray.700")}
                                                        borderColor={borderColor}
                                                        _focus={{ borderColor: "blue.500", shadow: "md" }}
                                                    />
                                                </FormControl>
                                                
                                                <FormControl>
                                                    <FormLabel fontWeight="semibold">
                                                        <Icon as={FiMail} mr={2} />
                                                        Email
                                                    </FormLabel>
                                                    <Input 
                                                        value={email} 
                                                        isReadOnly 
                                                        bg="gray.100"
                                                        _dark={{ bg: "gray.700" }}
                                                    />
                                                </FormControl>
                                                
                                                <Button 
                                                    colorScheme="blue" 
                                                    w="full"
                                                    leftIcon={<Icon as={FiSave} />}
                                                    onClick={handleUpdateProfile}
                                                >
                                                    Lưu thay đổi
                                                </Button>
                                            </VStack>
                                        </VStack>
                                    </CardBody>
                                </Card>

                                {/* Password Card */}
                                <Card bg={cardBg} shadow="sm" borderColor={borderColor}>
                                    <CardHeader>
                                        <Flex align="center">
                                            <Icon as={FiLock} color="orange.500" mr={3} />
                                            <Heading size="md">Đổi mật khẩu</Heading>
                                        </Flex>
                                    </CardHeader>
                                    <CardBody>
                                        <VStack spacing={4}>
                                            <FormControl>
                                                <FormLabel fontWeight="semibold">Mật khẩu mới</FormLabel>
                                                <Input
                                                    type="password"
                                                    value={password}
                                                    onChange={(e) => setPassword(e.target.value)}
                                                    bg={useColorModeValue("white", "gray.700")}
                                                    borderColor={borderColor}
                                                    _focus={{ borderColor: "orange.500", shadow: "md" }}
                                                />
                                            </FormControl>
                                            
                                            <FormControl>
                                                <FormLabel fontWeight="semibold">Xác nhận mật khẩu mới</FormLabel>
                                                <Input
                                                    type="password"
                                                    value={confirmPassword}
                                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                                    bg={useColorModeValue("white", "gray.700")}
                                                    borderColor={borderColor}
                                                    _focus={{ borderColor: "orange.500", shadow: "md" }}
                                                />
                                            </FormControl>
                                            
                                            <Button 
                                                onClick={handlePasswordChange} 
                                                colorScheme="orange"
                                                w="full"
                                                leftIcon={<Icon as={FiLock} />}
                                            >
                                                Đổi mật khẩu
                                            </Button>
                                        </VStack>
                                    </CardBody>
                                </Card>
                            </SimpleGrid>
                        </TabPanel>

                        {/* Notifications Panel */}
                        <TabPanel p={0}>
                            <Card bg={cardBg} shadow="sm" borderColor={borderColor}>
                                <CardHeader>
                                    <Flex align="center">
                                        <Icon as={FiBell} color="green.500" mr={3} />
                                        <Heading size="md">Cài đặt thông báo</Heading>
                                    </Flex>
                                </CardHeader>
                                <CardBody>
                                    <VStack spacing={6} align="stretch">
                                        <Flex 
                                            justify="space-between" 
                                            align="center"
                                            p={4}
                                            bg={useColorModeValue("green.50", "green.900")}
                                            borderRadius="lg"
                                            border="1px"
                                            borderColor="green.200"
                                        >
                                            <Box>
                                                <Text fontWeight="semibold">Thông báo qua Email</Text>
                                                <Text fontSize="sm" color="gray.600">
                                                    Nhận cập nhật tin tức và phân tích qua email
                                                </Text>
                                            </Box>
                                            <Switch
                                                size="lg"
                                                colorScheme="green"
                                                isChecked={notificationsEnabled}
                                                onChange={(e) => setNotificationsEnabled(e.target.checked)}
                                            />
                                        </Flex>
                                        
                                        <Box>
                                            <Text fontWeight="semibold" mb={3}>
                                                Nhận thông báo cho các ngành:
                                            </Text>
                                            <CheckboxGroup
                                                colorScheme="blue"
                                                value={interestedIndustries}
                                                onChange={setInterestedIndustries}
                                            >
                                                <SimpleGrid columns={2} spacing={3}>
                                                    {industries.map((industry) => (
                                                        <Checkbox 
                                                            key={industry} 
                                                            value={industry}
                                                            p={3}
                                                            borderRadius="md"
                                                            _checked={{
                                                                bg: "blue.50",
                                                                borderColor: "blue.500"
                                                            }}
                                                        >
                                                            {industry}
                                                        </Checkbox>
                                                    ))}
                                                </SimpleGrid>
                                            </CheckboxGroup>
                                        </Box>
                                        
                                        <Button 
                                            onClick={handleUpdateProfile} 
                                            colorScheme="green"
                                            leftIcon={<Icon as={FiSave} />}
                                        >
                                            Lưu cài đặt thông báo
                                        </Button>
                                    </VStack>
                                </CardBody>
                            </Card>
                        </TabPanel>

                        {/* Security Panel */}
                        <TabPanel p={0}>
                            <VStack spacing={6}>
                                {/* Account Actions */}
                                <Card bg={cardBg} shadow="sm" borderColor={borderColor} w="full">
                                    <CardHeader>
                                        <Flex align="center">
                                            <Icon as={FiSettings} color="gray.500" mr={3} />
                                            <Heading size="md">Quản lý tài khoản</Heading>
                                        </Flex>
                                    </CardHeader>
                                    <CardBody>
                                        <Button 
                                            onClick={handleSignOut} 
                                            colorScheme="gray"
                                            variant="outline"
                                            leftIcon={<Icon as={FiLogOut} />}
                                            size="lg"
                                            w="full"
                                            _hover={{
                                                bg: "red.50",
                                                borderColor: "red.500",
                                                color: "red.600"
                                            }}
                                            _dark={{
                                                _hover: {
                                                    bg: "red.900",
                                                    borderColor: "red.400",
                                                    color: "red.300"
                                                }
                                            }}
                                        >
                                            Đăng xuất
                                        </Button>
                                    </CardBody>
                                </Card>

                                {/* Danger Zone */}
                                <Card 
                                    bg="red.50" 
                                    borderColor="red.200" 
                                    shadow="sm"
                                    w="full"
                                    _dark={{ bg: "red.900", borderColor: "red.700" }}
                                >
                                    <CardHeader>
                                        <Flex align="center">
                                            <Icon as={FiTrash2} color="red.500" mr={3} />
                                            <Heading size="md" color="red.600">
                                                Vùng nguy hiểm
                                            </Heading>
                                        </Flex>
                                    </CardHeader>
                                    <CardBody>
                                        <Text mb={4} color="red.700" _dark={{ color: "red.300" }}>
                                            Hành động này không thể hoàn tác. Toàn bộ dữ liệu của bạn sẽ bị xóa vĩnh viễn.
                                        </Text>
                                        <Button 
                                            colorScheme="red"
                                            leftIcon={<Icon as={FiTrash2} />}
                                            size="lg"
                                        >
                                            Xóa tài khoản
                                        </Button>
                                    </CardBody>
                                </Card>
                            </VStack>
                        </TabPanel>
                    </TabPanels>
                </Tabs>
            </VStack>
        </Container>
    );
};

export default SettingsPage;
