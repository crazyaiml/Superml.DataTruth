"""
Chat Session Management

Handles persistence of chat conversations and messages.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.database.internal_db import InternalDB

logger = logging.getLogger(__name__)


class ChatSession:
    """Represents a chat conversation session."""
    
    def __init__(
        self,
        id: str,
        user_id: str,
        connection_id: Optional[str] = None,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_message_at: Optional[datetime] = None,
        message_count: int = 0,
        is_archived: bool = False,
        metadata: Optional[Dict] = None
    ):
        self.id = id
        self.user_id = user_id
        self.connection_id = connection_id
        self.title = title
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_message_at = last_message_at
        self.message_count = message_count
        self.is_archived = is_archived
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "connection_id": self.connection_id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "message_count": self.message_count,
            "is_archived": self.is_archived,
            "metadata": self.metadata
        }


class ChatMessage:
    """Represents a message in a chat session."""
    
    def __init__(
        self,
        id: str,
        session_id: str,
        role: str,
        content: str,
        created_at: Optional[datetime] = None,
        sql_query: Optional[str] = None,
        result_data: Optional[Any] = None,
        result_metadata: Optional[Dict] = None,
        token_count: Optional[int] = None,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.id = id
        self.session_id = session_id
        self.role = role
        self.content = content
        self.created_at = created_at or datetime.utcnow()
        self.sql_query = sql_query
        self.result_data = result_data
        self.result_metadata = result_metadata
        self.token_count = token_count
        self.processing_time_ms = processing_time_ms
        self.error_message = error_message
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sql_query": self.sql_query,
            "data": self.result_data,  # Match frontend expectation
            "metadata": {
                **(self.result_metadata or {}),
                **(self.metadata or {}),
                "token_count": self.token_count,
                "processing_time_ms": self.processing_time_ms
            },
            "error": error_message is not None if hasattr(self, 'error_message') else False
        }


class ChatSessionManager:
    """Manages chat sessions and messages."""
    
    @staticmethod
    def create_session(
        user_id: str,
        connection_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ChatSession:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        import json
        InternalDB.execute_query(
            """INSERT INTO chat_sessions 
               (id, user_id, connection_id, title, created_at, updated_at, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (session_id, user_id, connection_id, title, now, now, json.dumps(metadata or {}))
        )
        
        return ChatSession(
            id=session_id,
            user_id=user_id,
            connection_id=connection_id,
            title=title,
            created_at=now,
            updated_at=now,
            metadata=metadata
        )
    
    @staticmethod
    def get_session(session_id: str) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        result = InternalDB.execute_query(
            """SELECT id, user_id, connection_id, title, created_at, updated_at,
                      last_message_at, message_count, is_archived, metadata
               FROM chat_sessions WHERE id = %s""",
            (session_id,),
            fetch_one=True
        )
        
        if not result:
            return None
        
        import json
        return ChatSession(
            id=result['id'] if isinstance(result, dict) else result[0],
            user_id=result['user_id'] if isinstance(result, dict) else result[1],
            connection_id=result['connection_id'] if isinstance(result, dict) else result[2],
            title=result['title'] if isinstance(result, dict) else result[3],
            created_at=result['created_at'] if isinstance(result, dict) else result[4],
            updated_at=result['updated_at'] if isinstance(result, dict) else result[5],
            last_message_at=result['last_message_at'] if isinstance(result, dict) else result[6],
            message_count=result['message_count'] if isinstance(result, dict) else result[7],
            is_archived=result['is_archived'] if isinstance(result, dict) else result[8],
            metadata=json.loads(result['metadata'] if isinstance(result, dict) else result[9]) if result[9 if not isinstance(result, dict) else 'metadata'] else {}
        )
    
    @staticmethod
    def list_sessions(
        user_id: str,
        limit: int = 50,
        include_archived: bool = False
    ) -> List[ChatSession]:
        """List chat sessions for a user."""
        query = """
            SELECT id, user_id, connection_id, title, created_at, updated_at,
                   last_message_at, message_count, is_archived, metadata
            FROM chat_sessions
            WHERE user_id = %s
        """
        params = [user_id]
        
        if not include_archived:
            query += " AND is_archived = false"
        
        query += " ORDER BY updated_at DESC LIMIT %s"
        params.append(limit)
        
        results = InternalDB.execute_query(query, tuple(params), fetch_all=True)
        
        import json
        sessions = []
        for result in results:
            sessions.append(ChatSession(
                id=result['id'] if isinstance(result, dict) else result[0],
                user_id=result['user_id'] if isinstance(result, dict) else result[1],
                connection_id=result['connection_id'] if isinstance(result, dict) else result[2],
                title=result['title'] if isinstance(result, dict) else result[3],
                created_at=result['created_at'] if isinstance(result, dict) else result[4],
                updated_at=result['updated_at'] if isinstance(result, dict) else result[5],
                last_message_at=result['last_message_at'] if isinstance(result, dict) else result[6],
                message_count=result['message_count'] if isinstance(result, dict) else result[7],
                is_archived=result['is_archived'] if isinstance(result, dict) else result[8],
                metadata=json.loads(result['metadata'] if isinstance(result, dict) else result[9]) if result[9 if not isinstance(result, dict) else 'metadata'] else {}
            ))
        
        return sessions
    
    @staticmethod
    def add_message(
        session_id: str,
        role: str,
        content: str,
        sql_query: Optional[str] = None,
        result_data: Optional[Any] = None,
        result_metadata: Optional[Dict] = None,
        processing_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ChatMessage:
        """Add a message to a chat session."""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        import json
        InternalDB.execute_query(
            """INSERT INTO chat_messages 
               (id, session_id, role, content, created_at, sql_query, result_data, 
                result_metadata, processing_time_ms, error_message, metadata)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                message_id, session_id, role, content, now,
                sql_query,
                json.dumps(result_data) if result_data else None,
                json.dumps(result_metadata) if result_metadata else None,
                processing_time_ms,
                error_message,
                json.dumps(metadata or {})
            )
        )
        
        return ChatMessage(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            created_at=now,
            sql_query=sql_query,
            result_data=result_data,
            result_metadata=result_metadata,
            processing_time_ms=processing_time_ms,
            error_message=error_message,
            metadata=metadata
        )
    
    @staticmethod
    def get_messages(session_id: str, limit: int = 100) -> List[ChatMessage]:
        """Get messages for a chat session."""
        results = InternalDB.execute_query(
            """SELECT id, session_id, role, content, created_at, sql_query,
                      result_data, result_metadata, processing_time_ms, error_message, metadata
               FROM chat_messages
               WHERE session_id = %s
               ORDER BY created_at ASC
               LIMIT %s""",
            (session_id, limit),
            fetch_all=True
        )
        
        import json
        messages = []
        for result in results:
            messages.append(ChatMessage(
                id=result['id'] if isinstance(result, dict) else result[0],
                session_id=result['session_id'] if isinstance(result, dict) else result[1],
                role=result['role'] if isinstance(result, dict) else result[2],
                content=result['content'] if isinstance(result, dict) else result[3],
                created_at=result['created_at'] if isinstance(result, dict) else result[4],
                sql_query=result['sql_query'] if isinstance(result, dict) else result[5],
                result_data=json.loads(result['result_data'] if isinstance(result, dict) else result[6]) if result[6 if not isinstance(result, dict) else 'result_data'] else None,
                result_metadata=json.loads(result['result_metadata'] if isinstance(result, dict) else result[7]) if result[7 if not isinstance(result, dict) else 'result_metadata'] else None,
                processing_time_ms=result['processing_time_ms'] if isinstance(result, dict) else result[8],
                error_message=result['error_message'] if isinstance(result, dict) else result[9],
                metadata=json.loads(result['metadata'] if isinstance(result, dict) else result[10]) if result[10 if not isinstance(result, dict) else 'metadata'] else {}
            ))
        
        return messages
    
    @staticmethod
    def update_session_title(session_id: str, title: str) -> None:
        """Update session title."""
        InternalDB.execute_query(
            "UPDATE chat_sessions SET title = %s, updated_at = %s WHERE id = %s",
            (title, datetime.utcnow(), session_id)
        )
    
    @staticmethod
    def archive_session(session_id: str) -> None:
        """Archive a chat session."""
        InternalDB.execute_query(
            "UPDATE chat_sessions SET is_archived = true, updated_at = %s WHERE id = %s",
            (datetime.utcnow(), session_id)
        )
    
    @staticmethod
    def delete_session(session_id: str) -> None:
        """Delete a chat session and all its messages."""
        InternalDB.execute_query(
            "DELETE FROM chat_sessions WHERE id = %s",
            (session_id,)
        )


def get_chat_manager() -> ChatSessionManager:
    """Get chat session manager instance."""
    return ChatSessionManager()
