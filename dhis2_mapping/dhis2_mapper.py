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
        Processes multi-row, multi-column data.
        Accepts any value type (Text, Numeric, etc.)
        """
        data_values = []
        report_config = self.config.get("reports", {}).get(report_name, {})
        rules = report_config.get("mappings", [])

        if not rules:
            print(f"Warning: No mapping rules found for report: {report_name}")
            return None

        for rule in rules:
            col_name = rule["sql_column"]
            row_idx = rule.get("row", 0)
            
            # 1. Row Check: Ensures the row exists in the results
            if len(sql_rows) > row_idx:
                target_row = sql_rows[row_idx]
                
                # 2. Column Check: Ensures the column exists in that row
                if col_name in target_row:
                    val = target_row[col_name]
                    
                    # Skip only if truly empty/null to avoid DHIS2 400 errors
                    if val is None or str(val).strip() == "":
                        continue
                    
                    # Package the data - DHIS2 values are always sent as strings
                    data_values.append({
                        "dataElement": rule["dataElement"],
                        "categoryOptionCombo": rule.get("categoryOptionCombo", "HllvX50cXC0"),
                        "orgUnit": self.org_unit,
                        "period": period,
                        "value": str(val).strip()
                    })
                else:
                    print(f"Mapping Error: Column '{col_name}' not found in SQL results.")
            else:
                print(f"Mapping Error: Row {row_idx} requested, but only {len(sql_rows)} rows returned.")
        
        # Return the payload only if we have values to send
        return {"dataValues": data_values} if data_values else None