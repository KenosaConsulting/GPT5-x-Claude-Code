const { User, users } = require('./userModel');
const { generateToken } = require('./authMiddleware');

async function login(req, res) {
    const { username, password } = req.body;

    // Basic validation
    if (!username || !password) {
        return res.status(400).json({ message: 'Username and password are required' });
    }

    // Check if user exists
    const user = users.get(username);
    if (!user) {
        return res.status(401).json({ message: 'Invalid credentials' });
    }

    // Validate password
    try {
        const isValid = await user.comparePassword(password);
        if (!isValid) {
            return res.status(401).json({ message: 'Invalid credentials' });
        }

        // Generate JWT token
        const token = generateToken(user);
        res.status(200).json({ token });
    } catch (error) {
        console.error('Authentication error:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
}

module.exports = { login };