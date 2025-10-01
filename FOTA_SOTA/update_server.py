#!/usr/bin/env python3
"""
FOTA/SOTA Update Server
Flask-based server for managing and distributing OTA updates
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('UpdateServer')

# ==================== CONFIGURATION ====================

class ServerConfig:
    """Server configuration"""
    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = True
    
    # Directories
    BASE_DIR = Path('/opt/update_server')
    UPDATES_DIR = BASE_DIR / 'updates'
    KEYS_DIR = BASE_DIR / 'keys'
    MANIFESTS_DIR = BASE_DIR / 'manifests'
    
    # Files
    PRIVATE_KEY_FILE = KEYS_DIR / 'private_key.pem'
    PUBLIC_KEY_FILE = KEYS_DIR / 'public_key.pem'
    
    # Update catalog
    CATALOG_FILE = BASE_DIR / 'update_catalog.json'

# ==================== CRYPTO MANAGER ====================

class ServerCryptoManager:
    """Server-side cryptographic operations"""
    
    def __init__(self, keys_dir: Path):
        self.keys_dir = keys_dir
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        self.private_key_file = self.keys_dir / 'private_key.pem'
        self.public_key_file = self.keys_dir / 'public_key.pem'
        
        # Load or generate keys
        if not self.private_key_file.exists():
            logger.info("Generating new RSA key pair...")
            self._generate_keys()
        
        self.private_key = self._load_private_key()
        self.public_key = self._load_public_key()
    
    def _generate_keys(self):
        """Generate RSA key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        # Save private key
        with open(self.private_key_file, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Save public key
        with open(self.public_key_file, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        
        logger.info("RSA keys generated successfully")
    
    def _load_private_key(self):
        """Load private key"""
        with open(self.private_key_file, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    
    def _load_public_key(self):
        """Load public key"""
        with open(self.public_key_file, 'rb') as f:
            return serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
    
    def sign_file(self, file_path: Path) -> str:
        """Sign file and return signature as hex string"""
        with open(file_path, 'rb') as f:
            data = f.read()
        
        signature = self.private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return signature.hex()
    
    @staticmethod
    def calculate_hash(file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()

# ==================== UPDATE CATALOG MANAGER ====================

class UpdateCatalog:
    """Manages update catalog"""
    
    def __init__(self, catalog_file: Path):
        self.catalog_file = catalog_file
        self.catalog = self._load_catalog()
    
    def _load_catalog(self) -> Dict:
        """Load catalog from file"""
        if self.catalog_file.exists():
            with open(self.catalog_file, 'r') as f:
                return json.load(f)
        
        return {
            'updates': {},
            'vehicles': {}
        }
    
    def save_catalog(self):
        """Save catalog to file"""
        with open(self.catalog_file, 'w') as f:
            json.dump(self.catalog, f, indent=2)
    
    def add_update(self, update_info: Dict):
        """Add update to catalog"""
        update_id = update_info['update_id']
        self.catalog['updates'][update_id] = update_info
        self.save_catalog()
        logger.info(f"Added update to catalog: {update_id}")
    
    def get_updates_for_vehicle(self, vehicle_id: str, current_versions: Dict) -> Dict:
        """Get available updates for a vehicle"""
        available_updates = {}
        
        for update_id, update_info in self.catalog['updates'].items():
            component = update_info['component']
            new_version = update_info['version']
            
            # Check if update is applicable
            current_version = current_versions.get(component, '0.0.0')
            
            # Simple version comparison (assumes semantic versioning)
            if self._compare_versions(new_version, current_version) > 0:
                # Check hardware compatibility
                hw_version = update_info.get('hardware_version', 'any')
                if hw_version == 'any' or hw_version == current_versions.get('hardware_version'):
                    available_updates[update_info['update_type']] = update_info
        
        return available_updates
    
    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare two version strings. Returns 1 if v1 > v2, -1 if v1 < v2, 0 if equal"""
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        
        for i in range(max(len(parts1), len(parts2))):
            p1 = parts1[i] if i < len(parts1) else 0
            p2 = parts2[i] if i < len(parts2) else 0
            
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        
        return 0
    
    def get_all_updates(self) -> Dict:
        """Get all updates in catalog"""
        return self.catalog['updates']

# ==================== FLASK APP ====================

app = Flask(__name__)
CORS(app)

# Initialize components
config = ServerConfig()
config.BASE_DIR.mkdir(parents=True, exist_ok=True)
config.UPDATES_DIR.mkdir(parents=True, exist_ok=True)
config.MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)

crypto = ServerCryptoManager(config.KEYS_DIR)
catalog = UpdateCatalog(config.CATALOG_FILE)

# ==================== API ENDPOINTS ====================

@app.route('/api/v1/updates/check', methods=['GET'])
def check_updates():
    """Check for available updates"""
    try:
        vehicle_id = request.args.get('vehicle_id')
        hardware_version = request.args.get('hardware_version')
        current_versions = json.loads(request.args.get('current_versions', '{}'))
        
        logger.info(f"Update check from {vehicle_id}")
        
        # Get available updates
        updates = catalog.get_updates_for_vehicle(vehicle_id, current_versions)
        
        return jsonify(updates), 200
        
    except Exception as e:
        logger.error(f"Error checking updates: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/updates/download/<update_id>', methods=['GET'])
def download_update(update_id):
    """Download update file"""
    try:
        updates = catalog.get_all_updates()
        
        if update_id not in updates:
            return jsonify({'error': 'Update not found'}), 404
        
        update_info = updates[update_id]
        file_path = config.UPDATES_DIR / update_info['filename']
        
        if not file_path.exists():
            return jsonify({'error': 'Update file not found'}), 404
        
        logger.info(f"Serving update: {update_id}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=update_info['filename']
        )
        
    except Exception as e:
        logger.error(f"Error downloading update: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/updates/upload', methods=['POST'])
def upload_update():
    """Upload new update (admin only)"""
    try:
        # Check authentication (implement proper auth in production)
        auth_token = request.headers.get('Authorization')
        if auth_token != 'Bearer admin_token_123':
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Get file and metadata
        file = request.files.get('file')
        metadata = json.loads(request.form.get('metadata'))
        
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        
        # Save file
        filename = metadata['filename']
        file_path = config.UPDATES_DIR / filename
        file.save(file_path)
        
        # Calculate hash
        file_hash = crypto.calculate_hash(file_path)
        
        # Sign file
        signature = crypto.sign_file(file_path)
        
        # Create update info
        update_info = {
            'update_id': metadata['update_id'],
            'update_type': metadata['update_type'],
            'component': metadata['component'],
            'version': metadata['version'],
            'filename': filename,
            'hash': file_hash,
            'signature': signature,
            'download_url': f'/api/v1/updates/download/{metadata["update_id"]}',
            'size': file_path.stat().st_size,
            'uploaded_at': datetime.now().isoformat(),
            'description': metadata.get('description', ''),
            'hardware_version': metadata.get('hardware_version', 'any')
        }
        
        # Add to catalog
        catalog.add_update(update_info)
        
        logger.info(f"Update uploaded: {metadata['update_id']}")
        
        return jsonify({
            'success': True,
            'update_info': update_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error uploading update: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/updates/list', methods=['GET'])
def list_updates():
    """List all available updates"""
    try:
        updates = catalog.get_all_updates()
        return jsonify(updates), 200
    except Exception as e:
        logger.error(f"Error listing updates: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/updates/delete/<update_id>', methods=['DELETE'])
def delete_update(update_id):
    """Delete update (admin only)"""
    try:
        # Check authentication
        auth_token = request.headers.get('Authorization')
        if auth_token != 'Bearer admin_token_123':
            return jsonify({'error': 'Unauthorized'}), 401
        
        updates = catalog.get_all_updates()
        
        if update_id not in updates:
            return jsonify({'error': 'Update not found'}), 404
        
        update_info = updates[update_id]
        file_path = config.UPDATES_DIR / update_info['filename']
        
        # Delete file
        if file_path.exists():
            file_path.unlink()
        
        # Remove from catalog
        del catalog.catalog['updates'][update_id]
        catalog.save_catalog()
        
        logger.info(f"Update deleted: {update_id}")
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"Error deleting update: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/keys/public', methods=['GET'])
def get_public_key():
    """Get public key for signature verification"""
    try:
        return send_file(
            crypto.public_key_file,
            mimetype='application/x-pem-file'
        )
    except Exception as e:
        logger.error(f"Error serving public key: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'updates_count': len(catalog.get_all_updates()),
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/', methods=['GET'])
def index():
    """Server info page"""
    updates = catalog.get_all_updates()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>FOTA/SOTA Update Server</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; }}
            .update {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .status {{ color: green; }}
        </style>
    </head>
    <body>
        <h1>🔄 FOTA/SOTA Update Server</h1>
        <p class="status">✓ Server is running</p>
        <h2>Available Updates: {len(updates)}</h2>
        <div>
    """
    
    for update_id, info in updates.items():
        html += f"""
        <div class="update">
            <h3>{info['component']} - v{info['version']}</h3>
            <p><strong>Type:</strong> {info['update_type']}</p>
            <p><strong>File:</strong> {info['filename']} ({info['size']} bytes)</p>
            <p><strong>Hash:</strong> {info['hash'][:16]}...</p>
            <p><strong>Uploaded:</strong> {info['uploaded_at']}</p>
        </div>
        """
    
    html += """
        </div>
        <h2>API Endpoints</h2>
        <ul>
            <li>GET /api/v1/updates/check - Check for updates</li>
            <li>GET /api/v1/updates/download/&lt;id&gt; - Download update</li>
            <li>POST /api/v1/updates/upload - Upload update (admin)</li>
            <li>GET /api/v1/updates/list - List all updates</li>
            <li>GET /api/v1/keys/public - Get public key</li>
        </ul>
    </body>
    </html>
    """
    
    return html

# ==================== CLI TOOL ====================

def create_upload_script():
    """Create helper script for uploading updates"""
    script = """#!/usr/bin/env python3
'''
Upload Update Tool
Helper script to upload updates to the server
'''

import requests
import json
import sys
from pathlib import Path

SERVER_URL = "http://localhost:5000"
AUTH_TOKEN = "Bearer admin_token_123"

def upload_update(file_path, update_type, component, version, description=""):
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return False
    
    update_id = f"{component}_{version}".replace(".", "_")
    
    metadata = {
        'update_id': update_id,
        'update_type': update_type,
        'component': component,
        'version': version,
        'filename': file_path.name,
        'description': description
    }
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'metadata': json.dumps(metadata)}
        headers = {'Authorization': AUTH_TOKEN}
        
        response = requests.post(
            f"{SERVER_URL}/api/v1/updates/upload",
            files=files,
            data=data,
            headers=headers
        )
    
    if response.status_code == 200:
        print(f"✓ Update uploaded successfully!")
        print(json.dumps(response.json(), indent=2))
        return True
    else:
        print(f"✗ Upload failed: {response.text}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python upload_update.py <file> <type> <component> <version> [description]")
        print("Example: python upload_update.py firmware.bin esp32_firmware esp32_firmware 1.1.0 'Security patch'")
        sys.exit(1)
    
    file_path = sys.argv[1]
    update_type = sys.argv[2]
    component = sys.argv[3]
    version = sys.argv[4]
    description = sys.argv[5] if len(sys.argv) > 5 else ""
    
    upload_update(file_path, update_type, component, version, description)
"""
    
    with open('upload_update.py', 'w') as f:
        f.write(script)
    
    print("Created upload_update.py helper script")

# ==================== MAIN ====================

def main():
    """Run the update server"""
    print("=" * 50)
    print("   FOTA/SOTA Update Server")
    print("=" * 50)
    print(f"Updates directory: {config.UPDATES_DIR}")
    print(f"Public key: {crypto.public_key_file}")
    print(f"Updates in catalog: {len(catalog.get_all_updates())}")
    print("=" * 50)
    
    # Create upload helper script
    create_upload_script()
    
    # Run server
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)

if __name__ == '__main__':
    main()