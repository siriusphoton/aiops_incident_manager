import os
import sys
import json
import logging
import re
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('servicenow-tools')

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SN_INSTANCE = os.getenv("SN_INSTANCE")
SN_USER = os.getenv("SN_USERNAME")
SN_PASS = os.getenv("SN_PASSWORD")

class ServiceNowClient:
    """ServiceNow API client with connection pooling and error handling."""

    def __init__(self, instance: str, username: str, password: str):
        if not SN_INSTANCE or not SN_USER or not SN_PASS:
            raise ValueError("ServiceNow credentials missing in .env")
            
        self.instance = SN_INSTANCE.rstrip('/')
        self.auth = (SN_USER, SN_PASS)
        self.client = httpx.AsyncClient(
            timeout=30.0,
            verify=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"ServiceNow client initialized for: {self.instance}")

    async def _handle_request(self, func, *args, **kwargs) -> Dict[str, Any]:
        """Generic error handler to ensure consistent JSON returns."""
        try:
            response = await func(*args, **kwargs)
            response.raise_for_status()
            
            if not response.text.strip():
                return {"success": False, "error": "Empty response body from ServiceNow."}
                
            data = response.json()
            return {"success": True, "data": data.get('result', data)}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error: {e.response.text}")
            return {"success": False, "error": f"HTTP {e.response.status_code}", "details": e.response.text}
        except Exception as e:
            logger.error(f"API error: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def query_table(self, table: str, params: dict) -> Dict[str, Any]:
        url = f"{self.instance}/api/now/table/{table}"
        headers = {"Accept": "application/json"}
        result = await self._handle_request(self.client.get, url, auth=self.auth, headers=headers, params=params)
        
        # Normalize data to always be a list
        if result["success"]:
            data_list = result["data"] if isinstance(result["data"], list) else [result["data"]]
            result["data"] = data_list
            result["count"] = len(data_list)
        return result

    async def modify_record(self, table: str, sys_id: str, payload: dict) -> Dict[str, Any]:
        url = f"{self.instance}/api/now/table/{table}/{sys_id}?sysparm_input_display_value=true"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        return await self._handle_request(self.client.patch, url, auth=self.auth, headers=headers, json=payload)

    async def insert_record(self, table: str, payload: dict) -> Dict[str, Any]:
        url = f"{self.instance}/api/now/table/{table}?sysparm_input_display_value=true"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        return await self._handle_request(self.client.post, url, auth=self.auth, headers=headers, json=payload)

    async def close(self):
        await self.client.aclose()


# ============================================================================
# EXPORTED TOOL FUNCTIONS
# ============================================================================

async def query_servicenow_records(client: ServiceNowClient, table_name: str, query: str = "", limit: int = 10) -> Dict[str, Any]:
    """Fetches a list of records. sysparm_display_value=all ensures we get sys_ids AND readable text."""
    logger.info(f"Querying {table_name} with query: {query}")
    params = {"sysparm_limit": limit, "sysparm_display_value": "all"}
    if query: params["sysparm_query"] = query
    return await client.query_table(table_name, params)

async def get_single_servicenow_record(client: ServiceNowClient, table_name: str, record_number: str) -> Dict[str, Any]:
    """Fetches full details of a single record by its number (e.g., INC0000052)."""
    logger.info(f"Fetching single record: {record_number} from {table_name}")
    params = {"sysparm_query": f"number={record_number}", "sysparm_limit": 1, "sysparm_display_value": "all"}
    return await client.query_table(table_name, params)

async def update_servicenow_record(client: ServiceNowClient, table_name: str, sys_id: str, payload: dict) -> Dict[str, Any]:
    """Updates a record. sys_id MUST be the 32-character hexadecimal string."""
    logger.info(f"Updating {table_name} record {sys_id}")
    if not re.fullmatch(r'[0-9a-f]{32}', sys_id):
        return {"success": False, "error": f"Invalid sys_id format: '{sys_id}'"}
    return await client.modify_record(table_name, sys_id, payload)

async def create_servicenow_record(client: ServiceNowClient, table_name: str, payload: dict) -> Dict[str, Any]:
    """Creates a new record (Used for Problem Generation)."""
    logger.info(f"Creating new record in {table_name}")
    return await client.insert_record(table_name, payload)