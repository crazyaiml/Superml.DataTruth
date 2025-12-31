# User Management System

## Overview

Comprehensive user management system with role-based personas and customizable business goals. Integrates seamlessly with **Insights**, **Chats**, and **Search & Ask** features.

## Features

### 🎭 User Roles & Personas
- **Executive/Director** 👔 - Strategic KPIs, long-term trends
- **Trader** 📊 - Short-term patterns, volatility, quick actions
- **Investor** 💰 - Long-term growth, risk assessment
- **Analyst** 🔬 - Deep data analysis, quality checks
- **Manager** 👥 - Team performance, operational metrics
- **Sales** 🎯 - Revenue metrics, customer insights
- **Operations** ⚙️ - Efficiency, process optimization
- **Finance** 💵 - Cost analysis, budgets, forecasts
- **Agent** 🎧 - Task-specific, immediate actions
- **Admin** 🔐 - System management

### 🎯 Business Goals
- **Role-based goal suggestions** - Smart recommendations based on user role
- **Custom goals** - Add personalized business objectives
- **Editable goals** - Update goals as priorities change
- **Goal tracking** - Use goals to personalize insights and recommendations

### 💼 Full CRUD Operations
- **Create** - Add new users with role and goals
- **Read** - View user profiles and details
- **Update** - Edit user info, role, department, goals
- **Delete** - Soft delete (deactivate) or hard delete

## API Endpoints

### User Management
```
POST   /api/v1/users                    Create user (admin only)
GET    /api/v1/users                    List all users
GET    /api/v1/users/{id}               Get user by ID
PUT    /api/v1/users/{id}               Update user (self or admin)
DELETE /api/v1/users/{id}               Delete user (admin only)
GET    /api/v1/users/me                 Get current user profile
GET    /api/v1/users/goals/suggestions  Get goal suggestions for role
```

### Request/Response Models

**Create User:**
```json
{
  "username": "john_trader",
  "email": "john@example.com",
  "password": "secure123",
  "full_name": "John Smith",
  "role": "trader",
  "goals": [
    "Identify short-term trading opportunities",
    "Monitor market volatility"
  ],
  "department": "Trading Desk"
}
```

**Update User:**
```json
{
  "email": "john.smith@example.com",
  "full_name": "John Smith",
  "role": "investor",
  "goals": [
    "Identify long-term investment opportunities",
    "Assess asset growth potential"
  ],
  "department": "Investment Team"
}
```

**User Profile Response:**
```json
{
  "id": "uuid-here",
  "username": "john_trader",
  "email": "john@example.com",
  "full_name": "John Smith",
  "role": "trader",
  "goals": [
    "Identify short-term trading opportunities",
    "Monitor market volatility"
  ],
  "department": "Trading Desk",
  "is_active": true,
  "created_at": "2025-12-28T10:00:00Z",
  "updated_at": "2025-12-28T10:00:00Z"
}
```

## Integration with Features

### 🔮 Insights
- **Role-based filtering** - See only relevant insight types
- **Priority boosting** - Insights preferred by your role get higher scores
- **Custom narratives** - LLM generates explanations tailored to your role
- **Action suggestions** - Role-specific recommended actions

### 💬 Chat Interface
- Uses user goals to provide context-aware responses
- Prioritizes answers relevant to user's business objectives
- Remembers user preferences and role

### 🔍 Search & Ask
- Personalizes query suggestions based on role
- Filters results by user goals and priorities
- Provides role-appropriate data insights

## UI Features

### User List View
- **Card-based layout** - Clean, modern design
- **Role badges** - Visual role indicators with icons
- **Goal preview** - Shows first 3 goals, with count
- **Status indicators** - Active/Inactive badges
- **Quick actions** - Edit and Delete buttons

### Create/Edit Modal
- **Form validation** - Email, password, required fields
- **Role selector** - Dropdown with icons
- **Smart goal suggestions** - Auto-populated based on role
- **Custom goals** - Add personalized objectives
- **Goal management** - Add/remove with visual feedback
- **Department field** - Optional organizational context

## Database Schema

```sql
CREATE TABLE users (
    id VARCHAR(100) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    goals TEXT[],
    department VARCHAR(100),
    preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Security

### Authentication
- Password hashing using SHA-256
- JWT tokens for session management
- User can update own profile
- Admin required for user creation/deletion

### Authorization
- **Admin** - Full access to all users
- **User** - Can update own profile only
- **Guest** - No access to user management

### Data Protection
- Passwords stored as hashes (never plain text)
- Soft delete by default (preserves audit trail)
- Hard delete option for admins
- Email validation

## Usage Examples

### Frontend Navigation
Access User Management from the homepage or navigate directly to `/users`

### Create a New User
1. Click "Create User" button
2. Fill in username, email, password, full name
3. Select role from dropdown
4. Choose goals from suggestions or add custom
5. Optionally add department
6. Click "Create User"

### Edit User Goals
1. Click "Edit" on user card
2. Role selector updates goal suggestions
3. Click suggested goals to add
4. Click "+" on existing goals to remove
5. Add custom goals as needed
6. Click "Update User"

### Role-Based Insights
1. Go to Insights screen
2. Select your role from dropdown
3. Generate insights
4. See personalized insights and actions

## File Structure

```
Backend:
├── src/user/
│   ├── __init__.py          # Module exports
│   ├── models.py            # User models, roles, goal suggestions
│   └── manager.py           # UserManager class, CRUD operations
└── src/api/routes.py        # API endpoints (added user routes)

Frontend:
├── src/components/
│   └── UserManagement.tsx   # User management UI
└── src/App.tsx              # Added /users route
```

## Future Enhancements

- [ ] Password reset functionality
- [ ] Email verification
- [ ] User groups and teams
- [ ] Goal progress tracking
- [ ] Activity logging and audit trail
- [ ] User preferences for UI customization
- [ ] Integration with SSO (Single Sign-On)
- [ ] Role permissions configuration
- [ ] Bulk user import/export
- [ ] User analytics dashboard
