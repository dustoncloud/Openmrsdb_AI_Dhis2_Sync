# ---------------------------------------------------------
# Bahmni AI + DHIS2 Sync Tool
# Copyright (c) 2025 [Deepak Neupane]
# Licensed under the MIT License (see LICENSE for details)
# ---------------------------------------------------------
import json
import os

class DHIS2Mapper:
    def __init__(self, config_filename="mapping.json"):
        base_path = os.path.dirname(__file__)
        config_path = os.path.join(base_path, config_filename)
        
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            self.org_unit = self.config.get("orgUnit")
        except Exception as e:
            print(f"CRITICAL: Could not load {config_filename}. Error: {e}")
            self.config = {}
            self.org_unit = None

    def transform(self, sql_rows, period, report_name):
        """
        MODIFIED: Now maps specific JSON rules to specific SQL rows to prevent duplication.
        """
        data_values = []
        report_config = self.config.get("reports", {}).get(report_name, {})
        rules = report_config.get("mappings", [])

        if not rules:
            print(f"Warning: No mapping rules found for report: {report_name}")
            return None

        # UPDATED LOGIC: Loop through rules first to check for specific row assignments
        for rule in rules:
            col_name = rule["sql_column"]
            coc_id = rule.get("categoryOptionCombo")
            # Get the target row index from JSON (e.g., 0 for row 1, 1 for row 2)
            target_row_idx = rule.get("row") 
            
            # Identify which rows from the SQL results to process for this rule
            rows_to_process = []
            if target_row_idx is not None:
                # If JSON specifies a row, only process that one row
                if 0 <= target_row_idx < len(sql_rows):
                    rows_to_process = [sql_rows[target_row_idx]]
            else:
                # If no row is specified in JSON, process all rows (original behavior)
                rows_to_process = sql_rows

            for row_data in rows_to_process:
                # Check if the column exists in this row
                if col_name in row_data:
                    val = row_data[col_name]
                    
                    # Skip empty values to prevent DHIS2 API errors (400 Bad Request)
                    if val is None or str(val).strip() == "":
                        continue
                    
                    if coc_id:
                        data_values.append({
                            "dataElement": rule["dataElement"],
                            "categoryOptionCombo": coc_id,
                            "orgUnit": self.org_unit,
                            "period": period,
                            "value": str(val).strip()
                        })
                    else:
                        print(f"Mapping Warning: No categoryOptionCombo found in JSON for {col_name}")
                else:
                    # Log if the SQL result column name doesn't match the JSON 'sql_column'
                    print(f"Mapping Error: Column '{col_name}' not found in SQL results.")
        
        # Return the formatted payload for the DHIS2 /dataValueSets endpoint
        return {"dataValues": data_values} if data_values else None