/**
 * Firebase Cloud Functions for SDV OTA Updates & V2X
 * Deploy with: firebase deploy --only functions
 */

const functions = require('firebase-functions');
const admin = require('firebase-admin');
const crypto = require('crypto');

admin.initializeApp();

// ==================== FOTA/SOTA FUNCTIONS ====================

/**
 * Trigger when new update is uploaded to Cloud Storage
 * Automatically creates Firestore metadata
 */
exports.onUpdateUploaded = functions.storage.object().onFinalize(async (object) => {
  const filePath = object.name;
  
  // Only process files in 'updates/' folder
  if (!filePath.startsWith('updates/')) {
    return null;
  }
  
  console.log('New update uploaded:', filePath);
  
  const filename = filePath.split('/').pop();
  const metadata = object.metadata || {};
  
  // Calculate file hash
  const bucket = admin.storage().bucket();
  const file = bucket.file(filePath);
  const [fileBuffer] = await file.download();
  const hash = crypto.createHash('sha256').update(fileBuffer).digest('hex');
  
  // Create Firestore document
  const updateDoc = {
    update_id: metadata.update_id || filename.replace(/\./g, '_'),
    filename: filename,
    storage_path: filePath,
    component: metadata.component || 'unknown',
    version: metadata.version || '1.0.0',
    update_type: metadata.update_type || 'software',
    hash: hash,
    size: parseInt(object.size),
    uploaded_at: admin.firestore.FieldValue.serverTimestamp(),
    active: metadata.active !== 'false',  // Default true
    description: metadata.description || '',
    hardware_version: metadata.hardware_version || 'any'
  };
  
  await admin.firestore()
    .collection('updates')
    .doc(updateDoc.update_id)
    .set(updateDoc);
  
  console.log('Update metadata created:', updateDoc.update_id);
  
  // Notify all vehicles about new update
  await notifyVehiclesAboutUpdate(updateDoc);
  
  return null;
});

/**
 * Notify vehicles about new available update
 */
async function notifyVehiclesAboutUpdate(update) {
  const vehiclesSnapshot = await admin.firestore()
    .collection('vehicles')
    .where('status', '==', 'online')
    .get();
  
  const notifications = [];
  
  vehiclesSnapshot.forEach((doc) => {
    const vehicle = doc.data();
    const currentVersion = vehicle.current_versions[update.component] || '0.0.0';
    
    // Check if update is applicable
    if (compareVersions(update.version, currentVersion) > 0) {
      notifications.push(
        admin.firestore()
          .collection('vehicles')
          .doc(doc.id)
          .collection('notifications')
          .add({
            type: 'update_available',
            component: update.component,
            version: update.version,
            update_id: update.update_id,
            timestamp: admin.firestore.FieldValue.serverTimestamp(),
            read: false
          })
      );
    }
  });
  
  await Promise.all(notifications);
  console.log(`Notified ${notifications.length} vehicles`);
}

/**
 * HTTP endpoint to check for updates
 */
exports.checkUpdates = functions.https.onRequest(async (req, res) => {
  // Enable CORS
  res.set('Access-Control-Allow-Origin', '*');
  
  if (req.method === 'OPTIONS') {
    res.set('Access-Control-Allow-Methods', 'GET, POST');
    res.set('Access-Control-Allow-Headers', 'Content-Type');
    res.status(204).send('');
    return;
  }
  
  const vehicleId = req.query.vehicle_id || req.body.vehicle_id;
  const currentVersions = req.query.current_versions || req.body.current_versions || '{}';
  
  if (!vehicleId) {
    res.status(400).json({ error: 'vehicle_id required' });
    return;
  }
  
  try {
    const versions = typeof currentVersions === 'string' 
      ? JSON.parse(currentVersions) 
      : currentVersions;
    
    // Query available updates
    const updatesSnapshot = await admin.firestore()
      .collection('updates')
      .where('active', '==', true)
      .get();
    
    const availableUpdates = {};
    
    updatesSnapshot.forEach((doc) => {
      const update = doc.data();
      const currentVersion = versions[update.component] || '0.0.0';
      
      if (compareVersions(update.version, currentVersion) > 0) {
        availableUpdates[update.component] = {
          update_id: update.update_id,
          component: update.component,
          version: update.version,
          update_type: update.update_type,
          filename: update.filename,
          storage_path: update.storage_path,
          hash: update.hash,
          size: update.size,
          description: update.description,
          download_url: `https://firebasestorage.googleapis.com/v0/b/${admin.storage().bucket().name}/o/${encodeURIComponent(update.storage_path)}?alt=media`
        };
      }
    });
    
    // Log check
    await admin.firestore()
      .collection('update_logs')
      .add({
        vehicle_id: vehicleId,
        event_type: 'check',
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
        updates_found: Object.keys(availableUpdates).length
      });
    
    res.json(availableUpdates);
    
  } catch (error) {
    console.error('Error checking updates:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * HTTP endpoint to get download URL with token
 */
exports.getDownloadUrl = functions.https.onRequest(async (req, res) => {
  res.set('Access-Control-Allow-Origin', '*');
  
  const updateId = req.query.update_id;
  
  if (!updateId) {
    res.status(400).json({ error: 'update_id required' });
    return;
  }
  
  try {
    const updateDoc = await admin.firestore()
      .collection('updates')
      .doc(updateId)
      .get();
    
    if (!updateDoc.exists) {
      res.status(404).json({ error: 'Update not found' });
      return;
    }
    
    const update = updateDoc.data();
    const file = admin.storage().bucket().file(update.storage_path);
    
    // Generate signed URL valid for 1 hour
    const [url] = await file.getSignedUrl({
      action: 'read',
      expires: Date.now() + 3600000
    });
    
    res.json({ download_url: url });
    
  } catch (error) {
    console.error('Error getting download URL:', error);
    res.status(500).json({ error: error.message });
  }
});

// ==================== V2X FUNCTIONS ====================

/**
 * Process V2X messages and route to nearby vehicles
 */
exports.processV2XMessage = functions.database
  .ref('/v2x/bsm/{vehicleId}')
  .onWrite(async (change, context) => {
    const vehicleId = context.params.vehicleId;
    const bsmData = change.after.val();
    
    if (!bsmData) return null;
    
    // Find nearby vehicles (within 500m radius for example)
    const vehiclesSnapshot = await admin.firestore()
      .collection('vehicles')
      .where('status', '==', 'online')
      .get();
    
    const notifications = [];
    
    vehiclesSnapshot.forEach((doc) => {
      const vehicle = doc.data();
      
      if (doc.id === vehicleId) return;  // Skip self
      
      // Calculate distance (simplified)
      const distance = calculateDistance(
        bsmData.latitude,
        bsmData.longitude,
        vehicle.location.latitude,
        vehicle.location.longitude
      );
      
      // If within 500m, notify
      if (distance < 0.5) {
        notifications.push(
          admin.database()
            .ref(`/v2x/messages/${doc.id}/${Date.now()}`)
            .set({
              type: 'bsm',
              from: vehicleId,
              data: bsmData,
              timestamp: Date.now()
            })
        );
      }
    });
    
    await Promise.all(notifications);
    return null;
  });

/**
 * Broadcast emergency messages to all vehicles
 */
exports.broadcastEmergency = functions.database
  .ref('/v2x/emergency/{messageId}')
  .onCreate(async (snapshot, context) => {
    const emergencyData = snapshot.val();
    
    console.log('Emergency broadcast:', emergencyData);
    
    // Get all active vehicles
    const vehiclesSnapshot = await admin.firestore()
      .collection('vehicles')
      .where('status', '==', 'online')
      .get();
    
    const broadcasts = [];
    
    vehiclesSnapshot.forEach((doc) => {
      broadcasts.push(
        admin.database()
          .ref(`/v2x/messages/${doc.id}/${Date.now()}`)
          .set({
            type: 'emergency',
            data: emergencyData,
            timestamp: Date.now(),
            priority: 'high'
          })
      );
    });
    
    await Promise.all(broadcasts);
    return null;
  });

/**
 * Clean up old V2X messages (runs every hour)
 */
exports.cleanupOldMessages = functions.pubsub
  .schedule('every 1 hours')
  .onRun(async (context) => {
    const cutoff = Date.now() - (24 * 60 * 60 * 1000);  // 24 hours ago
    
    const messagesRef = admin.database().ref('/v2x/bsm');
    const snapshot = await messagesRef.once('value');
    
    const deletions = [];
    
    snapshot.forEach((child) => {
      const data = child.val();
      if (data.timestamp && data.timestamp < cutoff) {
        deletions.push(child.ref.remove());
      }
    });
    
    await Promise.all(deletions);
    console.log(`Cleaned up ${deletions.length} old messages`);
    
    return null;
  });

// ==================== ANALYTICS FUNCTIONS ====================

/**
 * Generate fleet statistics
 */
exports.generateFleetStats = functions.pubsub
  .schedule('every 5 minutes')
  .onRun(async (context) => {
    const vehiclesSnapshot = await admin.firestore()
      .collection('vehicles')
      .get();
    
    const stats = {
      total_vehicles: vehiclesSnapshot.size,
      online: 0,
      updating: 0,
      total_updates_today: 0,
      timestamp: admin.firestore.FieldValue.serverTimestamp()
    };
    
    vehiclesSnapshot.forEach((doc) => {
      const vehicle = doc.data();
      if (vehicle.status === 'online') stats.online++;
      if (vehicle.update_status === 'installing') stats.updating++;
    });
    
    // Count updates today
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const logsSnapshot = await admin.firestore()
      .collection('update_logs')
      .where('event_type', '==', 'success')
      .where('timestamp', '>=', today)
      .get();
    
    stats.total_updates_today = logsSnapshot.size;
    
    // Save stats
    await admin.firestore()
      .collection('fleet_stats')
      .doc('current')
      .set(stats);
    
    return null;
  });

// ==================== UTILITY FUNCTIONS ====================

function compareVersions(v1, v2) {
  const parts1 = v1.split('.').map(Number);
  const parts2 = v2.split('.').map(Number);
  
  for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
    const p1 = parts1[i] || 0;
    const p2 = parts2[i] || 0;
    
    if (p1 > p2) return 1;
    if (p1 < p2) return -1;
  }
  
  return 0;
}

function calculateDistance(lat1, lon1, lat2, lon2) {
  // Haversine formula (returns distance in km)
  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

function toRad(degrees) {
  return degrees * Math.PI / 180;
}

// ==================== ADMIN FUNCTIONS ====================

/**
 * HTTP endpoint to manually trigger update for specific vehicle
 */
exports.triggerUpdate = functions.https.onRequest(async (req, res) => {
  res.set('Access-Control-Allow-Origin', '*');
  
  if (req.method === 'OPTIONS') {
    res.set('Access-Control-Allow-Methods', 'POST');
    res.set('Access-Control-Allow-Headers', 'Content-Type');
    res.status(204).send('');
    return;
  }
  
  const { vehicle_id, update_id } = req.body;
  
  if (!vehicle_id || !update_id) {
    res.status(400).json({ error: 'vehicle_id and update_id required' });
    return;
  }
  
  try {
    // Add notification
    await admin.firestore()
      .collection('vehicles')
      .doc(vehicle_id)
      .collection('notifications')
      .add({
        type: 'update_required',
        update_id: update_id,
        timestamp: admin.firestore.FieldValue.serverTimestamp(),
        priority: 'high'
      });
    
    res.json({ success: true, message: 'Update triggered' });
    
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});