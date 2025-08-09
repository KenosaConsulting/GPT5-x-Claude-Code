const express = require('express');
const { login } = require('./authController');
const { authenticateToken } = require('./authMiddleware');

const router = express.Router();

// Authentication endpoint
router.post('/api/auth/login', login);

// Example of a protected route
router.get('/api/protected', authenticateToken, (req, res) => {
    res.json({ message: 'Access granted to protected route', user: req.user });
});

module.exports = router;