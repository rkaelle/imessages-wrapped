"""Read Contacts through Apple's API. Never creates a save request."""
import re
import threading


def normalize(value):
    value = str(value or '').strip()
    if '@' in value:
        return value.casefold()
    digits = re.sub(r'\D', '', value)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits or value.casefold()


class Contacts:
    def __init__(self):
        self.mapping = {}
        self.state = 'unavailable'
        self.detail = 'Install the macOS Contacts bridge, then restart the server.'
        self.count = 0
        self.lock = threading.RLock()
        self.refresh()

    def refresh(self):
        with self.lock:
            self.mapping = {}
            self.count = 0
            try:
                import Contacts as C
                status = int(C.CNContactStore.authorizationStatusForEntityType_(C.CNEntityTypeContacts))
                self.state = {0:'not_requested',1:'restricted',2:'denied',3:'authorized',4:'limited'}.get(status,'unavailable')
                if self.state not in ('authorized','limited'):
                    self.detail = {'not_requested':'Allow Contacts to show names instead of numbers.', 'restricted':'Contacts access is restricted by macOS.', 'denied':'Enable Contacts access for the app running this server in System Settings → Privacy & Security → Contacts.'}.get(self.state,'Contacts is unavailable.')
                    return self.status()
                store = C.CNContactStore.alloc().init()
                request = C.CNContactFetchRequest.alloc().initWithKeysToFetch_([
                    C.CNContactIdentifierKey,C.CNContactGivenNameKey,C.CNContactFamilyNameKey,
                    C.CNContactOrganizationNameKey,C.CNContactPhoneNumbersKey,C.CNContactEmailAddressesKey])
                mapping = {}
                count = 0
                def receive(contact, stop):
                    nonlocal count
                    name = ' '.join(str(x) for x in [contact.givenName(),contact.familyName()] if x).strip() or str(contact.organizationName() or '')
                    if not name:
                        return
                    count += 1
                    entry = {'name':name,'key':str(contact.identifier())}
                    for phone in contact.phoneNumbers():
                        mapping[normalize(phone.value().stringValue())] = entry
                    for email in contact.emailAddresses():
                        mapping[normalize(email.value())] = entry
                ok, error = store.enumerateContactsWithFetchRequest_error_usingBlock_(request,None,receive)
                if not ok:
                    raise RuntimeError('macOS could not read Contacts. Check Contacts permission and retry.')
                self.mapping = mapping
                self.count = count
                self.detail = f'{count:,} named contacts loaded' + (' (limited access).' if self.state == 'limited' else '.')
            except ImportError:
                self.state = 'unavailable'
                self.detail = 'The macOS Contacts bridge is not installed.'
            except Exception:
                self.state = 'error'
                self.detail = 'Contacts could not be loaded. Check macOS Contacts permission, then retry.'
            return self.status()

    def request_access(self):
        # Called only by the explicit Allow Contacts button, never by page load.
        try:
            import Contacts as C
            if int(C.CNContactStore.authorizationStatusForEntityType_(C.CNEntityTypeContacts)) == 0:
                done = threading.Event()
                C.CNContactStore.alloc().init().requestAccessForEntityType_completionHandler_(C.CNEntityTypeContacts, lambda granted,error: done.set())
                done.wait(45)
        except Exception:
            pass
        return self.refresh()

    def status(self):
        return {'state':self.state,'detail':self.detail,'loaded':self.count}

    def resolve(self, identifier):
        return self.mapping.get(normalize(identifier))
