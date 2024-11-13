# core/config.py

from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import pyjwt
from passlib.context import CryptContext
from pydantic import BaseModel, SecretStr
import secrets
import logging
from dataclasses import dataclass
import aiohttp
import ssl
import hashlib
import json
from pathlib import Path

class SecurityConfig(BaseModel):
    """Security configuration for production environment."""
    
    # JWT Settings
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Settings
    MIN_PASSWORD_LENGTH: int = 12
    PASSWORD_REGEX: str = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{12,}$"
    
    # Rate Limiting
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour
    MAX_REQUESTS_PER_WINDOW: int = 1000
    
    # Session Settings
    SESSION_LIFETIME: int = 3600  # 1 hour
    MAX_SESSIONS_PER_USER: int = 5
    
    # File Upload Settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ['xlsx', 'xls', 'csv']
    
    # SSL/TLS Settings
    SSL_CERT_PATH: Optional[Path] = None
    SSL_KEY_PATH: Optional[Path] = None
    MIN_TLS_VERSION: ssl.TLSVersion = ssl.TLSVersion.TLSv1_2
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = []
    ALLOWED_METHODS: List[str] = ["GET", "POST"]
    ALLOW_CREDENTIALS: bool = True
    
    # Security Headers
    SECURITY_HEADERS: Dict[str, str] = {
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }

class SecurityService:
    """Service for handling security operations."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.logger = logging.getLogger(__name__)

    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
            
        to_encode.update({"exp": expire})
        
        return pyjwt.encode(
            to_encode,
            self.config.JWT_SECRET_KEY,
            algorithm=self.config.JWT_ALGORITHM
        )

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token."""
        try:
            payload = pyjwt.decode(
                token,
                self.config.JWT_SECRET_KEY,
                algorithms=[self.config.JWT_ALGORITHM]
            )
            return payload
        except pyjwt.JWTError as e:
            self.logger.warning(f"Token verification failed: {str(e)}")
            return None

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def validate_file(self, filename: str, content: bytes) -> Tuple[bool, str]:
        """Validate file upload."""
        
        # Check file extension
        ext = filename.split('.')[-1].lower()
        if ext not in self.config.ALLOWED_EXTENSIONS:
            return False, f"File type not allowed. Allowed types: {self.config.ALLOWED_EXTENSIONS}"
        
        # Check file size
        if len(content) > self.config.MAX_UPLOAD_SIZE:
            return False, f"File too large. Maximum size: {self.config.MAX_UPLOAD_SIZE/1024/1024}MB"
        
        # Calculate file hash
        file_hash = hashlib.sha256(content).hexdigest()
        
        return True, file_hash

    def setup_ssl_context(self) -> ssl.SSLContext:
        """Set up SSL context for HTTPS."""
        ssl_context = ssl.create_default_context()
        ssl_context.minimum_version = self.config.MIN_TLS_VERSION
        
        if self.config.SSL_CERT_PATH and self.config.SSL_KEY_PATH:
            ssl_context.load_cert_chain(
                self.config.SSL_CERT_PATH,
                self.config.SSL_KEY_PATH
            )
            
        return ssl_context

class RateLimiter:
    """Rate limiting implementation."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.requests: Dict[str, List[datetime]] = {}

    def is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.config.RATE_LIMIT_WINDOW)
        
        # Clean old requests
        if client_id in self.requests:
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > window_start
            ]
        else:
            self.requests[client_id] = []
            
        # Check rate limit
        if len(self.requests[client_id]) >= self.config.MAX_REQUESTS_PER_WINDOW:
            return True
            
        # Add new request
        self.requests[client_id].append(now)
        return False

class SessionManager:
    """Manage user sessions."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.sessions: Dict[str, Dict] = {}

    def create_session(self, user_id: str) -> str:
        """Create new session."""
        # Clean expired sessions
        self._clean_expired_sessions(user_id)
        
        # Check max sessions
        user_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session['user_id'] == user_id
        ]
        
        if len(user_sessions) >= self.config.MAX_SESSIONS_PER_USER:
            # Remove oldest session
            oldest_session = min(
                user_sessions,
                key=lambda s: self.sessions[s]['created_at']
            )
            del self.sessions[oldest_session]

        # Create new session
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(
                seconds=self.config.SESSION_LIFETIME
            )
        }
        
        return session_id

    def validate_session(self, session_id: str) -> Optional[str]:
        """Validate session and return user_id if valid."""
        if session_id not in self.sessions:
            return None
            
        session = self.sessions[session_id]
        if session['expires_at'] < datetime.utcnow():
            del self.sessions[session_id]
            return None
            
        return session['user_id']

    def _clean_expired_sessions(self, user_id: str):
        """Remove expired sessions for user."""
        now = datetime.utcnow()
        expired = [
            session_id for session_id, session in self.sessions.items()
            if session['user_id'] == user_id and session['expires_at'] < now
        ]
        
        for session_id in expired:
            del self.sessions[session_id]

class SecurityMiddleware:
    """Security middleware for web application."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.security_service = SecurityService(config)
        self.rate_limiter = RateLimiter(config)
        self.session_manager = SessionManager(config)

    async def process_request(self, request) -> Optional[Response]:
        """Process incoming request."""
        # Check rate limiting
        client_id = self._get_client_id(request)
        if self.rate_limiter.is_rate_limited(client_id):
            return Response(status_code=429, content="Rate limit exceeded")

        # Verify session
        session_id = request.cookies.get('session_id')
        if session_id:
            user_id = self.session_manager.validate_session(session_id)
            if not user_id:
                return Response(status_code=401, content="Invalid session")
            request.state.user_id = user_id

        # Add security headers
        response = Response()
        for header, value in self.config.SECURITY_HEADERS.items():
            response.headers[header] = value

        return response

    def _get_client_id(self, request) -> str:
        """Get unique client identifier."""
        return request.client.host  # Use IP address as client ID

# Example usage:
"""
security_config = SecurityConfig()
security_service = SecurityService(security_config)

# Initialize SSL context
ssl_context = security_service.setup_ssl_context()

# Create middleware
security_middleware = SecurityMiddleware(security_config)

# Use in FastAPI app
app.middleware("http")(security_middleware.process_request)
"""
