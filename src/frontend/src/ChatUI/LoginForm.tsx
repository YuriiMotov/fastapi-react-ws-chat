import React, { useState } from "react";
import {
  Flex,
  Text,
  VStack,
  InputGroup,
  Input,
  InputRightElement,
  Button,
  Container,
} from "@chakra-ui/react";

interface TokensResponse {
  access_token: string
  refresh_token: string
};

interface LoginFormComponentParams {
  setTokens: (accessToken: string, refreshToken: string) => void
}

function LoginFormComponent({setTokens}: LoginFormComponentParams) {
  // const apiUrl = process.env.REACT_APP_API_KEY;
  const [userName, setUserName] = useState('');
  const [userPassword, setUserPassword] = useState('');
  const [show, setShow] = useState(false);
  const handleClick = () => setShow(!show);

  function loginClickHandle() {
    const formData = new URLSearchParams();
    formData.append('username', userName);
    formData.append('password', userPassword);

    fetch("http://127.0.0.1:8000/auth/token",
      {
          headers: {
            'Accept': 'application/json',
          },
          method: "POST",
          body: formData,
      })
      .then(function(res){
        console.log(res);
        res.json().then(function(responseJson) {
          const tokenResp = responseJson as TokensResponse;
          console.log(responseJson);
          setTokens(tokenResp.access_token, tokenResp.refresh_token);
        })
        .catch(function(res){ console.log(res) })

      })
      .catch(function(res){ console.log(res) })
  }


  return (
    <Container size="md">
      <Text mb='8px'>Name</Text>
      <Input
        value={userName}
        onChange={(event) => setUserName(event.target.value)}
        size='sm'
      />
      <Text mb='8px'>Password</Text>
      <InputGroup size='md'>
        <Input
          value={userPassword}
          onChange={(event) => setUserPassword(event.target.value)}
          pr='4.5rem'
          type={show ? 'text' : 'password'}
        />
        <InputRightElement width='4.5rem'>
          <Button h='1.75rem' size='sm' onClick={handleClick}>
            {show ? 'Hide' : 'Show'}
          </Button>
        </InputRightElement>
      </InputGroup>
      <Button colorScheme='blue' onClick={loginClickHandle}>Log in</Button>
    </Container>
  );
}


export { LoginFormComponent };
