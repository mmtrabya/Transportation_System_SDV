#!/usr/bin/env python3
"""
Security Monitoring Dashboard
Real-time security status visualization with Streamlit
"""
import streamlit as st
import time
import json
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from collections import deque

# Import security system
try:
    from automotive_cybersecurity import AutomotiveSecurity, SecurityEvent
except:
    st.error("automotive_cybersecurity.py not found. Please ensure it's in the same directory.")
    st.stop()

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Security Dashboard",
    layout="wide",
    page_icon="🔐"
)

# ==================== SESSION STATE ====================
if 'security_system' not in st.session_state:
    st.session_state.security_system = AutomotiveSecurity()
    st.session_state.event_history = deque(maxlen=100)
    st.session_state.score_history = deque(maxlen=50)
    st.session_state.timestamp_history = deque(maxlen=50)
    st.session_state.last_update = time.time()

security = st.session_state.security_system

# ==================== HELPER FUNCTIONS ====================

def get_severity_color(severity: str) -> str:
    """Get color for severity level"""
    colors = {
        'critical': '#FF0000',
        'high': '#FF6B6B',
        'medium': '#FFA500',
        'low': '#90EE90',
        'info': '#87CEEB'
    }
    return colors.get(severity, '#808080')

def get_severity_emoji(severity: str) -> str:
    """Get emoji for severity level"""
    emojis = {
        'critical': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🟢',
        'info': '🔵'
    }
    return emojis.get(severity, '⚪')

def create_security_score_gauge(score: float):
    """Create security score gauge"""
    color = 'green' if score >= 80 else 'orange' if score >= 60 else 'red'
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Security Score", 'font': {'size': 24}},
        delta={'reference': 100, 'increasing': {'color': "green"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 60], 'color': '#FFE5E5'},
                {'range': [60, 80], 'color': '#FFF5E5'},
                {'range': [80, 100], 'color': '#E5FFE5'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        font={'size': 16}
    )
    
    return fig

def create_score_history_chart(score_history, timestamp_history):
    """Create security score history chart"""
    if len(score_history) == 0:
        return None
    
    df = pd.DataFrame({
        'Time': list(timestamp_history),
        'Security Score': list(score_history)
    })
    
    fig = px.line(df, x='Time', y='Security Score', 
                  title='Security Score History',
                  range_y=[0, 100])
    
    fig.add_hline(y=80, line_dash="dash", line_color="green", 
                  annotation_text="Good")
    fig.add_hline(y=60, line_dash="dash", line_color="orange", 
                  annotation_text="Warning")
    fig.add_hline(y=40, line_dash="dash", line_color="red", 
                  annotation_text="Critical")
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

def create_event_distribution_chart(events):
    """Create event severity distribution chart"""
    if not events:
        return None
    
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    
    for event in events:
        if event.severity in severity_counts:
            severity_counts[event.severity] += 1
    
    df = pd.DataFrame({
        'Severity': list(severity_counts.keys()),
        'Count': list(severity_counts.values())
    })
    
    colors = ['#FF0000', '#FF6B6B', '#FFA500', '#90EE90']
    
    fig = px.bar(df, x='Severity', y='Count', 
                 title='Security Events by Severity',
                 color='Severity',
                 color_discrete_sequence=colors)
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False
    )
    
    return fig

def create_threat_timeline(events):
    """Create threat timeline"""
    if not events:
        return None
    
    data = []
    for event in events:
        data.append({
            'Time': datetime.fromtimestamp(event.timestamp),
            'Event': event.event_type,
            'Severity': event.severity,
            'Source': event.source
        })
    
    df = pd.DataFrame(data)
    
    fig = px.scatter(df, x='Time', y='Event', 
                     color='Severity',
                     title='Threat Timeline',
                     color_discrete_map={
                         'critical': '#FF0000',
                         'high': '#FF6B6B',
                         'medium': '#FFA500',
                         'low': '#90EE90'
                     })
    
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig

# ==================== MAIN DASHBOARD ====================

def main():
    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("🔐 Automotive Security Dashboard")
    
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    with col3:
        auto_refresh = st.checkbox("Auto-refresh", value=True)
    
    # Get security status
    status = security.get_status()
    score = status['security_score']
    
    # Update history
    st.session_state.score_history.append(score)
    st.session_state.timestamp_history.append(datetime.now())
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cert_status = "✅ Valid" if status['certificate_valid'] else "❌ Invalid"
        st.metric("Certificate", cert_status)
    
    with col2:
        st.metric("Active Sessions", status['active_sessions'])
    
    with col3:
        blacklist_delta = -status['blacklisted_peers'] if status['blacklisted_peers'] > 0 else None
        st.metric("Blacklisted", status['blacklisted_peers'], 
                 delta=blacklist_delta, delta_color="inverse")
    
    with col4:
        critical_delta = -status['recent_critical_events'] if status['recent_critical_events'] > 0 else None
        st.metric("Critical Events", status['recent_critical_events'],
                 delta=critical_delta, delta_color="inverse")
    
    st.divider()
    
    # Main content - Two columns
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Security Score Gauge
        gauge_fig = create_security_score_gauge(score)
        st.plotly_chart(gauge_fig, use_container_width=True)
        
        # Score History
        history_fig = create_score_history_chart(
            st.session_state.score_history,
            st.session_state.timestamp_history
        )
        if history_fig:
            st.plotly_chart(history_fig, use_container_width=True)
    
    with col2:
        # Event Distribution
        recent_events = security.ids.get_recent_events(50)
        dist_fig = create_event_distribution_chart(recent_events)
        if dist_fig:
            st.plotly_chart(dist_fig, use_container_width=True)
        
        # Certificate Info
        st.subheader("📜 Certificate Information")
        cert_data = {
            'Expires': status['certificate_expires'],
            'Valid': cert_status,
            'Vehicle ID': security.config.VEHICLE_ID
        }
        st.json(cert_data)
    
    # Threat Timeline
    st.subheader("📊 Threat Timeline")
    timeline_fig = create_threat_timeline(recent_events)
    if timeline_fig:
        st.plotly_chart(timeline_fig, use_container_width=True)
    else:
        st.info("No security events recorded")
    
    st.divider()
    
    # Tabs for detailed info
    tab1, tab2, tab3, tab4 = st.tabs([
        "🚨 Recent Events", 
        "🚫 Blacklist", 
        "📈 Statistics",
        "📋 Full Report"
    ])
    
    with tab1:
        st.subheader("Recent Security Events")
        
        if recent_events:
            for event in recent_events[:20]:
                timestamp = datetime.fromtimestamp(event.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                emoji = get_severity_emoji(event.severity)
                color = get_severity_color(event.severity)
                
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 4])
                    
                    with col1:
                        st.markdown(f"**{emoji} {event.severity.upper()}**")
                    
                    with col2:
                        st.text(timestamp)
                    
                    with col3:
                        st.markdown(f"**{event.event_type}**: {event.description}")
                        if event.metadata:
                            st.caption(f"Source: {event.source} | Metadata: {event.metadata}")
                    
                    st.divider()
        else:
            st.success("No security events - System is secure!")
    
    with tab2:
        st.subheader("Blacklisted Peers")
        
        if security.ids.blacklisted_peers:
            blacklist_data = []
            for peer in security.ids.blacklisted_peers:
                attempts = security.ids.failed_auth_attempts.get(peer, 0)
                blacklist_data.append({
                    'Peer ID': peer,
                    'Failed Attempts': attempts,
                    'Status': '🚫 Blocked'
                })
            
            df = pd.DataFrame(blacklist_data)
            st.dataframe(df, use_container_width=True)
            
            if st.button("Clear Blacklist"):
                security.ids.blacklisted_peers.clear()
                security.ids.failed_auth_attempts.clear()
                st.success("Blacklist cleared!")
                st.rerun()
        else:
            st.success("No blacklisted peers")
    
    with tab3:
        st.subheader("Security Statistics")
        
        stats_col1, stats_col2 = st.columns(2)
        
        with stats_col1:
            st.metric("Total Events", len(security.ids.security_events))
            st.metric("Critical Events", len([e for e in recent_events if e.severity == 'critical']))
            st.metric("High Severity Events", len([e for e in recent_events if e.severity == 'high']))
        
        with stats_col2:
            st.metric("Medium Severity Events", len([e for e in recent_events if e.severity == 'medium']))
            st.metric("Low Severity Events", len([e for e in recent_events if e.severity == 'low']))
            st.metric("Unique Sources", len(set(e.source for e in recent_events)))
        
        # Event types breakdown
        st.subheader("Event Types")
        event_types = {}
        for event in recent_events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        
        if event_types:
            event_df = pd.DataFrame({
                'Event Type': list(event_types.keys()),
                'Count': list(event_types.values())
            })
            event_df = event_df.sort_values('Count', ascending=False)
            st.dataframe(event_df, use_container_width=True)
    
    with tab4:
        st.subheader("Full Security Report")
        
        report = security.get_report()
        st.code(report, language=None)
        
        if st.button("📥 Download Report"):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"security_report_{timestamp}.txt"
            st.download_button(
                label="Download",
                data=report,
                file_name=filename,
                mime="text/plain"
            )
    
    # Footer with last update time
    st.divider()
    last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st.caption(f"Last updated: {last_update}")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(2)
        st.rerun()

if __name__ == "__main__":
    main()