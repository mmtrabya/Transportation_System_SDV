#!/usr/bin/env python3
"""
SDV Real-Time Dashboard
Streamlit-based dashboard for monitoring SDV telemetry data
"""

import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
from collections import deque
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict

# ==================== CONFIGURATION ====================

class DashboardConfig:
    """Dashboard configuration"""
    MQTT_BROKER = "localhost"
    MQTT_PORT = 1883
    VEHICLE_ID = "SDV_001"
    
    # MQTT Topics
    TOPIC_GPS = f"sdv/{VEHICLE_ID}/gps"
    TOPIC_ADAS = f"sdv/{VEHICLE_ID}/adas"
    TOPIC_V2X = f"sdv/{VEHICLE_ID}/v2x"
    TOPIC_SYSTEM = f"sdv/{VEHICLE_ID}/system"
    TOPIC_ALERTS = f"sdv/{VEHICLE_ID}/alerts"
    TOPIC_STATUS = f"sdv/{VEHICLE_ID}/status"

# ==================== DATA MANAGER ====================

class DataManager:
    """Manages incoming telemetry data"""
    
    def __init__(self):
        self.gps_data = {}
        self.adas_data = {}
        self.v2x_data = {}
        self.system_data = {}
        self.alerts = deque(maxlen=50)
        self.status = "offline"
        
        # Historical data for graphs
        self.gps_history = deque(maxlen=100)
        self.speed_history = deque(maxlen=100)
        self.lane_departure_history = deque(maxlen=100)
        self.objects_history = deque(maxlen=100)
        self.timestamps = deque(maxlen=100)
        
        self.last_update = time.time()
        self.connected = False
    
    def update_gps(self, data: Dict):
        self.gps_data = data
        self.gps_history.append((data.get('latitude'), data.get('longitude')))
        self.speed_history.append(data.get('speed', 0))
        self.timestamps.append(datetime.now())
        self.last_update = time.time()
    
    def update_adas(self, data: Dict):
        self.adas_data = data
        self.lane_departure_history.append(data.get('lane_departure', 0))
        self.objects_history.append(data.get('objects_detected', 0))
        self.last_update = time.time()
    
    def update_v2x(self, data: Dict):
        self.v2x_data = data
        self.last_update = time.time()
    
    def update_system(self, data: Dict):
        self.system_data = data
        self.last_update = time.time()
    
    def add_alert(self, data: Dict):
        self.alerts.appendleft(data)
        self.last_update = time.time()
    
    def update_status(self, data: Dict):
        self.status = data.get('status', 'offline')
        self.last_update = time.time()
    
    def get_connection_status(self) -> str:
        elapsed = time.time() - self.last_update
        if elapsed < 2:
            return "🟢 Connected"
        elif elapsed < 5:
            return "🟡 Unstable"
        else:
            return "🔴 Disconnected"

# ==================== MQTT CLIENT ====================

class MQTTClient:
    """MQTT client for receiving telemetry"""
    
    def __init__(self, data_manager: DataManager, config: DashboardConfig):
        self.data_manager = data_manager
        self.config = config
        
        self.client = mqtt.Client(client_id="dashboard_viewer")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        self.connected = False
    
    def connect(self):
        try:
            self.client.connect(self.config.MQTT_BROKER, self.config.MQTT_PORT, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            st.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.data_manager.connected = True
            
            topics = [
                (self.config.TOPIC_GPS, 0),
                (self.config.TOPIC_ADAS, 0),
                (self.config.TOPIC_V2X, 0),
                (self.config.TOPIC_SYSTEM, 0),
                (self.config.TOPIC_ALERTS, 0),
                (self.config.TOPIC_STATUS, 0),
            ]
            client.subscribe(topics)
        else:
            self.connected = False
            self.data_manager.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.data_manager.connected = False
    
    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            
            if self.config.TOPIC_GPS in msg.topic:
                self.data_manager.update_gps(data)
            elif self.config.TOPIC_ADAS in msg.topic:
                self.data_manager.update_adas(data)
            elif self.config.TOPIC_V2X in msg.topic:
                self.data_manager.update_v2x(data)
            elif self.config.TOPIC_SYSTEM in msg.topic:
                self.data_manager.update_system(data)
            elif self.config.TOPIC_ALERTS in msg.topic:
                self.data_manager.add_alert(data)
            elif self.config.TOPIC_STATUS in msg.topic:
                self.data_manager.update_status(data)
                
        except:
            pass

# ==================== VISUALIZATION FUNCTIONS ====================

def create_map(gps_data: Dict, gps_history: deque):
    if not gps_data:
        return None
    
    lat = gps_data.get('latitude', 30.0444)
    lon = gps_data.get('longitude', 31.2357)
    
    fig = go.Figure()
    
    if len(gps_history) > 1:
        lats = [pos[0] for pos in gps_history if pos[0]]
        lons = [pos[1] for pos in gps_history if pos[1]]
        
        fig.add_trace(go.Scattermapbox(
            lat=lats, lon=lons, mode='lines',
            line=dict(width=2, color='blue'),
            name='Trajectory'
        ))
    
    fig.add_trace(go.Scattermapbox(
        lat=[lat], lon=[lon], mode='markers',
        marker=dict(size=15, color='red'),
        text=[f"Speed: {gps_data.get('speed', 0):.1f} km/h"],
        name='Current Position'
    ))
    
    fig.update_layout(
        mapbox=dict(style="open-street-map", center=dict(lat=lat, lon=lon), zoom=15),
        margin=dict(l=0, r=0, t=0, b=0), height=400
    )
    
    return fig

def create_speed_chart(speed_history: deque, timestamps: deque):
    if len(speed_history) == 0:
        return None
    
    df = pd.DataFrame({'Time': list(timestamps), 'Speed (km/h)': list(speed_history)})
    fig = px.line(df, x='Time', y='Speed (km/h)', title='Vehicle Speed')
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def create_lane_departure_chart(lane_history: deque, timestamps: deque):
    if len(lane_history) == 0:
        return None
    
    df = pd.DataFrame({'Time': list(timestamps), 'Departure': list(lane_history)})
    fig = px.line(df, x='Time', y='Departure', title='Lane Departure')
    
    fig.add_hline(y=0.2, line_dash="dash", line_color="orange")
    fig.add_hline(y=-0.2, line_dash="dash", line_color="orange")
    fig.add_hline(y=0.3, line_dash="dash", line_color="red")
    fig.add_hline(y=-0.3, line_dash="dash", line_color="red")
    
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def create_system_gauges(system_data: Dict):
    if not system_data:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Indicator(
        mode="gauge+number", value=system_data.get('cpu_percent', 0),
        title={'text': "CPU %"}, domain={'x': [0, 0.3], 'y': [0, 1]},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "darkblue"}}
    ))
    
    fig.add_trace(go.Indicator(
        mode="gauge+number", value=system_data.get('memory_percent', 0),
        title={'text': "Memory %"}, domain={'x': [0.35, 0.65], 'y': [0, 1]},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "green"}}
    ))
    
    fig.add_trace(go.Indicator(
        mode="gauge+number", value=system_data.get('temperature', 0),
        title={'text': "Temp °C"}, domain={'x': [0.7, 1], 'y': [0, 1]},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "red"}}
    ))
    
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# ==================== MAIN DASHBOARD ====================

def main():
    st.set_page_config(page_title="SDV Dashboard", layout="wide", page_icon="🚗")
    
    st.title("🚗 Software-Defined Vehicle Dashboard")
    
    # Initialize session state
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()
        st.session_state.mqtt_client = MQTTClient(
            st.session_state.data_manager,
            DashboardConfig()
        )
        st.session_state.mqtt_client.connect()
    
    dm = st.session_state.data_manager
    
    # Header with status
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(f"Vehicle: {DashboardConfig.VEHICLE_ID}")
    with col2:
        st.metric("Status", dm.status.upper())
    with col3:
        st.metric("Connection", dm.get_connection_status())
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📍 Location", "🚦 ADAS", "📡 V2X", "⚙️ System"])
    
    with tab1:
        # GPS Data
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if dm.gps_data:
                map_fig = create_map(dm.gps_data, dm.gps_history)
                if map_fig:
                    st.plotly_chart(map_fig, use_container_width=True)
            else:
                st.info("Waiting for GPS data...")
        
        with col2:
            st.subheader("GPS Metrics")
            if dm.gps_data:
                st.metric("Latitude", f"{dm.gps_data.get('latitude', 0):.6f}")
                st.metric("Longitude", f"{dm.gps_data.get('longitude', 0):.6f}")
                st.metric("Speed", f"{dm.gps_data.get('speed', 0):.1f} km/h")
                st.metric("Heading", f"{dm.gps_data.get('heading', 0):.1f}°")
        
        # Speed chart
        speed_chart = create_speed_chart(dm.speed_history, dm.timestamps)
        if speed_chart:
            st.plotly_chart(speed_chart, use_container_width=True)
    
    with tab2:
        # ADAS Data
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Lane Detection")
            if dm.adas_data:
                lane_dep = dm.adas_data.get('lane_departure', 0)
                color = "green" if abs(lane_dep) < 0.1 else "orange" if abs(lane_dep) < 0.3 else "red"
                st.metric("Lane Departure", f"{lane_dep:.3f}", delta_color="inverse")
                
                lane_chart = create_lane_departure_chart(dm.lane_departure_history, dm.timestamps)
                if lane_chart:
                    st.plotly_chart(lane_chart, use_container_width=True)
        
        with col2:
            st.subheader("Object Detection")
            if dm.adas_data:
                st.metric("Objects Detected", dm.adas_data.get('objects_detected', 0))
                
                sign = dm.adas_data.get('traffic_sign')
                conf = dm.adas_data.get('sign_confidence', 0)
                if sign:
                    st.info(f"🚸 {sign} (Confidence: {conf:.2f})")
    
    with tab3:
        # V2X Data
        st.subheader("Vehicle-to-Everything Communication")
        
        col1, col2, col3, col4 = st.columns(4)
        
        if dm.v2x_data:
            with col1:
                st.metric("Nearby Vehicles", dm.v2x_data.get('nearby_vehicles', 0))
            with col2:
                st.metric("Hazards", dm.v2x_data.get('hazards_detected', 0))
            with col3:
                st.metric("Emergency Vehicles", dm.v2x_data.get('emergency_vehicles', 0))
            with col4:
                st.metric("Messages Received", dm.v2x_data.get('messages_received', 0))
    
    with tab4:
        # System Health
        st.subheader("System Health")
        
        if dm.system_data:
            gauge_fig = create_system_gauges(dm.system_data)
            if gauge_fig:
                st.plotly_chart(gauge_fig, use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Uptime", f"{dm.system_data.get('uptime', 0)/60:.1f} min")
            with col2:
                st.metric("Messages Sent", dm.system_data.get('messages_sent', 0))
            with col3:
                st.metric("Messages Failed", dm.system_data.get('messages_failed', 0))
    
    # Alerts sidebar
    with st.sidebar:
        st.subheader("🚨 Recent Alerts")
        
        if dm.alerts:
            for alert in list(dm.alerts)[:10]:
                severity = alert.get('severity', 'info')
                icon = "🔴" if severity == 'critical' else "🟡" if severity == 'warning' else "🔵"
                st.write(f"{icon} **{alert.get('type')}**")
                st.caption(alert.get('message'))
                st.divider()
        else:
            st.info("No alerts")
        
        # Refresh button
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    # Auto-refresh
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()