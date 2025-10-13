# simple_dashboard.py - Simple HTML dashboard
import pandas as pd
import os
from datetime import datetime

def generate_html_dashboard():
    # Find detection files
    csv_files = [f for f in os.listdir('.') if f.startswith('traffic_analysis_report_') and f.endswith('.csv')]
    
    if not csv_files:
        print("❌ No detection files found!")
        return
    
    # Load data
    all_data = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            df['source_file'] = file
            all_data.append(df)
        except Exception as e:
            print(f"Warning: Could not load {file}: {e}")
    
    if not all_data:
        print("❌ No data loaded!")
        return
    
    df = pd.concat(all_data, ignore_index=True)
    
    # Generate HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Traffic Detection Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚗 Traffic Detection Analytics</h1>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value">{len(df)}</div>
            <div class="metric-label">Total Vehicles</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{df['vehicle_type'].nunique()}</div>
            <div class="metric-label">Vehicle Types</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{df['source_file'].nunique()}</div>
            <div class="metric-label">Data Files</div>
        </div>
        {'<div class="metric-card"><div class="metric-value">' + f"{df['confidence'].mean():.2f}" + '</div><div class="metric-label">Avg Confidence</div></div>' if 'confidence' in df.columns else ''}
    </div>
    
    <div class="chart-container">
        <h2>🚗 Vehicle Type Distribution</h2>
        <table>
            <thead>
                <tr>
                    <th>Vehicle Type</th>
                    <th>Count</th>
                    <th>Percentage</th>
                </tr>
            </thead>
            <tbody>
"""

    # Add vehicle type rows
    vehicle_counts = df['vehicle_type'].value_counts()
    total_vehicles = len(df)
    
    for vehicle_type, count in vehicle_counts.items():
        percentage = (count / total_vehicles) * 100
        html_content += f"""
                <tr>
                    <td>{vehicle_type}</td>
                    <td>{count}</td>
                    <td>{percentage:.1f}%</td>
                </tr>
"""
    
    html_content += """
            </tbody>
        </table>
    </div>
    
    <div class="chart-container">
        <h2>📊 Recent Detections</h2>
        <table>
            <thead>
                <tr>
                    <th>Vehicle Type</th>
                    <th>Confidence</th>
                    <th>Source File</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Add recent detections
    recent_data = df.head(20)
    for _, row in recent_data.iterrows():
        html_content += f"""
                <tr>
                    <td>{row['vehicle_type']}</td>
                    <td>{row.get('confidence', 'N/A')}</td>
                    <td>{row['source_file']}</td>
                    <td>{row.get('timestamp', 'N/A')}</td>
                </tr>
"""
    
    html_content += """
            </tbody>
        </table>
    </div>
    
    <div style="text-align: center; margin-top: 30px; color: #666;">
        <p>Generated by Traffic Detection System</p>
    </div>
</body>
</html>
"""
    
    # Save HTML file
    html_file = f"traffic_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML Dashboard created: {html_file}")
    print("🌐 Open this file in your web browser to view the dashboard")

if __name__ == "__main__":
    generate_html_dashboard()
