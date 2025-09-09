"""
Database models for PyBOG using SQLAlchemy
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Session(Base):
    __tablename__ = 'sessions'
    
    # Use external session_id as the primary key (matches existing DB and workflows)
    session_id = Column(String(255), primary_key=True, index=True)
    name = Column(String(255), nullable=False, default='New Session')
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True), default=func.now())
    state = Column(String(50), default='idle')
    # Attribute name 'metadata' is reserved in SQLAlchemy declarative; map to DB column 'metadata'
    meta = Column('metadata', JSON, default={})
    
    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    files = relationship("File", back_populates="session", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="session", cascade="all, delete-orphan")
    bog_files = relationship("BOGFile", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(String(255), unique=True, nullable=False)
    session_id = Column(String(255), ForeignKey('sessions.session_id', ondelete='CASCADE'), nullable=False)
    type = Column(String(50), nullable=False)  # user, assistant, system
    message_type = Column(String(50))  # status, analysis, artifact, processing, error
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    meta = Column('metadata', JSON, default={})
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    files = relationship("File", back_populates="message")


class File(Base):
    __tablename__ = 'files'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(String(255), unique=True, nullable=False)
    session_id = Column(String(255), ForeignKey('sessions.session_id', ondelete='CASCADE'), nullable=False)
    message_id = Column(String(255), ForeignKey('messages.message_id', ondelete='SET NULL'), nullable=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(100))
    file_size = Column(BigInteger)
    storage_path = Column(Text)
    upload_time = Column(DateTime(timezone=True), default=func.now())
    meta = Column('metadata', JSON, default={})
    
    # Relationships
    session = relationship("Session", back_populates="files")
    message = relationship("Message", back_populates="files")


class AnalysisResult(Base):
    __tablename__ = 'analysis_results'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(String(255), unique=True, nullable=False)
    session_id = Column(String(255), ForeignKey('sessions.session_id', ondelete='CASCADE'), nullable=False)
    message_id = Column(String(255), ForeignKey('messages.message_id', ondelete='SET NULL'), nullable=True)
    analysis_data = Column(JSON, nullable=False)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    session = relationship("Session", back_populates="analysis_results")


class BOGFile(Base):
    __tablename__ = 'bog_files'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bog_id = Column(String(255), unique=True, nullable=False)
    session_id = Column(String(255), ForeignKey('sessions.session_id', ondelete='CASCADE'), nullable=False)
    message_id = Column(String(255), ForeignKey('messages.message_id', ondelete='SET NULL'), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text)
    download_url = Column(Text)
    content = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=func.now())
    meta = Column('metadata', JSON, default={})
    
    # Relationships
    session = relationship("Session", back_populates="bog_files")
