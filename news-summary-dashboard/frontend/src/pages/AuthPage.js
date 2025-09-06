import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../services/supabaseClient";
import logoImage from "../assets/icon_logo.png";
import {
    Box,
    Button,
    Divider,
    Flex,
    FormControl,
    FormLabel,
    Heading,
    Input,
    Stack,
    Text,
    useToast,
    Image,
    HStack,
} from "@chakra-ui/react";
import { FcGoogle } from "react-icons/fc";

// Background image URL, you can replace it with your own image
const BACKGROUND_IMAGE_URL =
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRp1fZckhB23SHAuxU_g7yw4Rzhs_pig9CJ9YdR5wVsYYoJlmZ2";

const AuthPage = () => {
    const [isLogin, setIsLogin] = useState(false); // Default is registration page
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();
    const toast = useToast();

    const handleAuthAction = async (e) => {
        e.preventDefault();
        setLoading(true);

        let error;
        if (isLogin) {
            // Login logic
            const { error: signInError } = await supabase.auth.signInWithPassword({
                email,
                password,
            });
            error = signInError;
        } else {
            // Registration logic
            const { error: signUpError } = await supabase.auth.signUp({
                email,
                password,
            });
            if (!signUpError) {
                toast({
                    title: "Registration successful!",
                    description: "Please check your email to confirm your account.",
                    status: "success",
                    duration: 5000,
                    isClosable: true,
                });
                setIsLogin(true); // Automatically switch to login form
            }
            error = signUpError;
        }

        if (error) {
            toast({
                title: "An error occurred",
                description: error.message,
                status: "error",
                duration: 5000,
                isClosable: true,
            });
        } else if (isLogin) {
            navigate("/"); // Redirect to homepage after successful login
        }
        setLoading(false);
    };

    const handleGoogleSignIn = async () => {
        // Get current URL for redirect
        const redirectURL = process.env.NODE_ENV === 'production' 
            ? `${window.location.origin}/auth/callback`
            : 'http://localhost:3000/auth/callback';
            
        await supabase.auth.signInWithOAuth({ 
            provider: "google",
            options: {
                redirectTo: redirectURL
            }
        });
    };

    return (
        <Flex minH="100vh" w="100%">
        {/* Left column - Background image */}
        <Box
            flex={1}
            bgImage={`url(${BACKGROUND_IMAGE_URL})`}
            bgSize="cover"
            bgPosition="center"
            display={{ base: "none", md: "block" }}
        />

        {/* Right column - Authentication form */}
        <Flex
            flex={1}
            align="center"
            justify="center"
            bg="gray.50"
            p={{ base: 4, md: 8 }}
        >
            <Stack spacing={8} w="full" maxW="md">
            <Stack align={"center"}>
                <HStack>
                {/* Logo icon with icon_logo.png */}
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
                        console.log('Image failed to load:', e);
                    }}
                />
                <Heading fontSize={"2xl"}>FINsistant</Heading>
                </HStack>
                <Text fontSize={"lg"} color={"gray.600"}>
                AI Assistant for Market Insight
                </Text>
            </Stack>

            <Box rounded={"lg"} bg={"white"} boxShadow={"lg"} p={8}>
                <Stack spacing={4}>
                <Heading fontSize="2xl">
                    {isLogin ? "Đăng nhập" : "Tạo tài khoản"}
                </Heading>
                <Text fontSize="sm" color="gray.600">
                    {isLogin
                    ? "Chào mừng trở lại!"
                    : "Nhập email và mật khẩu để đăng ký."}
                </Text>
                <form onSubmit={handleAuthAction}>
                    <FormControl id="email" isRequired>
                    <FormLabel>Email</FormLabel>
                    <Input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                    />
                    </FormControl>
                    <FormControl id="password" mt={4} isRequired>
                    <FormLabel>Password</FormLabel>
                    <Input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    </FormControl>
                    <Button
                    type="submit"
                    colorScheme="blue"
                    w="full"
                    mt={8}
                    isLoading={loading}
                    >
                    {isLogin ? "Đăng nhập" : "Đăng ký"}
                    </Button>
                </form>

                <Divider my={6} />

                <Button
                    w={"full"}
                    variant={"outline"}
                    leftIcon={<FcGoogle />}
                    onClick={handleGoogleSignIn}
                >
                    <Text>Continue with Google</Text>
                </Button>

                <Text align="center" mt={4}>
                    {isLogin ? "Chưa có tài khoản? " : "Đã có tài khoản? "}
                    <Text
                    as="span"
                    color="blue.400"
                    cursor="pointer"
                    onClick={() => setIsLogin(!isLogin)}
                    >
                    {isLogin ? "Đăng ký" : "Đăng nhập"}
                    </Text>
                </Text>
                </Stack>
            </Box>
            </Stack>
        </Flex>
        </Flex>
    );
};

export default AuthPage;
