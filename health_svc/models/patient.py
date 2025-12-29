"""
Domain model for patients.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class Patient:
    """Model representing a patient in the system."""
    
    id: int
    name: str
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert patient to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }
    
    @classmethod
    def from_row(cls, row: tuple) -> 'Patient':
        """
        Create a Patient from a database row tuple.
        
        Args:
            row: Tuple of (id, name, created_at) from database query.
        
        Returns:
            Patient instance.
        """
        created_at = row[2]
        if isinstance(created_at, str):
            # Handle SQLite datetime strings
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                # Fallback for different datetime formats
                created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        
        return cls(
            id=row[0],
            name=row[1],
            created_at=created_at
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Patient':
        """
        Create a Patient from a dictionary.
        
        Args:
            data: Dictionary with id, name, and created_at keys.
        
        Returns:
            Patient instance.
        """
        created_at = data["created_at"]
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=created_at
        )

