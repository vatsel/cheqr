import base64
from typing import Any
from quopri import decodestring
from email import message_from_string
from email.message import Message


from ..utils import string_is_blank

from ..projects.models import Person, EmailMsg
from ..logging.service import setup_logger

from .models import GmailMsg, GmailMsgPayloadPart
from .models import GmailMsgPayloadSubPart, GmailThread
from .utils import remove_cid_references
from .utils import remove_gmail_trailing_quoted_content


def _decode_body_data(body:dict[str,Any]) -> str:
    """For use with personal database only"""
    if 'data' not in body:
        assert('size' in body)
        if int(body['size']) > 0:
            raise ValueError(f"body without 'data' key is expected to have zero size.\n{body}")
        return "" # skipping subpart with zero data
            
    encoded_text = body['data']
    return base64.urlsafe_b64decode(encoded_text).decode('utf-8').rstrip()


def decode_multipart_mimetype(subparts:list[GmailMsgPayloadSubPart]) -> str:
    """For use with personal database only"""
    logger = setup_logger()
    
    if len(subparts) == 0:
        logger.warning("passed no message payload subparts")
        return ""

    decoded_str = ""
    skipped_img_count = 0
    for subpart in subparts:
        if subpart.mime_type == 'image/png' or subpart.mime_type == 'image/jpeg':
            skipped_img_count += 1
            continue

        if subpart.header_info.is_text_html_type:
            logger.debug("skipping text/html formatted version (assumed to be a duplicate)")
            continue
        
        decoded_str += _decode_body_data(body=subpart.body)
    
    if skipped_img_count > 0:
        logger.debug(f"decode_multipart_mimetype: Skipped {skipped_img_count} image subparts")
    
    if len(decoded_str) == 0:
        logger.debug("No TEXT decoded from payload subparts.")
    return decoded_str


def decode_text_mimetype(payloadpart:GmailMsgPayloadPart) -> str:
    """For use with personal database only"""
    if payloadpart.body is None:
        raise ValueError(f".body was not set for payload part of mimeType {payloadpart.mime_type}.")
    
    return _decode_body_data(body=payloadpart.body)


def email_body_to_str(message_part: Message) -> str:
    logger = setup_logger()
    
    content_transfer_encoding = message_part.get('Content-Transfer-Encoding', '').lower().strip()
    logger.debug(f"transfer_encoding: {content_transfer_encoding}")

    if content_transfer_encoding == 'quoted-printable':
        payload = message_part.get_payload(decode=True)
        if isinstance(payload, str):
            return decodestring(payload).decode('utf-8')
        elif isinstance(payload, bytes):
            return payload.decode('utf-8')
        else:
            raise TypeError(f"Unhandled type of payload: {type(payload)}")
        
    elif content_transfer_encoding == 'base64':
        payload = message_part.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode('utf-8')
        else:
            raise TypeError(f"Unhandled type of payload: {type(payload)}")
        
    elif string_is_blank(content_transfer_encoding):
        payload = message_part.get_payload()
        if isinstance(payload, str):
            return payload
        else:
            raise TypeError(f"Unhandled type of payload = {type(payload)}.\n"
                            f"Expected an unencoded str because there's no value"
                            f" in Content-Transfer-Encoding")

    else:
        raise TypeError(f"Unhandled value of Content-Transfer-Encoding: {content_transfer_encoding}")


def get_msg_content(message:GmailMsg, clip_text:int = 0) -> str:
    """when clip_text is set to 0, text won't be clipped."""
    logger = setup_logger()

    skipped_img_count = 0
    decoded_str = ""

    for part in message.payload.parts:                 
        if part.header_info.is_image_jpg_type or part.mime_type == "image/png":
            skipped_img_count += 1
            continue
        
        if "application" in part.mime_type:
            # TODO: handle attachments. eventually.
            if part.mime_type == 'application/octet-stream':
                logger.debug(f"skipping binary message part {part.mime_type}")
                continue
            logger.debug(f"Skipping application mimeType: {part.mime_type}")
            continue

        if part.mime_type == "multipart/alternative":
            decoded_str += decode_multipart_mimetype(subparts=part.sub_parts)
        elif part.mime_type == "multipart/related":
            for sub_part in part.sub_parts:
                if sub_part.mime_type == "image/png":
                    skipped_img_count += 1
                else:
                    decoded_str += decode_multipart_mimetype(subparts=part.sub_parts)
        elif part.mime_type == "text/html":
            logger.debug("skipping text/html formatted version (assumed to be a duplicate)")
        elif part.mime_type == "text/plain":
            decoded_str += decode_text_mimetype(payloadpart=part)

        else:
            raise ValueError(f"UNHANDLED type of part {part}") #TODO, replace with log in prod
    

    decoded_str = remove_gmail_trailing_quoted_content(text=decoded_str)
    decoded_str = remove_cid_references(text=decoded_str)

    if clip_text > 0:
        decoded_str = decoded_str[:clip_text]
    
    if skipped_img_count > 0:
        logger.debug(f"Skipped {skipped_img_count} image parts / subparts")
    
    return decoded_str


def get_msg_data_from_gmail(message:GmailMsg) -> EmailMsg:
    writer = None
    sent_to = list[Person]()
    subject = ""

    for header in message.payload.headers:
        name = header['name'].lower()
        val =  header['value']

        if name == 'from':
            person_list = Person.parse_str_to_person_objs(text=val)
            if len(person_list) != 1:
                raise ValueError(f"Unexpected size of person_list {person_list}")
            writer = person_list[0]
        elif name == 'to':
            sent_to += Person.parse_str_to_person_objs(text=val)
        elif name == 'cc':
            sent_to += Person.parse_str_to_person_objs(text=val)
        elif name == 'bcc':
            sent_to += Person.parse_str_to_person_objs(text=val)
        elif name == 'subject':
            subject = val
        
    if writer is None:
        raise ValueError(f"Found no writer in email.\n"
                         f"Possibly no 'from' header in email. Headers:\n"
                         f"{message.payload.headers}")

    content = get_msg_content(message=message)

    return EmailMsg(
        message_id=message.msg_id,
        received=message.internal_date,
        writer=writer,
        subject=subject,
        content=content,
        sent_to=sent_to,
        attachments=None
    )


def get_concatenated_msg_data_from_gmail_thread(thread:GmailThread) -> str:
    emails_concat_full_info = ""
    for gmail_msg_data in thread.msgs:
        msg_info_str = get_msg_data_from_gmail(message=gmail_msg_data).info_str
        emails_concat_full_info += msg_info_str + "\n"
        
    return emails_concat_full_info


def parse_raw_gmail_content_to_str(raw_content:str, strip_quotes:bool = True) -> str:
    '''Written for gmail getRawContent()'''
    assert(isinstance(raw_content, str))
    logger = setup_logger()

    email_message = message_from_string(s=raw_content)
    decoded_body_text = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                decoded_body_text += email_body_to_str(part)
            elif content_type == "text/html":
                logger.debug("Skipping text/html formatted version (assumed to be a duplicate)")
            else:
                logger.warning(f"Skipping processing of unhandled mime type of content: {content_type}")
    else:
        decoded_body_text = email_body_to_str(email_message)

    if strip_quotes:
        decoded_body_text = remove_gmail_trailing_quoted_content(text=decoded_body_text)
    decoded_body_text = remove_cid_references(text=decoded_body_text)

    return decoded_body_text


