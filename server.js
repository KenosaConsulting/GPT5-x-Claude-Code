const express = require('express');
const userController = require('./controllers/userController');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Routes
app.get('/api/users', userController.getUsers);

// Documentation endpoint
app.get('/api/docs', (req, res) => {
  res.json({
    endpoints: [
      {
        path: '/api/users',
        method: 'GET',
        description: 'Returns a list of users',
        response: {
          success: 'boolean',
          data: 'array of user objects containing id, name, email, and age'
        }
      }
    ]
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    success: false,
    error: 'Internal server error'
  });
});

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

module.exports = app; // For testing purposes