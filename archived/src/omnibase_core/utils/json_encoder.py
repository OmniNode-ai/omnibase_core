import datetime
import json
import uuid


class OmniJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime.datetime | datetime.date):
            return obj.isoformat()
        return super().default(obj)
