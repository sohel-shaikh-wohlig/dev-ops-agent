"""
Session Manager Service
Handles session creation, storage, and cleanup
"""
import uuid
import json
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from app.core.config import get_settings
from app.core.logging_config import logger
from app.models.schemas import ConfigChange


class SessionManager:
    """
    Manages user sessions for configuration updates
    """

    settings = get_settings()
    
    def __init__(self):
        """Initialize session manager"""
        self.sessions: Dict[str, Dict] = {}
        logger.info("SessionManager initialized")
    
    def create_session(
        self,
        microservice_path: Path,
        env_vars: Dict[str, str],
        changes: List[ConfigChange]
    ) -> str:
        """
        Create a new session
        
        Args:
            microservice_path: Path to microservice files
            env_vars: Environment variables
            changes: List of configuration changes
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        session_data = {
            'session_id': session_id,
            'microservice_path': str(microservice_path),
            'env_vars': env_vars,
            'changes': [change.model_dump() for change in changes],
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRY_HOURS),
            'status': 'preview',
            'applied': False
        }
        
        self.sessions[session_id] = session_data
        
        # Save session to disk for persistence
        self._save_session_to_disk(session_id, session_data)
        
        logger.info(f"Created session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Get session data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        # Try memory first
        if session_id in self.sessions:
            session = self.sessions[session_id]
            
            # Check expiry
            if datetime.utcnow() > session['expires_at']:
                logger.warning(f"Session expired: {session_id}")
                self.delete_session(session_id)
                return None
            
            return session
        
        # Try loading from disk
        session = self._load_session_from_disk(session_id)
        if session:
            self.sessions[session_id] = session
            return session
        
        logger.warning(f"Session not found: {session_id}")
        return None
    
    def update_session(self, session_id: str, updates: Dict) -> bool:
        """
        Update session data
        
        Args:
            session_id: Session identifier
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.update(updates)
        self.sessions[session_id] = session
        self._save_session_to_disk(session_id, session)
        
        logger.info(f"Updated session: {session_id}")
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        # Remove from disk
        session_file = self._get_session_file_path(session_id)
        if session_file.exists():
            session_file.unlink()
        
        # Remove session directory
        session_dir = settings.UPLOAD_DIR / session_id
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)
        
        logger.info(f"Deleted session: {session_id}")
        return True
    
    def list_sessions(self) -> List[Dict]:
        """
        List all active sessions
        
        Returns:
            List of session data
        """
        sessions = []
        for session_id in list(self.sessions.keys()):
            session = self.get_session(session_id)
            if session:
                sessions.append({
                    'session_id': session_id,
                    'created_at': session['created_at'],
                    'expires_at': session['expires_at'],
                    'status': session['status'],
                    'changes_count': len(session['changes'])
                })
        return sessions
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = []
        
        for session_id, session in list(self.sessions.items()):
            if datetime.utcnow() > session['expires_at']:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.delete_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    def _get_session_file_path(self, session_id: str) -> Path:
        """Get path to session metadata file"""
        return settings.UPLOAD_DIR / f"{session_id}_session.json"
    
    def _save_session_to_disk(self, session_id: str, session_data: Dict) -> None:
        """
        Save session data to disk for persistence
        
        Args:
            session_id: Session identifier
            session_data: Session data to save
        """
        try:
            session_file = self._get_session_file_path(session_id)
            
            # Convert datetime objects to strings
            data_to_save = session_data.copy()
            data_to_save['created_at'] = session_data['created_at'].isoformat()
            data_to_save['expires_at'] = session_data['expires_at'].isoformat()
            
            with open(session_file, 'w') as f:
                json.dump(data_to_save, f, indent=2)
            
            logger.debug(f"Saved session to disk: {session_id}")
        except Exception as e:
            logger.error(f"Failed to save session to disk: {e}")
    
    def _load_session_from_disk(self, session_id: str) -> Optional[Dict]:
        """
        Load session data from disk
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        try:
            session_file = self._get_session_file_path(session_id)
            
            if not session_file.exists():
                return None
            
            with open(session_file, 'r') as f:
                data = json.load(f)
            
            # Convert ISO strings back to datetime
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
            
            logger.debug(f"Loaded session from disk: {session_id}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load session from disk: {e}")
            return None


# Create global session manager instance
session_manager = SessionManager()