docs/api.md
VRP Optimizer API Documentation
Overview
The VRP Optimizer provides a RESTful API for route optimization with LIFO (Last-In-First-Out) constraints.
Base URL
Copyhttp://localhost:8000/api/v1
Authentication
All API endpoints require an API key to be included in the request header:
CopyAuthorization: Bearer YOUR_API_KEY
Endpoints
POST /optimize
Optimize routes for a set of shipments.
Request

Content-Type: multipart/form-data
Body:
jsonCopy{
  "file": "Excel file (.xlsx, .xls)",
  "parameters": {
    "max_vehicles": 10,
    "max_distance": 800,
    "time_limit": 30
  }
}


Response
jsonCopy{
  "success": true,
  "solution": {
    "routes": [
      {
        "id": "R001",
        "stops": [
          {
            "type": "pickup",
            "shipment": {
              "id": "SHP001",
              "origin": {
                "city": "Chicago",
                "state": "IL"
              },
              "destination": {
                "city": "Detroit",
                "state": "MI"
              },
              "pallet_count": 10
            }
          }
        ],
        "total_distance": 237.1,
        "total_pallets": 10
      }
    ],
    "total_distance": 237.1,
    "total_cost": 592.75,
    "unassigned_shipments": []
  }
}
GET /health
Check API health status.
Response
jsonCopy{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0"
}
Error Handling
The API uses standard HTTP status codes and returns error details in the response:
jsonCopy{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid file format",
    "details": ["Only Excel files are supported"]
  }
}
Rate Limiting

100 requests per minute per API key
Headers include rate limit information:
CopyX-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200


SDK Examples
Python
pythonCopyimport requests

api_key = 'your_api_key'
url = 'http://localhost:8000/api/v1/optimize'

files = {
    'file': open('shipments.xlsx', 'rb')
}

headers = {
    'Authorization': f'Bearer {api_key}'
}

response = requests.post(url, files=files, headers=headers)
solution = response.json()
