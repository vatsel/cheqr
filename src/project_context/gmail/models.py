from typing import Any
from enum import Enum
from datetime import datetime

from pydantic import BaseModel

from .utils import internalDate_to_str


class MimeType(Enum):
    IMG_PNG = "image/png"
    IMG_JPEG = "image/jpeg"
    TXT_HTML = "text/html"


class GmailMsgPartHeaderInfo(BaseModel):
    content_type: str 
    content_transfer_encoding: str | None

    @classmethod
    def from_cached_json(cls, json_data:list[dict[str,Any]]) -> "GmailMsgPartHeaderInfo":
        assert(isinstance(json_data, list))

        _content_type = None
        encoding = ""
        for json_item in json_data:
            assert('name' in json_item)
            if json_item['name'] == 'Content-Type':
                _content_type = json_item['value']
            elif json_item['name'] == 'Content-Transfer-Encoding':
                encoding = json_item['value']

        if _content_type is None:
            raise ValueError(f"No element found with a key of 'name' and "
                             f"value of 'Content-Type'. Full JSON data:\n{str(json_data)}")
        
        return cls(
            content_type=_content_type,
            content_transfer_encoding=encoding)
    
    @property
    def is_text_html_type(self) -> bool:
        return "text/html" in self.content_type
    
    @property
    def is_text_plain_type(self) -> bool:
        return "text/plain" in self.content_type
    
    @property
    def is_image_jpg_type(self) -> bool:
        return "image/jpeg" in self.content_type
    
    @property
    def is_image_png_type(self) -> bool:
        return "image/png" in self.content_type
    

class GmailMsgPayloadSubPart(BaseModel):
    mime_type:str
    header_info:GmailMsgPartHeaderInfo
    body:dict[str,Any]
    raw_json: dict[str,Any] | None

    @classmethod
    def from_cached_json(cls, json_data:dict[str,Any]) -> "GmailMsgPayloadSubPart":
        assert(isinstance(json_data, dict))

        return cls(
            mime_type = json_data['mimeType'],
            header_info = GmailMsgPartHeaderInfo.from_cached_json(
                json_data=json_data['headers']),
            body=json_data['body'],
            raw_json=json_data
        )
        

class GmailMsgPayloadPart(BaseModel):
    mime_type: str
    header_info: GmailMsgPartHeaderInfo
    sub_parts: list[GmailMsgPayloadSubPart] # may be empty
    body: dict[str,Any] | None
    raw_json: dict[str,Any] | None

    @classmethod
    def from_cached_json(cls, json_data:dict[str,Any]) -> "GmailMsgPayloadPart":
        assert(isinstance(json_data, dict))

        # sometimes there's subparts
        _sub_parts = list[GmailMsgPayloadSubPart]()
        if 'parts' in json_data:
            for p in json_data['parts']:
                _sub_parts.append(GmailMsgPayloadSubPart.from_cached_json(json_data=p))

        _body = None
        if 'body' in json_data:
            _body = json_data['body']

        return cls(
            mime_type = json_data['mimeType'],
            header_info = GmailMsgPartHeaderInfo.from_cached_json(
                json_data=json_data['headers']),
            sub_parts=_sub_parts,
            body = _body,
            raw_json=json_data
        )


class GmailMsgPayload(BaseModel):
    # TODO: create data classes for all the below
    body: dict[str, Any]
    headers: list[dict[str, Any]]
    mime_type: str
    parts: list[GmailMsgPayloadPart]
    raw_json: dict[str,Any] | None

    @classmethod
    def from_cached_json(cls, json_data:dict[str,Any]) -> "GmailMsgPayload":
        assert(isinstance(json_data, dict))

        _parts = list[GmailMsgPayloadPart]()
        for p in json_data['parts']:
            _parts.append(GmailMsgPayloadPart.from_cached_json(json_data=p))

        return cls(
            body = json_data['body'],
            headers = json_data['headers'],
            mime_type = json_data['mimeType'],
            parts = _parts,
            raw_json = json_data
        )


class GmailMsg(BaseModel):
    """This is a Gmail-specific way of keeping information in parts."""
    msg_id:str # can be shared across messages
    payload:GmailMsgPayload
    internal_date: datetime
    raw_json: dict[str,Any] | None

    # TODO: labelIds: Optional[list[?]] 
    # TODO: internalDate: str

    @classmethod
    def from_cached_json(cls, json_data:dict[str,Any]) -> "GmailMsg":
        assert(isinstance(json_data, dict))
        _payload = GmailMsgPayload.from_cached_json(json_data=json_data['payload'])
        return cls(msg_id=json_data['id'], 
                   payload=_payload,
                   internal_date=internalDate_to_str(json_data['internalDate']),
                   raw_json=json_data)


class GmailThread(BaseModel):
    '''On gmail, messages (emails) are grouped as threads'''
    thread_id:str # TODO: is it shared across messages?
    msgs: list[GmailMsg]
    raw_json: dict[str,Any] | None

    @classmethod
    def from_cached_json(cls, json_data:dict[str,Any]) -> "GmailThread":
        assert(isinstance(json_data, dict))

        # TODO: error logs if keys don't exist.
        _msgs = list[GmailMsg]()
        for msg in json_data['messages']:
            _msgs.append(GmailMsg.from_cached_json(json_data=msg))
        
        return cls(thread_id=json_data['id'], 
                   msgs=_msgs,
                   raw_json=json_data)

