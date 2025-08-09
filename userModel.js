const bcrypt = require('bcrypt');

class User {
    constructor(username, passwordHash) {
        this.username = username;
        this.password_hash = passwordHash;
    }

    static async hashPassword(password) {
        const saltRounds = 10;
        return await bcrypt.hash(password, saltRounds);
    }

    async comparePassword(password) {
        return await bcrypt.compare(password, this.password_hash);
    }
}

// Mock database for demonstration
const users = new Map();

// Add a mock user for testing
(async () => {
    const hashedPassword = await User.hashPassword('validPassword');
    users.set('validUser', new User('validUser', hashedPassword));
})();

module.exports = { User, users };