import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta
import glob

class TrafficDashboard:
    def __init__(self):
        self.reports_dir = 'PowerBI_Reports'
        self.data_files = self.find_data_files()
        
    def find_data_files(self):
        """Find all CSV data files in current directory"""
        csv_files = glob.glob('traffic_analysis_report_*.csv')
        csv_files.extend(glob.glob('powerbi_traffic_data_*.csv'))
        return sorted(csv_files, reverse=True)
    
    def find_report_files(self):
        """Find Power BI report files"""
        try:
            if not os.path.exists(self.reports_dir):
                os.makedirs(self.reports_dir)
                return []
            report_files = [f for f in os.listdir(self.reports_dir) if f.endswith('.pbix')]
            return sorted(report_files, reverse=True)
        except Exception as e:
            st.warning(f"Could not access reports directory: {e}")
            return []
    
    def load_data(self, selected_files):
        """Load and combine selected data files"""
        if not selected_files:
            return pd.DataFrame()
            
        combined_df = pd.DataFrame()
        
        for file in selected_files:
            try:
                df = pd.read_csv(file)
                combined_df = pd.concat([combined_df, df], ignore_index=True)
                st.success(f"✅ Loaded {file} ({len(df)} records)")
            except Exception as e:
                st.error(f"❌ Error loading {file}: {e}")
        
        return combined_df

def main():
    st.set_page_config(
        page_title="Traffic Detection Dashboard",
        page_icon="🚗",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">🚗 Traffic Detection Dashboard</h1>', unsafe_allow_html=True)
    
    # Initialize dashboard
    dashboard = TrafficDashboard()
    
    # Sidebar
    st.sidebar.title("Configuration")
    
    # File selection
    st.sidebar.subheader("Data Sources")
    if not dashboard.data_files:
        st.sidebar.error("No data files found! Please run the detection system first.")
        return
    
    selected_files = st.sidebar.multiselect(
        "Select data files to analyze:",
        options=dashboard.data_files,
        default=dashboard.data_files[:2] if len(dashboard.data_files) >= 2 else dashboard.data_files
    )
    
    if not selected_files:
        st.warning("Please select at least one data file to continue.")
        return
    
    # Load data
    with st.spinner("Loading data..."):
        df = dashboard.load_data(selected_files)
    
    if df.empty:
        st.error("No data loaded. Please check your file selections.")
        return
    
    # Data preprocessing
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.day_name()
    
    # Filters
    st.sidebar.subheader("Filters")
    
    # Vehicle type filter
    vehicle_types = ['All'] + sorted(df['vehicle_type'].unique().tolist())
    selected_vehicle = st.sidebar.selectbox("Vehicle Type", vehicle_types)
    
    if selected_vehicle != 'All':
        df = df[df['vehicle_type'] == selected_vehicle]
    
    # Date range filter (if timestamp available)
    if 'timestamp' in df.columns and not df['timestamp'].isna().all():
        min_date = df['timestamp'].min().date()
        max_date = df['timestamp'].max().date()
        
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)]
    
    # Confidence filter (if available)
    if 'confidence' in df.columns:
        min_confidence = st.sidebar.slider(
            "Minimum Confidence",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.1
        )
        df = df[df['confidence'] >= min_confidence]
    
    # Main dashboard
    if df.empty:
        st.warning("No data matches the selected filters.")
        return
    
    # Key metrics
    st.subheader("📊 Overview Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_detections = len(df)
        st.metric("Total Detections", total_detections)
    
    with col2:
        unique_vehicles = df['vehicle_type'].nunique()
        st.metric("Vehicle Types", unique_vehicles)
    
    with col3:
        if 'timestamp' in df.columns:
            date_range_days = (df['timestamp'].max() - df['timestamp'].min()).days + 1
            st.metric("Days Analyzed", date_range_days)
        else:
            st.metric("Files Loaded", len(selected_files))
    
    with col4:
        if 'confidence' in df.columns:
            avg_confidence = df['confidence'].mean()
            st.metric("Avg Confidence", f"{avg_confidence:.2%}")
        else:
            st.metric("Status", "Active")
    
    # Charts
    st.subheader("📈 Analysis Charts")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Vehicle type distribution
        vehicle_counts = df['vehicle_type'].value_counts().reset_index()
        vehicle_counts.columns = ['vehicle_type', 'count']
        
        fig1 = px.pie(
            vehicle_counts,
            values='count',
            names='vehicle_type',
            title="Vehicle Type Distribution"
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Hourly distribution (if timestamp available)
        if 'hour' in df.columns:
            hourly_counts = df['hour'].value_counts().sort_index().reset_index()
            hourly_counts.columns = ['hour', 'count']
            
            fig2 = px.bar(
                hourly_counts,
                x='hour',
                y='count',
                title="Hourly Traffic Pattern",
                labels={'hour': 'Hour of Day', 'count': 'Number of Detections'}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            # Alternative: Source file distribution
            source_counts = df['source_file'].value_counts().head(10).reset_index()
            source_counts.columns = ['source_file', 'count']
            
            fig2 = px.bar(
                source_counts,
                x='source_file',
                y='count',
                title="Top 10 Source Files"
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    # Time series analysis (if timestamp available)
    if 'timestamp' in df.columns:
        st.subheader("📅 Time Series Analysis")
        
        # Daily counts
        daily_counts = df.groupby(df['timestamp'].dt.date).size().reset_index()
        daily_counts.columns = ['date', 'count']
        
        fig3 = px.line(
            daily_counts,
            x='date',
            y='count',
            title="Daily Detection Trends",
            labels={'date': 'Date', 'count': 'Detections per Day'}
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    # Confidence distribution (if available)
    if 'confidence' in df.columns:
        st.subheader("🎯 Confidence Analysis")
        
        fig4 = px.histogram(
            df,
            x='confidence',
            nbins=20,
            title="Distribution of Detection Confidence Scores"
        )
        st.plotly_chart(fig4, use_container_width=True)
    
    # Data table
    st.subheader("📋 Detection Data")
    
    # Show limited columns for better readability
    display_columns = ['vehicle_type']
    if 'confidence' in df.columns:
        display_columns.append('confidence')
    if 'direction' in df.columns:
        display_columns.append('direction')
    if 'timestamp' in df.columns:
        display_columns.append('timestamp')
    if 'source_file' in df.columns:
        display_columns.append('source_file')
    
    st.dataframe(df[display_columns].head(100), use_container_width=True)
    
    # Export option
    st.subheader("💾 Export Data")
    
    if st.button("Download Filtered Data as CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"traffic_detection_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()