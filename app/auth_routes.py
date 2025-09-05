"""
Authentication routes for login, logout, and user management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Optional
import os

from app.auth import (
    User, UserCreate, UserUpdate, Token,
    verify_password, get_password_hash,
    create_access_token, create_refresh_token,
    get_current_user, require_admin, require_user,
    UserRole, ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.repo import DatabaseRepository
from jinja2 import Template

router = APIRouter(prefix="/auth", tags=["authentication"])

# Database connection
def get_db():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/consultant_matching")
    return DatabaseRepository(db_url)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: Optional[str] = None):
    """Display login page."""
    login_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Consultant Matching System</title>
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Inter Font -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <!-- Custom styles -->
    <style>
        * {
            font-family: 'Inter', sans-serif;
        }
        
        /* Glass morphism effect */
        .glass {
            background: rgba(17, 24, 39, 0.8);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(75, 85, 99, 0.2);
        }
        
        .glass-lighter {
            background: rgba(17, 24, 39, 0.6);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(75, 85, 99, 0.15);
        }
        
        /* Glow effects */
        .glow-purple {
            box-shadow: 0 0 30px rgba(124, 58, 237, 0.3);
        }
        
        /* Floating animation */
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            33% { transform: translateY(-10px) rotate(1deg); }
            66% { transform: translateY(5px) rotate(-1deg); }
        }
        
        .animate-float {
            animation: float 6s ease-in-out infinite;
        }
        
        /* Gradient background */
        .gradient-bg {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f172a 100%);
        }
    </style>
    
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    animation: {
                        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                        'float': 'float 6s ease-in-out infinite',
                    }
                }
            }
        }
    </script>
</head>
<body class="gradient-bg min-h-screen text-gray-100 relative overflow-hidden">
    <!-- Animated background elements -->
    <div class="absolute inset-0 overflow-hidden">
        <div class="absolute -top-40 -right-40 w-80 h-80 bg-purple-600 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-float"></div>
        <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-600 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-float" style="animation-delay: 2s;"></div>
        <div class="absolute top-1/2 left-1/2 w-80 h-80 bg-violet-600 rounded-full mix-blend-multiply filter blur-xl opacity-10 animate-float" style="animation-delay: 4s;"></div>
    </div>
    
    <!-- Background pattern -->
    <div class="fixed inset-0 opacity-5">
        <div class="absolute inset-0" style="background-image: url('data:image/svg+xml,%3Csvg width=\"60\" height=\"60\" viewBox=\"0 0 60 60\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cg fill=\"none\" fill-rule=\"evenodd\"%3E%3Cg fill=\"%239C92AC\" fill-opacity=\"0.1\"%3E%3Cpath d=\"M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E');"></div>
    </div>

    <div class="relative min-h-screen flex items-center justify-center px-4">
        <div class="glass rounded-2xl p-8 w-full max-w-md glow-purple relative">
            <!-- Logo and header -->
            <div class="text-center mb-8">
                <div class="flex justify-center mb-4">
                    <div class="w-16 h-16 bg-gradient-to-br from-violet-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                        <i class="fas fa-users text-white text-2xl"></i>
                    </div>
                </div>
                <h1 class="text-3xl font-bold bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent mb-2">
                    Consultant Matching
                </h1>
                <p class="text-gray-400">Executive Platform Access</p>
            </div>
            
            <form action="/auth/login" method="POST" class="space-y-6">
                {% if error %}
                <div class="bg-red-900/30 border border-red-800/50 text-red-400 px-4 py-3 rounded-lg backdrop-blur-sm">
                    <i class="fas fa-exclamation-triangle mr-2"></i>{{ error }}
                </div>
                {% endif %}
                
                <div>
                    <label for="username" class="block text-sm font-medium text-gray-300 mb-2">
                        <i class="fas fa-user mr-2 text-purple-400"></i>Username
                    </label>
                    <input type="text" name="username" id="username" required
                           class="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-200 backdrop-blur-sm"
                           placeholder="Enter your username">
                </div>
                
                <div>
                    <label for="password" class="block text-sm font-medium text-gray-300 mb-2">
                        <i class="fas fa-lock mr-2 text-purple-400"></i>Password
                    </label>
                    <input type="password" name="password" id="password" required
                           class="w-full px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-lg text-gray-200 placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-200 backdrop-blur-sm"
                           placeholder="Enter your password">
                </div>
                
                <input type="hidden" name="next" value="{{ next or '/consultant/' }}">
                
                <div class="pt-2">
                    <button type="submit"
                            class="w-full bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 hover:scale-105 transform focus:outline-none focus:ring-2 focus:ring-purple-500/50 shadow-lg">
                        <i class="fas fa-sign-in-alt mr-2"></i>Sign In
                    </button>
                </div>
            </form>
            
            <!-- Footer -->
            <div class="mt-8 text-center text-sm text-gray-500">
                <p>
                    <i class="fas fa-shield-alt mr-1 text-purple-400"></i>
                    Secure Executive Access Portal
                </p>
                <p class="text-xs mt-1 text-gray-600">
                    Swedish Consultant Assignment Matching System
                </p>
            </div>
        </div>
    </div>

    <script>
        // Add subtle entrance animation
        document.addEventListener('DOMContentLoaded', function() {
            const loginCard = document.querySelector('.glass');
            loginCard.style.opacity = '0';
            loginCard.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                loginCard.style.transition = 'all 0.6s ease-out';
                loginCard.style.opacity = '1';
                loginCard.style.transform = 'translateY(0)';
            }, 100);
        });
        
        // Focus management
        document.getElementById('username').focus();
    </script>
</body>
</html>
    """
    template = Template(login_html)
    return template.render(next=next, error=request.query_params.get("error"))


@router.post("/login")
async def login_web(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/consultant/")
):
    """Authenticate user and create access token for web interface."""
    db = get_db()
    await db.init()
    
    try:
        # Get user from database
        user_dict = await db.get_user_by_username(username)
        
        if not user_dict or not verify_password(password, user_dict["hashed_password"]):
            # Return to login page with error
            await db.close()
            return RedirectResponse(
                url=f"/auth/login?error=Invalid username or password&next={next}",
                status_code=302
            )
        
        if not user_dict["is_active"]:
            await db.close()
            return RedirectResponse(
                url="/auth/login?error=Account is disabled",
                status_code=302
            )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": username, "user_id": str(user_dict["user_id"]), "role": user_dict["role"]}
        )
        
        # Update last login
        await db.update_last_login(str(user_dict["user_id"]))
        
        # Log the login action
        client_ip = request.client.host if request.client else None
        await db.log_user_action(
            str(user_dict["user_id"]), 
            "login", 
            ip_address=client_ip
        )
        
        await db.close()
        
        # Set cookie and redirect
        redirect_response = RedirectResponse(url=next, status_code=302)
        redirect_response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax"
        )
        return redirect_response
        
    except Exception as e:
        await db.close()
        print(f"Authentication failed: {e}")
        return RedirectResponse(
            url=f"/auth/login?error=Authentication failed: {str(e)}",
            status_code=302
        )


@router.post("/token", response_model=Token)
async def login_api(form_data: OAuth2PasswordRequestForm = Depends()):
    """API endpoint for token authentication (for API clients)."""
    db = get_db()
    await db.init()
    
    try:
        user_dict = await db.get_user_by_username(form_data.username)
        
        if not user_dict or not verify_password(form_data.password, user_dict["hashed_password"]):
            await db.close()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user_dict["is_active"]:
            await db.close()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Create tokens
        access_token = create_access_token(
            data={"sub": form_data.username, "user_id": str(user_dict["user_id"]), "role": user_dict["role"]}
        )
        refresh_token = create_refresh_token(
            data={"sub": form_data.username, "user_id": str(user_dict["user_id"])}
        )
        
        await db.update_last_login(str(user_dict["user_id"]))
        await db.close()
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )



@router.get("/logout")
async def logout(response: Response):
    """Logout user by clearing the session cookie."""
    redirect_response = RedirectResponse(url="/auth/login", status_code=302)
    redirect_response.delete_cookie(key="access_token")
    return redirect_response


@router.get("/users", response_class=HTMLResponse)
async def users_admin_page(request: Request, current_user: User = Depends(require_admin)):
    """Display user management page (admin only)."""
    db = get_db()
    await db.init()
    
    try:
        users = await db.get_all_users()
        await db.close()
        
        html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Management - Admin</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.6"></script>
</head>
<body class="bg-gray-100">
    <div class="min-h-screen p-8">
        <div class="max-w-7xl mx-auto">
            <div class="bg-white rounded-lg shadow-lg p-6">
                <div class="flex justify-between items-center mb-6">
                    <h1 class="text-2xl font-bold text-gray-800">User Management</h1>
                    <div class="space-x-4">
                        <a href="/consultant/" class="text-blue-600 hover:text-blue-800">← Back to Dashboard</a>
                        <button onclick="showAddUserModal()" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                            Add New User
                        </button>
                    </div>
                </div>
                
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Username</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Full Name</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Login</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {% for user in users %}
                            <tr>
                                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ user.username }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ user.full_name }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ user.email }}</td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                                        {% if user.role == 'admin' %}bg-red-100 text-red-800
                                        {% elif user.role == 'manager' %}bg-blue-100 text-blue-800
                                        {% else %}bg-gray-100 text-gray-800{% endif %}">
                                        {{ user.role }}
                                    </span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                                        {% if user.is_active %}bg-green-100 text-green-800{% else %}bg-red-100 text-red-800{% endif %}">
                                        {% if user.is_active %}Active{% else %}Disabled{% endif %}
                                    </span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {{ user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never' }}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                    <button onclick="editUser('{{ user.user_id }}')" class="text-blue-600 hover:text-blue-900 mr-3">Edit</button>
                                    <button onclick="deleteUser('{{ user.user_id }}')" class="text-red-600 hover:text-red-900">Delete</button>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Add User Modal -->
    <div id="addUserModal" class="hidden fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 class="text-lg font-bold text-gray-900 mb-4">Add New User</h3>
            <form hx-post="/auth/users/create" hx-target="#result">
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Username</label>
                        <input type="text" name="username" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Email</label>
                        <input type="email" name="email" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Full Name</label>
                        <input type="text" name="full_name" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Password</label>
                        <input type="password" name="password" required class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Role</label>
                        <select name="role" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
                            <option value="viewer">Viewer</option>
                            <option value="manager">Manager</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>
                    <div class="flex justify-end space-x-3">
                        <button type="button" onclick="hideAddUserModal()" class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                            Cancel
                        </button>
                        <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                            Create User
                        </button>
                    </div>
                </div>
            </form>
            <div id="result"></div>
        </div>
    </div>
    
    <script>
        function showAddUserModal() {
            document.getElementById('addUserModal').classList.remove('hidden');
        }
        
        function hideAddUserModal() {
            document.getElementById('addUserModal').classList.add('hidden');
        }
        
        function editUser(userId) {
            // Implement edit functionality
            alert('Edit user: ' + userId);
        }
        
        function deleteUser(userId) {
            if (confirm('Are you sure you want to delete this user?')) {
                fetch('/auth/users/' + userId, { method: 'DELETE' })
                    .then(() => location.reload());
            }
        }
    </script>
</body>
</html>
        """
        
        template = Template(html)
        return template.render(users=users)
        
    except Exception as e:
        await db.close()
        return f"<h1>Error loading users: {str(e)}</h1>"


@router.post("/users/create")
async def create_user(
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form("viewer"),
    current_user: User = Depends(require_admin)
):
    """Create a new user (admin only)."""
    db = get_db()
    await db.init()
    
    try:
        # Check if user exists
        existing = await db.get_user_by_username(username)
        if existing:
            await db.close()
            return JSONResponse(
                status_code=400,
                content={"error": "Username already exists"}
            )
        
        # Create user
        hashed_password = get_password_hash(password)
        user = await db.create_user(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=role
        )
        
        # Log the action
        await db.log_user_action(
            str(current_user.user_id),
            "create_user",
            resource_type="user",
            resource_id=str(user["user_id"]),
            details={"username": username, "role": role}
        )
        
        await db.close()
        
        return RedirectResponse(url="/auth/users", status_code=302)
        
    except Exception as e:
        await db.close()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin)
):
    """Delete a user (admin only)."""
    if str(current_user.user_id) == user_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account"
        )
    
    db = get_db()
    await db.init()
    
    try:
        success = await db.delete_user(user_id)
        
        if success:
            await db.log_user_action(
                str(current_user.user_id),
                "delete_user",
                resource_type="user",
                resource_id=user_id
            )
        
        await db.close()
        
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.close()
        raise HTTPException(status_code=500, detail=str(e))