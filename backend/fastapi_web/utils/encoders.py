from datetime import datetime
import json
from typing import Any

from bson import ObjectId


class DateTimeEncoder(json.JSONEncoder):
    """JSONEncoder для datetime."""

    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat() 
        elif isinstance(o, ObjectId):
            return str(o)