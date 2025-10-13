import pandas as pd
import os
from datetime import datetime
import json

def enhanced_html_dashboard():
    print("Creating Enhanced HTML Dashboard...")
    
    # Find and combine all CSV files
    csv_files = [f for f in os.listdir('.') if f.startswith('traffic_analysis_report') and f.endswith('.csv')]
    
    if not csv_files:
        print("ERROR: No detection files found!")
        return
    
    # Combine all data
    df = pd.DataFrame()
    for file in csv_files:
        try:
            temp_df = pd.read_csv(file)
            df = pd.concat([df, temp_df], ignore_index=True)
            print(f"Loaded {file}")
        except Exception as e:
            print(f"ERROR loading {file}: {e}")
    
    if df.empty:
        print("ERROR: No data available for dashboard!")
        return
    
    print(f"SUCCESS: Loaded {len(df)} total records")
    
    # Process data
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
    
    # Generate statistics
    total_detections = len(df)
    vehicle_types = df['vehicle_type'].value_counts()
    hourly_traffic = df['hour'].value_counts().sort_index() if 'hour' in df.columns else None
    
    # Prepare data for JavaScript
    vehicle_labels = json.dumps(vehicle_types.index.tolist())
    vehicle_data = json.dumps(vehicle_types.values.tolist())
    
    if hourly_traffic is not None:
        hourly_labels = json.dumps(hourly_traffic.index.tolist())
        hourly_data = json.dumps(hourly_traffic.values.tolist())
    else:
        hourly_labels = "[]"
        hourly_data = "[]"
    
    # Create enhanced HTML content with fixed CSS
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Traffic Detection Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
            border-left: 4px solid #667eea;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .chart-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .chart {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
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
        @media (max-width: 768px) {{
            .chart-container {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Traffic Detection Dashboard</h1>
            <p>Real-time Traffic Analysis and Monitoring</p>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats-container">
            <div class="stat-card">
                <div class="stat-number">{total_detections}</div>
                <div>Total Detections</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(vehicle_types)}</div>
                <div>Vehicle Types</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(csv_files)}</div>
                <div>Source Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{df['date'].nunique() if 'date' in df.columns else 'N/A'}</div>
                <div>Days Analyzed</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart">
                <h3>Vehicle Type Distribution</h3>
                <canvas id="vehicleChart"></canvas>
            </div>
            <div class="chart">
                <h3>Hourly Traffic Pattern</h3>
                <canvas id="hourlyChart"></canvas>
            </div>
        </div>
        
        <div class="chart">
            <h3>Recent Detections</h3>
            <table>
                <thead>
                    <tr>
                        <th>Vehicle Type</th>
                        <th>Confidence</th>
                        <th>Source File</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody>"""

    # Add recent detections
    recent_data = df.head(20)
    for _, row in recent_data.iterrows():
        confidence = row.get('confidence', 'N/A')
        if isinstance(confidence, float):
            confidence = f"{confidence:.2f}"
        
        timestamp = row.get('timestamp', 'N/A')
        if pd.notna(timestamp) and timestamp != 'N/A':
            timestamp = str(timestamp)[:19]
        
        html_content += f"""
                    <tr>
                        <td>{row['vehicle_type']}</td>
                        <td>{confidence}</td>
                        <td>{row['source_file']}</td>
                        <td>{timestamp}</td>
                    </tr>"""

    html_content += f"""
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // Vehicle Type Chart
        const vehicleCtx = document.getElementById('vehicleChart').getContext('2d');
        const vehicleChart = new Chart(vehicleCtx, {{
            type: 'pie',
            data: {{
                labels: {vehicle_labels},
                datasets: [{{
                    data: {vehicle_data},
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                        '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'right',
                    }},
                    title: {{
                        display: true,
                        text: 'Vehicle Distribution'
                    }}
                }}
            }}
        }});

        // Hourly Traffic Chart
        const hourlyCtx = document.getElementById('hourlyChart').getContext('2d');
        const hourlyChart = new Chart(hourlyCtx, {{
            type: 'line',
            data: {{
                labels: {hourly_labels},
                datasets: [{{
                    label: 'Detections per Hour',
                    data: {hourly_data},
                    borderColor: '#36A2EB',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    tension: 0.4,
                    fill: true
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Hourly Traffic Pattern'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Number of Detections'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Hour of Day'
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    # Save HTML file
    html_file = f"enhanced_traffic_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"SUCCESS: Enhanced HTML Dashboard created: {html_file}")
    print("Open this file in your web browser to view the interactive dashboard")

if __name__ == "__main__":
    enhanced_html_dashboard()
