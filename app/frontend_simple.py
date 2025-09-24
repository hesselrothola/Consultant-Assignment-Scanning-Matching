"""
Simple frontend routes for testing
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/consultant", tags=["frontend"])

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard view"""
    return HTMLResponse("""
    <html>
    <head><title>Consultant Dashboard</title></head>
    <body>
        <h1>✅ Dashboard Works!</h1>
        <p>You have successfully logged in!</p>
        <p>Welcome to the Consultant Matching System</p>
        <ul>
            <li><a href="/consultant/jobs">View Jobs</a></li>
            <li><a href="/consultant/consultants">View Consultants</a></li>
            <li><a href="/auth/logout">Logout</a></li>
        </ul>
    </body>
    </html>
    """)

@router.get("/test", response_class=HTMLResponse)
async def test():
    """Test route"""
    return HTMLResponse("<h1>Test route works!</h1>")