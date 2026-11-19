"""
macOS Contacts Integration (Read-Only)
Resolves phone numbers and emails to contact names from macOS Contacts app
"""

try:
    from Contacts import CNContactStore, CNContactFetchRequest, CNContactFormatter, CNContactFormatterStyle
    from Contacts import CNLabeledValue
    CONTACTS_AVAILABLE = True
except ImportError:
    CONTACTS_AVAILABLE = False

import re
from typing import Optional, Dict


class ContactResolver:
    """Read-only access to macOS Contacts for name resolution"""
    
    def __init__(self):
        """Initialize contact resolver"""
        self.contact_cache: Dict[str, str] = {}
        self.contacts_authorized = False
        
        if not CONTACTS_AVAILABLE:
            return
        
        try:
            # Request read-only access to contacts
            self.store = CNContactStore.alloc().init()
            self.contacts_authorized = True
            self._load_contacts()
        except Exception as e:
            print(f"Warning: Could not access Contacts: {e}")
            self.contacts_authorized = False
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number for comparison
        
        Args:
            phone: Phone number string
            
        Returns:
            Normalized digits-only string
        """
        if not phone:
            return ""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        # Remove leading 1 for US numbers
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        return digits
    
    def _load_contacts(self):
        """Load all contacts from Contacts app (READ-ONLY)"""
        if not self.contacts_authorized:
            return
        
        try:
            # Create fetch request
            keys = [
                "givenName",
                "familyName", 
                "organizationName",
                "phoneNumbers",
                "emailAddresses"
            ]
            
            # Fetch all contacts (read-only)
            contacts = self.store.unifiedContactsMatchingPredicate_keysToFetch_error_(
                None, keys, None
            )[0]
            
            # Build lookup cache
            for contact in contacts:
                # Get formatted name
                name_parts = []
                if contact.givenName():
                    name_parts.append(contact.givenName())
                if contact.familyName():
                    name_parts.append(contact.familyName())
                
                display_name = " ".join(name_parts) if name_parts else contact.organizationName()
                
                if not display_name:
                    continue
                
                # Index by phone numbers
                if contact.phoneNumbers():
                    for phone_number in contact.phoneNumbers():
                        number_str = phone_number.value().stringValue()
                        normalized = self._normalize_phone(number_str)
                        if normalized:
                            self.contact_cache[normalized] = display_name
                            # Also cache the raw number
                            self.contact_cache[number_str] = display_name
                
                # Index by email
                if contact.emailAddresses():
                    for email in contact.emailAddresses():
                        email_str = email.value()
                        if email_str:
                            self.contact_cache[email_str.lower()] = display_name
            
            print(f"Loaded {len(self.contact_cache)} contact mappings")
            
        except Exception as e:
            print(f"Warning: Failed to load contacts: {e}")
    
    def get_contact_name(self, identifier: str) -> Optional[str]:
        """
        Get contact name for phone number or email (READ-ONLY lookup)
        
        Args:
            identifier: Phone number or email address
            
        Returns:
            Contact name if found, None otherwise
        """
        if not identifier or not self.contacts_authorized:
            return None
        
        # Try direct lookup
        if identifier in self.contact_cache:
            return self.contact_cache[identifier]
        
        # Try normalized phone lookup
        if '@' not in identifier:
            normalized = self._normalize_phone(identifier)
            if normalized in self.contact_cache:
                return self.contact_cache[normalized]
        else:
            # Email - try lowercase
            lower = identifier.lower()
            if lower in self.contact_cache:
                return self.contact_cache[lower]
        
        return None
    
    def is_available(self) -> bool:
        """Check if Contacts integration is available and authorized"""
        return CONTACTS_AVAILABLE and self.contacts_authorized


# Global singleton instance
_contact_resolver = None


def get_contact_resolver() -> ContactResolver:
    """Get or create the global ContactResolver instance"""
    global _contact_resolver
    if _contact_resolver is None:
        _contact_resolver = ContactResolver()
    return _contact_resolver
