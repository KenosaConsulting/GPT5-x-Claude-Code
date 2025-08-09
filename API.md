# Authentication API Documentation

## Login Endpoint

**URL:** `/api/auth/login`
**Method:** `POST`
**Content-Type:** `application/json`

### Request Body

```json
{
    "username": "string",
    "password": "string"
}
```

### Successful Response (200 OK)

```json
{
    "token": "JWT_TOKEN_STRING"
}
```

### Error Responses

#### 400 Bad Request
When username or password is missing:
```json
{
    "message": "Username and password are required"
}
```

#### 401 Unauthorized
When credentials are invalid:
```json
{
    "message": "Invalid credentials"
}
```

### Protected Routes

Protected routes require the JWT token to be included in the Authorization header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

#### 401 Unauthorized
When token is missing:
```json
{
    "message": "Authentication token required"
}
```

#### 403 Forbidden
When token is invalid or expired:
```json
{
    "message": "Invalid or expired token"
}
```