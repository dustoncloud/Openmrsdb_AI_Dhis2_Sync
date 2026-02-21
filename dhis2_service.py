# ---------------------------------------------------------
# Bahmni AI + DHIS2 Sync Tool
# Copyright (c) 2025 [Deepak Neupane]
# Licensed under the MIT License (see LICENSE for details)
# ---------------------------------------------------------
import requests
import json

class DHIS2Service:
    def __init__(self):
        # URL matches your browser URL exactly
        self.base_url = "https://play.im.dhis2.org/stable-2-42-3-1/api"
        self.auth = ("admin", "district")
        self.headers = {"Content-Type": "application/json"}

    def push_data(self, payload):
        url = f"{self.base_url}/dataValueSets"
        try:
            print(f"DEBUG: Sending to DHIS2: {json.dumps(payload)}")
            response = requests.post(
                url, 
                auth=self.auth, 
                headers=self.headers, 
                data=json.dumps(payload)
            )
            
            # Error Handling
            print(f"DEBUG: DHIS2 Status Code: {response.status_code}")
            print(f"DEBUG: DHIS2 Response Body: {response.text}")
            
            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, response.text
        except Exception as e:
            print(f"DEBUG: Connection Exception: {str(e)}")
            return False, str(e)