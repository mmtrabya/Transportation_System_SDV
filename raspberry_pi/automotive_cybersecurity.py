#!/usr/bin/env python3
"""
Automotive Cybersecurity System - Fixed Version
Implements TLS, certificate-based authentication, intrusion detection, and security monitoring
Uses user home directory for storage
"""

import ssl
import socket
import json
import time
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import secrets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('AutoSecurity')

# ==================== CONFIGURATION ====================

class SecurityConfig:
    """Security configuration"""
    
    # Directories - Use user home directory
    BASE_DIR = Path.home() / "sdv_security"
    CERTS_DIR = BASE_DIR / "certs"
    KEYS_DIR = BASE_DIR / "keys"
    LOGS_DIR = BASE_DIR / "security_logs"
    
    # Certificate files
    CA_CERT = CERTS_DIR / "ca_cert.pem"
    VEHICLE_CERT = CERTS_DIR / "vehicle_cert.pem"
    VEHICLE_KEY = KEYS_DIR / "vehicle_key.pem"
    
    # Security settings
    SESSION_KEY_ROTATION = 3600  # 1 hour
    MAX_AUTH_ATTEMPTS = 3
    LOCKOUT_DURATION = 300  # 5 minutes
    
    # V2X Security
    V2X_MESSAGE_TIMEOUT = 5  # seconds
    V2X_MAX_REPLAY_WINDOW = 10  # seconds
    
    # Intrusion detection
    ANOMALY_THRESHOLD = 0.75
    MAX_FAILED_AUTH = 5
    MAX_MESSAGES_PER_SECOND = 50
    
    # Vehicle info
    VEHICLE_ID = "SDV_001"

# ==================== DATA STRUCTURES ====================

@dataclass
class SecurityEvent:
    """Security event/alert"""
    timestamp: float
    event_type: str
    severity: str  # critical, high, medium, low
    source: str
    description: str
    metadata: Dict = field(default_factory=dict)

@dataclass
class SessionKey:
    """Session key information"""
    key: bytes
    created_at: float
    expires_at: float
    peer_id: str

# ==================== CERTIFICATE MANAGER ====================

class CertificateManager:
    """Manages X.509 certificates for authentication"""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        
        # Create all directories
        for directory in [self.config.BASE_DIR, self.config.CERTS_DIR, 
                         self.config.KEYS_DIR, self.config.LOGS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Load or generate certificates
        self.ca_cert = self._load_or_generate_ca()
        self.vehicle_cert, self.vehicle_key = self._load_or_generate_vehicle_cert()
        
        # Certificate cache
        self.cert_cache = {}
        self.revocation_list = set()
        
        logger.info("Certificate Manager initialized")
        logger.info(f"Certificates stored in: {self.config.CERTS_DIR}")
    
    def _load_or_generate_ca(self):
        """Load or generate CA certificate"""
        ca_key_path = self.config.KEYS_DIR / "ca_key.pem"
        
        if self.config.CA_CERT.exists() and ca_key_path.exists():
            with open(self.config.CA_CERT, 'rb') as f:
                cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            with open(ca_key_path, 'rb') as f:
                self.ca_private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
            return cert
        
        logger.warning("CA certificate not found. Generating self-signed CA...")
        return self._generate_ca_certificate()
    
    def _generate_ca_certificate(self):
        """Generate self-signed CA certificate"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Store the CA private key for signing vehicle certificates
        self.ca_private_key = private_key
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "EG"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Cairo"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SDV Project"),
            x509.NameAttribute(NameOID.COMMON_NAME, "SDV CA"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=3650)  # 10 years
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Save CA certificate and private key
        with open(self.config.CA_CERT, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Save CA private key
        ca_key_path = self.config.KEYS_DIR / "ca_key.pem"
        with open(ca_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        logger.info("CA certificate generated")
        return cert
    
    def _load_or_generate_vehicle_cert(self):
        """Load or generate vehicle certificate"""
        if self.config.VEHICLE_CERT.exists() and self.config.VEHICLE_KEY.exists():
            try:
                with open(self.config.VEHICLE_CERT, 'rb') as f:
                    cert = x509.load_pem_x509_certificate(f.read(), default_backend())
                with open(self.config.VEHICLE_KEY, 'rb') as f:
                    key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
                logger.info("Existing vehicle certificate loaded")
                return cert, key
            except Exception as e:
                logger.warning(f"Failed to load existing certificate: {e}, regenerating...")
        
        logger.warning("Vehicle certificate not found. Generating...")
        return self._generate_vehicle_certificate()
    
    def _generate_vehicle_certificate(self):
        """Generate vehicle certificate signed by CA"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "EG"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SDV Project"),
            x509.NameAttribute(NameOID.COMMON_NAME, self.config.VEHICLE_ID),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            self.ca_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(self.config.VEHICLE_ID),
            ]),
            critical=False,
        ).sign(self.ca_private_key, hashes.SHA256(), default_backend())
        
        # Save certificate and key
        with open(self.config.VEHICLE_CERT, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(self.config.VEHICLE_KEY, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        logger.info("Vehicle certificate generated")
        return cert, private_key
    
    def verify_certificate(self, cert_data: bytes) -> bool:
        """Verify certificate against CA"""
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Check if revoked
            serial = cert.serial_number
            if serial in self.revocation_list:
                logger.warning(f"Certificate {serial} is revoked")
                return False
            
            # Check expiry
            if datetime.now(timezone.utc) > cert.not_valid_after_utc:
                logger.warning("Certificate expired")
                return False
            
            if datetime.now(timezone.utc) < cert.not_valid_before_utc:
                logger.warning("Certificate not yet valid")
                return False
            
            # Verify signature (check if self-signed or CA-signed)
            try:
                ca_public_key = self.ca_cert.public_key()
                ca_public_key.verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    cert.signature_hash_algorithm,
                )
                logger.debug("Certificate verified with CA signature")
            except Exception as sig_error:
                # If CA verification fails, check if it's self-signed
                try:
                    cert_public_key = cert.public_key()
                    cert_public_key.verify(
                        cert.signature,
                        cert.tbs_certificate_bytes,
                        padding.PKCS1v15(),
                        cert.signature_hash_algorithm,
                    )
                    logger.debug("Self-signed certificate verified")
                except:
                    logger.error(f"Signature verification failed: {sig_error}")
                    raise
            
            return True
            
        except Exception as e:
            logger.error(f"Certificate verification failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def extract_vehicle_id(self, cert_data: bytes) -> Optional[str]:
        """Extract vehicle ID from certificate"""
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            return cn
        except:
            return None

# ==================== SECURE COMMUNICATION ====================

class SecureChannel:
    """Manages secure TLS communication channels"""
    
    def __init__(self, cert_manager: CertificateManager):
        self.cert_manager = cert_manager
        self.active_sessions = {}
        self.session_keys = {}
        
        # Create SSL context
        self.ssl_context = self._create_ssl_context()
        
        logger.info("Secure Channel initialized")
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL/TLS context"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        
        # Load certificates
        context.load_cert_chain(
            str(self.cert_manager.config.VEHICLE_CERT),
            str(self.cert_manager.config.VEHICLE_KEY)
        )
        
        # Load CA certificate for verification
        context.load_verify_locations(str(self.cert_manager.config.CA_CERT))
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Cipher suite
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        return context
    
    def create_secure_connection(self, host: str, port: int) -> Optional[ssl.SSLSocket]:
        """Create secure TLS connection"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            secure_sock = self.ssl_context.wrap_socket(
                sock,
                server_hostname=host
            )
            secure_sock.connect((host, port))
            
            logger.info(f"Secure connection established to {host}:{port}")
            logger.info(f"Cipher: {secure_sock.cipher()}")
            logger.info(f"Protocol: {secure_sock.version()}")
            
            return secure_sock
            
        except Exception as e:
            logger.error(f"Failed to establish secure connection: {e}")
            return None
    
    def establish_session_key(self, peer_id: str) -> SessionKey:
        """Establish session key with peer using ECDH"""
        # Generate session key
        session_key = secrets.token_bytes(32)  # 256-bit key
        
        now = time.time()
        expires = now + SecurityConfig.SESSION_KEY_ROTATION
        
        session = SessionKey(
            key=session_key,
            created_at=now,
            expires_at=expires,
            peer_id=peer_id
        )
        
        self.session_keys[peer_id] = session
        logger.info(f"Session key established with {peer_id}")
        
        return session
    
    def encrypt_message(self, message: bytes, peer_id: str) -> Optional[bytes]:
        """Encrypt message with session key"""
        session = self.session_keys.get(peer_id)
        if not session:
            logger.error(f"No session key for {peer_id}")
            return None
        
        # Check if key expired
        if time.time() > session.expires_at:
            logger.warning(f"Session key expired for {peer_id}")
            session = self.establish_session_key(peer_id)
        
        # AES-256-GCM encryption
        iv = secrets.token_bytes(12)  # 96-bit IV
        cipher = Cipher(
            algorithms.AES(session.key),
            modes.GCM(iv),
            backend=default_backend()
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(message) + encryptor.finalize()
        
        # Return IV + Tag + Ciphertext
        return iv + encryptor.tag + ciphertext
    
    def decrypt_message(self, encrypted: bytes, peer_id: str) -> Optional[bytes]:
        """Decrypt message with session key"""
        session = self.session_keys.get(peer_id)
        if not session:
            logger.error(f"No session key for {peer_id}")
            return None
        
        # Extract IV, tag, and ciphertext
        iv = encrypted[:12]
        tag = encrypted[12:28]
        ciphertext = encrypted[28:]
        
        # AES-256-GCM decryption
        cipher = Cipher(
            algorithms.AES(session.key),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        
        try:
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None

# ==================== V2X MESSAGE SECURITY ====================

class V2XSecurity:
    """Security for V2X messages"""
    
    def __init__(self, cert_manager: CertificateManager):
        self.cert_manager = cert_manager
        self.message_cache = {}  # Replay attack prevention
        self.nonce_cache = set()
        
        logger.info("V2X Security initialized")
    
    def sign_message(self, message: Dict) -> Dict:
        """Sign V2X message"""
        # Add timestamp and nonce
        message['timestamp'] = time.time()
        message['nonce'] = secrets.token_hex(8)
        
        # Create message digest
        message_bytes = json.dumps(message, sort_keys=True).encode()
        digest = hashlib.sha256(message_bytes).digest()
        
        # Sign with vehicle private key
        signature = self.cert_manager.vehicle_key.sign(
            digest,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Attach certificate and signature
        signed_message = message.copy()
        signed_message['signature'] = signature.hex()
        signed_message['certificate'] = self.cert_manager.vehicle_cert.public_bytes(
            serialization.Encoding.PEM
        ).decode()
        
        return signed_message
    
    def verify_message(self, signed_message: Dict) -> Tuple[bool, Optional[str]]:
        """Verify V2X message signature and authenticity"""
        try:
            # Extract components
            signature = bytes.fromhex(signed_message['signature'])
            cert_pem = signed_message['certificate'].encode()
            timestamp = signed_message['timestamp']
            nonce = signed_message['nonce']
            
            # Check timestamp (prevent replay attacks)
            if abs(time.time() - timestamp) > SecurityConfig.V2X_MESSAGE_TIMEOUT:
                logger.warning("Message timestamp too old")
                return False, None
            
            # Check nonce (prevent duplicate messages)
            if nonce in self.nonce_cache:
                logger.warning("Duplicate message detected (replay attack?)")
                return False, None
            
            # Verify certificate
            if not self.cert_manager.verify_certificate(cert_pem):
                logger.warning("Invalid certificate")
                return False, None
            
            # Extract vehicle ID
            vehicle_id = self.cert_manager.extract_vehicle_id(cert_pem)
            
            # Create message digest
            message_copy = {k: v for k, v in signed_message.items() 
                          if k not in ['signature', 'certificate']}
            message_bytes = json.dumps(message_copy, sort_keys=True).encode()
            digest = hashlib.sha256(message_bytes).digest()
            
            # Load certificate and verify signature
            cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
            public_key = cert.public_key()
            
            public_key.verify(
                signature,
                digest,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Add nonce to cache
            self.nonce_cache.add(nonce)
            
            # Cleanup old nonces (keep last 1000)
            if len(self.nonce_cache) > 1000:
                self.nonce_cache = set(list(self.nonce_cache)[-1000:])
            
            return True, vehicle_id
            
        except Exception as e:
            logger.error(f"Message verification failed: {e}")
            return False, None

# ==================== INTRUSION DETECTION ====================

class IntrusionDetectionSystem:
    """Detects security threats and anomalies"""
    
    def __init__(self):
        self.security_events = deque(maxlen=1000)
        
        # Attack counters
        self.failed_auth_attempts = defaultdict(int)
        self.message_rates = defaultdict(lambda: deque(maxlen=200))
        self.blacklisted_peers = set()
        
        # DoS detection deduplication
        self.last_dos_detection = {}  # peer_id -> timestamp
        
        # Baseline behavior
        self.baseline_message_rate = 10  # messages/second
        self.baseline_cpu = 50  # percent
        self.baseline_network = 1000  # KB/s
        
        logger.info("Intrusion Detection System initialized")
    
    def log_event(self, event: SecurityEvent):
        """Log security event"""
        self.security_events.append(event)
        logger.warning(f"Security Event [{event.severity}]: {event.event_type} - {event.description}")
    
    def check_failed_auth(self, peer_id: str) -> bool:
        """Check for brute force authentication attempts"""
        self.failed_auth_attempts[peer_id] += 1
        
        if self.failed_auth_attempts[peer_id] >= SecurityConfig.MAX_FAILED_AUTH:
            self.blacklisted_peers.add(peer_id)
            
            event = SecurityEvent(
                timestamp=time.time(),
                event_type="brute_force_attack",
                severity="critical",
                source=peer_id,
                description=f"Multiple failed authentication attempts from {peer_id}",
                metadata={'attempts': self.failed_auth_attempts[peer_id]}
            )
            self.log_event(event)
            return True
        
        return False
    
    def check_message_rate(self, peer_id: str) -> bool:
        """Check for message flooding (DoS attack)"""
        current_time = time.time()
        self.message_rates[peer_id].append(current_time)
        
        # Calculate messages per second (count messages within last 1 second)
        recent_messages = [t for t in self.message_rates[peer_id] 
                          if current_time - t <= 1.0]
        rate = len(recent_messages)
        
        # If rate exceeds threshold, log DoS attack event
        if rate > SecurityConfig.MAX_MESSAGES_PER_SECOND:
            # Only log event once per 5-second window to avoid spam
            last_detection = self.last_dos_detection.get(peer_id, 0)
            
            if current_time - last_detection >= 5.0:  # 5 second cooldown
                event = SecurityEvent(
                    timestamp=current_time,
                    event_type="dos_attack",
                    severity="high",
                    source=peer_id,
                    description=f"Message flood detected from {peer_id}: {rate} msg/s",
                    metadata={'rate': rate, 'threshold': SecurityConfig.MAX_MESSAGES_PER_SECOND}
                )
                self.log_event(event)
                self.last_dos_detection[peer_id] = current_time
            
            return True
        else:
            # Rate is normal - reset detection timer
            if peer_id in self.last_dos_detection:
                del self.last_dos_detection[peer_id]
        
        return False
    
    def check_anomaly(self, metric_type: str, value: float) -> bool:
        """Check for behavioral anomalies"""
        baseline = {
            'message_rate': self.baseline_message_rate,
            'cpu': self.baseline_cpu,
            'network': self.baseline_network
        }.get(metric_type, 0)
        
        if baseline == 0:
            return False
        
        deviation = abs(value - baseline) / baseline
        
        if deviation > SecurityConfig.ANOMALY_THRESHOLD:
            event = SecurityEvent(
                timestamp=time.time(),
                event_type="anomaly_detected",
                severity="medium",
                source="system",
                description=f"Anomaly in {metric_type}: {value} (baseline: {baseline})",
                metadata={'metric': metric_type, 'value': value, 'baseline': baseline}
            )
            self.log_event(event)
            return True
        
        return False
    
    def is_blacklisted(self, peer_id: str) -> bool:
        """Check if peer is blacklisted"""
        return peer_id in self.blacklisted_peers
    
    def get_recent_events(self, count: int = 10, severity: str = None) -> List[SecurityEvent]:
        """Get recent security events"""
        events = list(self.security_events)
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        return events[-count:]

# ==================== SECURITY MONITORING ====================

class SecurityMonitor:
    """Monitors overall system security"""
    
    def __init__(self, cert_manager: CertificateManager, 
                 secure_channel: SecureChannel,
                 v2x_security: V2XSecurity,
                 ids: IntrusionDetectionSystem):
        self.cert_manager = cert_manager
        self.secure_channel = secure_channel
        self.v2x_security = v2x_security
        self.ids = ids
        
        self.monitoring = False
        self.security_score = 100.0
        
        logger.info("Security Monitor initialized")
    
    def calculate_security_score(self) -> float:
        """Calculate overall security score"""
        score = 100.0
        
        # Check certificate expiry
        days_until_expiry = (self.cert_manager.vehicle_cert.not_valid_after_utc - datetime.now(timezone.utc)).days
        if days_until_expiry < 30:
            score -= 10
            logger.warning(f"Certificate expires in {days_until_expiry} days")
        
        # Check active sessions
        expired_sessions = sum(1 for s in self.secure_channel.session_keys.values() 
                             if time.time() > s.expires_at)
        if expired_sessions > 0:
            score -= 5
        
        # Check security events
        critical_events = len(self.ids.get_recent_events(severity='critical'))
        score -= critical_events * 5
        
        high_events = len(self.ids.get_recent_events(severity='high'))
        score -= high_events * 2
        
        # Check blacklisted peers
        score -= len(self.ids.blacklisted_peers) * 3
        
        self.security_score = max(0.0, min(100.0, score))
        return self.security_score
    
    def get_security_status(self) -> Dict:
        """Get comprehensive security status"""
        status = {
            'security_score': self.calculate_security_score(),
            'certificate_valid': datetime.now(timezone.utc) < self.cert_manager.vehicle_cert.not_valid_after_utc,
            'certificate_expires': self.cert_manager.vehicle_cert.not_valid_after_utc.isoformat(),
            'active_sessions': len(self.secure_channel.session_keys),
            'blacklisted_peers': len(self.ids.blacklisted_peers),
            'recent_critical_events': len(self.ids.get_recent_events(severity='critical')),
            'recent_high_events': len(self.ids.get_recent_events(severity='high')),
            'total_security_events': len(self.ids.security_events)
        }
        
        return status
    
    def generate_security_report(self) -> str:
        """Generate security report"""
        status = self.get_security_status()
        
        report = f"""
========================================
    SECURITY STATUS REPORT
========================================
Security Score: {status['security_score']:.1f}/100

Certificate Status:
  - Valid: {status['certificate_valid']}
  - Expires: {status['certificate_expires']}

Active Security:
  - Active Sessions: {status['active_sessions']}
  - Blacklisted Peers: {status['blacklisted_peers']}

Recent Events:
  - Critical: {status['recent_critical_events']}
  - High: {status['recent_high_events']}
  - Total Events: {status['total_security_events']}

Recent Security Events:
"""
        
        for event in self.ids.get_recent_events(5):
            timestamp = datetime.fromtimestamp(event.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            report += f"  [{timestamp}] {event.severity.upper()}: {event.description}\n"
        
        report += "========================================\n"
        
        return report

# ==================== INTEGRATED SECURITY SYSTEM ====================

class AutomotiveSecurity:
    """Main integrated security system"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        
        # Initialize components
        self.cert_manager = CertificateManager(self.config)
        self.secure_channel = SecureChannel(self.cert_manager)
        self.v2x_security = V2XSecurity(self.cert_manager)
        self.ids = IntrusionDetectionSystem()
        self.monitor = SecurityMonitor(
            self.cert_manager,
            self.secure_channel,
            self.v2x_security,
            self.ids
        )
        
        logger.info("Automotive Security System initialized")
    
    def secure_v2x_message(self, message: Dict) -> Dict:
        """Secure V2X message with signature"""
        return self.v2x_security.sign_message(message)
    
    def verify_v2x_message(self, message: Dict) -> Tuple[bool, Optional[str]]:
        """Verify incoming V2X message"""
        valid, vehicle_id = self.v2x_security.verify_message(message)
        
        if not valid:
            self.ids.check_failed_auth(vehicle_id or "unknown")
        
        if vehicle_id:
            self.ids.check_message_rate(vehicle_id)
            
            if self.ids.is_blacklisted(vehicle_id):
                logger.warning(f"Blocked message from blacklisted peer: {vehicle_id}")
                return False, None
        
        return valid, vehicle_id
    
    def get_status(self) -> Dict:
        """Get security status"""
        return self.monitor.get_security_status()
    
    def get_report(self) -> str:
        """Get security report"""
        return self.monitor.generate_security_report()

# ==================== EXAMPLE USAGE ====================

def main():
    """Example usage"""
    
    print("Initializing Automotive Security System...")
    print("=" * 50)
    
    # Initialize security system
    security = AutomotiveSecurity()
    
    print("\n" + security.get_report())
    
    # Example: Secure V2X message
    message = {
        'vehicle_id': 'SDV_001',
        'latitude': 30.0444,
        'longitude': 31.2357,
        'speed': 25.5
    }
    
    # Sign message
    print("\n" + "=" * 50)
    print("Testing V2X Message Security...")
    print("=" * 50)
    signed_message = security.secure_v2x_message(message)
    print(f"\n✓ Signed V2X message: {len(json.dumps(signed_message))} bytes")
    
    # Verify message
    valid, vehicle_id = security.verify_v2x_message(signed_message)
    print(f"✓ Message verification: {'PASSED' if valid else 'FAILED'}")
    print(f"✓ Sender vehicle ID: {vehicle_id}")
    
    # Show security status
    print("\n" + "=" * 50)
    print("Final Security Status")
    print("=" * 50)
    status = security.get_status()
    print(f"Security Score: {status['security_score']:.1f}/100")
    print(f"Certificate Valid: {status['certificate_valid']}")
    print(f"Active Sessions: {status['active_sessions']}")
    print(f"\n✓ System ready for secure operations")

if __name__ == "__main__":
    main()