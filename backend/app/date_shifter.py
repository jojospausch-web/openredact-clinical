"""
Date-shifting mechanism for anonymization.
Shifts dates by a fixed offset while preserving temporal relationships.
"""
from datetime import datetime, timedelta
import re
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DateShifter:
    """Shifts dates by a fixed offset while preserving temporal relationships"""
    
    def __init__(self, shift_months: int = 0, shift_days: int = 0):
        """
        Initialize date shifter
        
        Args:
            shift_months: Number of months to shift (can be negative)
            shift_days: Number of days to shift (can be negative)
        """
        self.shift_months = shift_months
        self.shift_days = shift_days
    
    def shift_date(self, date_str: str, date_groups: tuple = None) -> str:
        """
        Shift a date string by the configured offset
        
        Args:
            date_str: Original date string (e.g., "15.03.2024")
            date_groups: Regex groups from date pattern match
            
        Returns:
            Shifted date string in same format
        """
        try:
            # Parse date
            parsed_date = self._parse_date(date_str, date_groups)
            if not parsed_date:
                return date_str  # Return unchanged if parsing fails
            
            # Apply shift
            shifted_date = self._apply_shift(parsed_date)
            
            # Format back to original format
            return self._format_date(shifted_date, date_str)
            
        except Exception as e:
            # If anything fails, return original (safe fallback)
            logger.warning(f"Failed to shift date '{date_str}': {e}")
            return date_str
    
    def _parse_date(self, date_str: str, date_groups: tuple = None) -> Optional[datetime]:
        """Parse date string to datetime object"""
        
        # Try DD.MM.YYYY format
        if '.' in date_str:
            parts = date_str.split('.')
            if len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                # Handle 2-digit years
                if year < 100:
                    year += 2000 if year < 50 else 1900
                return datetime(year, month, day)
        
        # Try DD/MM/YYYY or DD-MM-YYYY
        for sep in ['/', '-']:
            if sep in date_str:
                parts = date_str.split(sep)
                if len(parts) == 3:
                    # Check if YYYY-MM-DD (ISO) or DD-MM-YYYY
                    if len(parts[0]) == 4:  # ISO format
                        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    else:  # European format
                        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    
                    if year < 100:
                        year += 2000 if year < 50 else 1900
                    return datetime(year, month, day)
        
        return None
    
    def _apply_shift(self, date: datetime) -> datetime:
        """Apply month and day shifts to a date"""
        
        # Shift months
        if self.shift_months != 0:
            new_month = date.month + self.shift_months
            new_year = date.year
            
            # Handle year overflow/underflow
            while new_month > 12:
                new_month -= 12
                new_year += 1
            while new_month < 1:
                new_month += 12
                new_year -= 1
            
            # Handle day overflow (e.g., Jan 31 + 1 month = Feb 31 → Feb 28/29)
            try:
                date = date.replace(year=new_year, month=new_month)
            except ValueError:
                # Day doesn't exist in target month (e.g., Feb 31)
                # Use last day of month
                if new_month == 2:
                    day = 29 if self._is_leap_year(new_year) else 28
                elif new_month in [4, 6, 9, 11]:
                    day = 30
                else:
                    day = 31
                date = date.replace(year=new_year, month=new_month, day=day)
        
        # Shift days
        if self.shift_days != 0:
            date = date + timedelta(days=self.shift_days)
        
        return date
    
    def _format_date(self, date: datetime, original: str) -> str:
        """Format datetime back to original format"""
        
        # Detect original format
        if '.' in original:
            # DD.MM.YYYY or DD.MM.YY
            if len(original.split('.')[-1]) == 2:
                return date.strftime('%d.%m.%y')
            else:
                return date.strftime('%d.%m.%Y')
        
        elif '/' in original:
            return date.strftime('%d/%m/%Y')
        
        elif '-' in original:
            # Check if ISO (YYYY-MM-DD) or European (DD-MM-YYYY)
            if original.startswith(('19', '20')):
                return date.strftime('%Y-%m-%d')
            else:
                return date.strftime('%d-%m-%Y')
        
        # Default
        return date.strftime('%d.%m.%Y')
    
    def _is_leap_year(self, year: int) -> bool:
        """Check if year is leap year"""
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


# Global instance
date_shifter = DateShifter()
