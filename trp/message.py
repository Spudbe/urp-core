import json
import uuid
from datetime import datetime
from dataclasses import asdict

PROTOCOL_VERSION = "0.3.0"

class TRPMessage:
    """
    A wrapper for TRP objects when sending over the wire.
    Carries metadata + a JSON‐serializable payload.
    """
    def __init__(self, msg_type: str, payload, sender: str,
                 message_id: str = None, timestamp: str = None,
                 protocol_version: str = PROTOCOL_VERSION):
        self.message_id = message_id or str(uuid.uuid4())
        # RFC3339 / ISO8601 UTC time
        self.timestamp = timestamp or datetime.utcnow().isoformat() + "Z"
        self.sender = sender
        self.type = msg_type
        self.payload = payload  # must have to_dict()
        self.protocol_version = protocol_version

    def to_json(self, compact: bool = True) -> str:
        # Build the wrapper dict
        wrapper = {
            "protocol_version": self.protocol_version,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "type": self.type,
            # use the object's to_dict() if available, else fallback to dataclasses.asdict
            "payload": self.payload.to_dict() if hasattr(self.payload, "to_dict")
                       else asdict(self.payload),
        }
        if compact:
            return json.dumps(wrapper, separators=(",", ":"))
        else:
            return json.dumps(wrapper, indent=2)

    @classmethod
    def from_json(cls, json_str: str, payload_cls):
        """
        Reconstruct a TRPMessage from its JSON representation.
        payload_cls must implement from_dict().
        """
        data = json.loads(json_str)
        payload_data = data["payload"]
        payload = payload_cls.from_dict(payload_data)
        return cls(
            msg_type=data["type"],
            payload=payload,
            sender=data["sender"],
            message_id=data["message_id"],
            timestamp=data["timestamp"],
            protocol_version=data.get("protocol_version", PROTOCOL_VERSION),
        )
