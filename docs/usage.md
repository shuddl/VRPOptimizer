docs/usage.md
VRP Optimizer User Guide
Quick Start
1. Prepare Input Data
Create an Excel file with the following columns:

Shipment ID
Origin City
Origin State
Destination City
Destination State
Pallet Count (1-26)

Example:
CopyShipment ID | Origin City | Origin State | Destination City | Destination State | Pallet Count
SHP001      | Chicago    | IL           | Detroit         | MI               | 10
SHP002      | Dallas     | TX           | Houston         | TX               | 15
2. Upload and Optimize

Open web interface (http://localhost:8501)
Click "Upload File"
Select your Excel file
Click "Optimize Routes"

3. View Results
The system will display:

Interactive route map
Route details table
Performance metrics
Cost analysis

Advanced Features
Custom Parameters
Adjust optimization settings:

Maximum vehicles
Maximum route distance
Time limit
LIFO constraints

Export Options
Export results as:

Excel file
JSON data
Route visualization
Analytics report

Batch Processing
For large datasets:

Use the API endpoint
Implement rate limiting
Handle responses asynchronously

Best Practices
Data Preparation

Verify addresses
Check pallet counts
Remove duplicates
Validate state codes

Optimization Strategy

Start with small batches
Adjust parameters gradually
Monitor performance
Review unassigned shipments

Performance Tips

Use caching
Batch geocoding requests
Optimize file sizes
Monitor system resources

Troubleshooting
Common Issues

File Upload Errors

Check file format
Verify required columns
Check file size limit


Geocoding Failures

Verify addresses
Check API key
Monitor rate limits


Optimization Issues

Review constraints
Check data validity
Monitor resource usage



Support
For additional help:

Check error logs
Review documentation
Contact support team

Security
Data Protection

All data is encrypted
Files are temporarily stored
Regular cleanup processes

Access Control

API key required
Rate limiting enforced
Session management

Maintenance
Regular Tasks

Clear cache
Update geocoding data
Monitor logs
Backup data

Updates

Check for new versions
Review changelog
Test in staging
Deploy safely