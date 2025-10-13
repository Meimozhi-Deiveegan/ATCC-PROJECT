import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os

# Set page config
st.set_page_config(
    page_title="ATCC Traffic Detection",
    page_icon="🚗",
    layout="wide"
)

def load_sample_data():
    """Load sample data for demo purposes"""
    # Create sample data if no CSV files exist
    sample_data = {
        'vehicle_type': ['car', 'truck', 'motorcycle', 'bus', 'car', 'truck'],
        'confidence': [0.95, 0.87, 0.92, 0.78, 0.96, 0.85],
        'source_file': ['video1.mp4', 'video1.mp4', 'video2.mp4', 'video2.mp4', 'video3.mp4', 'video3.mp4'],
        'timestamp': pd.date_range('2024-01-01', periods=6, freq='H')
    }
    return pd.DataFrame(sample_data)

def main():
    st.title("🚗 ATCC Traffic Detection Dashboard")
    st.markdown("Real-time traffic analysis and vehicle detection system")
    
    # File selection
    st.sidebar.header("Data Configuration")
    
    try:
        # Find CSV files
        csv_files = glob.glob('traffic_analysis_report_*.csv')
        
        if not csv_files:
            st.info("📊 Demo Mode: Using sample data. Upload CSV files for real data.")
            df = load_sample_data()
        else:
            selected_files = st.sidebar.multiselect(
                "Select data files:",
                csv_files,
                default=csv_files[:1]
            )
            
            if not selected_files:
                st.warning("Please select at least one data file.")
                return
            
            # Load selected files
            df = pd.DataFrame()
            for file in selected_files:
                try:
                    temp_df = pd.read_csv(file)
                    df = pd.concat([df, temp_df], ignore_index=True)
                    st.sidebar.success(f"✅ Loaded {file}")
                except Exception as e:
                    st.sidebar.error(f"❌ Error loading {file}: {e}")
            
            if df.empty:
                st.warning("No data loaded. Switching to demo mode.")
                df = load_sample_data()
        
        # Display metrics
        st.subheader("📊 Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Detections", len(df))
        
        with col2:
            st.metric("Vehicle Types", df['vehicle_type'].nunique())
        
        with col3:
            if 'source_file' in df.columns:
                st.metric("Source Files", df['source_file'].nunique())
            else:
                st.metric("Status", "Active")
        
        with col4:
            if 'confidence' in df.columns:
                avg_conf = df['confidence'].mean()
                st.metric("Avg Confidence", f"{avg_conf:.1%}")
            else:
                st.metric("Records", len(df))
        
        # Charts
        st.subheader("📈 Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            # Vehicle distribution
            vehicle_counts = df['vehicle_type'].value_counts()
            fig1 = px.pie(
                values=vehicle_counts.values, 
                names=vehicle_counts.index, 
                title="Vehicle Type Distribution"
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Confidence distribution if available
            if 'confidence' in df.columns:
                fig2 = px.histogram(
                    df, 
                    x='confidence',
                    title="Confidence Score Distribution",
                    nbins=20
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                # Source file distribution
                if 'source_file' in df.columns:
                    source_counts = df['source_file'].value_counts().head(10)
                    fig2 = px.bar(
                        x=source_counts.index,
                        y=source_counts.values,
                        title="Top Source Files"
                    )
                    st.plotly_chart(fig2, use_container_width=True)
        
        # Data table
        st.subheader("📋 Detection Data")
        
        # Select columns to display
        display_cols = ['vehicle_type']
        if 'confidence' in df.columns:
            display_cols.append('confidence')
        if 'source_file' in df.columns:
            display_cols.append('source_file')
        if 'timestamp' in df.columns:
            display_cols.append('timestamp')
            
        st.dataframe(df[display_cols].head(50), use_container_width=True)
        
        # File upload for users to add their own data
        st.sidebar.subheader("Upload Your Data")
        uploaded_file = st.sidebar.file_uploader(
            "Upload CSV file", 
            type=['csv'],
            help="Upload your traffic analysis CSV file"
        )
        
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                st.sidebar.success(f"✅ Uploaded {uploaded_file.name}")
                st.info(f"📁 Uploaded file: {uploaded_file.name} ({len(uploaded_df)} records)")
                
                # Show uploaded data
                st.subheader("📤 Uploaded Data Preview")
                st.dataframe(uploaded_df.head(20), use_container_width=True)
                
            except Exception as e:
                st.sidebar.error(f"Error reading uploaded file: {e}")
                
    except Exception as e:
        st.error(f"Application error: {e}")
        st.info("The app is running in limited demo mode.")

if __name__ == "__main__":
    main()
