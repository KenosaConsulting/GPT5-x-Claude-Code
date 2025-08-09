const mockUsers = require('../models/userMockData');

const userController = {
  getUsers: (req, res) => {
    try {
      res.status(200).json({
        success: true,
        data: mockUsers
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Internal server error'
      });
    }
  }
};

module.exports = userController;