# Pyrogram - Telegram MTProto API Client Library for Python
# Copyright (C) 2017-2019 Dan Tès <https://github.com/delivrance>
#
# This file is part of Pyrogram.
#
# Pyrogram is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pyrogram is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Pyrogram.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import base64
import struct
import sys
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Union, List

import pyrogram

from . import BaseClient
from ...api import types


def decode(s: str) -> bytes:
    s = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    r = b""

    assert s[-1] == 2

    i = 0
    while i < len(s) - 1:
        if s[i] != 0:
            r += bytes([s[i]])
        else:
            r += b"\x00" * s[i + 1]
            i += 1

        i += 1

    return r


def encode(s: bytes) -> str:
    r = b""
    n = 0

    for i in s + bytes([2]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])

    return base64.urlsafe_b64encode(r).decode().rstrip("=")


async def ainput(prompt: str = ""):
    print(prompt, end="", flush=True)

    with ThreadPoolExecutor(1) as executor:
        return (await asyncio.get_event_loop().run_in_executor(
            executor, sys.stdin.readline
        )).rstrip()


def get_peer_id(input_peer) -> int:
    return (
        input_peer.user_id if isinstance(input_peer, types.InputPeerUser)
        else -input_peer.chat_id if isinstance(input_peer, types.InputPeerChat)
        else int("-100" + str(input_peer.channel_id))
    )


def get_input_peer(peer_id: int, access_hash: int):
    return (
        types.InputPeerUser(user_id=peer_id, access_hash=access_hash) if peer_id > 0
        else types.InputPeerChannel(channel_id=int(str(peer_id)[4:]), access_hash=access_hash)
        if (str(peer_id).startswith("-100") and access_hash)
        else types.InputPeerChat(chat_id=-peer_id)
    )


def get_offset_date(dialogs):
    for m in reversed(dialogs.messages):
        if isinstance(m, types.MessageEmpty):
            continue
        else:
            return m.date
    else:
        return 0


def get_input_media_from_file_id(
    file_id_str: str,
    expected_media_type: int = None
) -> Union[types.InputMediaPhoto, types.InputMediaDocument]:
    try:
        decoded = decode(file_id_str)
    except Exception:
        raise ValueError("Failed to decode file_id: {}".format(file_id_str))
    else:
        media_type = decoded[0]

        if expected_media_type is not None:
            if media_type != expected_media_type:
                media_type_str = BaseClient.MEDIA_TYPE_ID.get(media_type, None)
                expected_media_type_str = BaseClient.MEDIA_TYPE_ID.get(expected_media_type, None)

                raise ValueError(
                    'Expected: "{}", got "{}" file_id instead'.format(expected_media_type_str, media_type_str)
                )

        if media_type in (0, 1, 14):
            raise ValueError("This file_id can only be used for download: {}".format(file_id_str))

        if media_type == 2:
            unpacked = struct.unpack("<iiqqc", decoded)
            dc_id, file_id, access_hash, thumb_size = unpacked[1:]

            return types.InputMediaPhoto(
                id=types.InputPhoto(
                    id=file_id,
                    access_hash=access_hash,
                    file_reference=b""
                )
            )

        if media_type in (3, 4, 5, 8, 9, 10, 13):
            unpacked = struct.unpack("<iiqq", decoded)
            dc_id, file_id, access_hash = unpacked[1:]

            return types.InputMediaDocument(
                id=types.InputDocument(
                    id=file_id,
                    access_hash=access_hash,
                    file_reference=b""
                )
            )

        raise ValueError("Unknown media type: {}".format(file_id_str))


async def parse_messages(client, messages: types.messages.Messages, replies: int = 1) -> List["pyrogram.Message"]:
    users = {i.id: i for i in messages.users}
    chats = {i.id: i for i in messages.chats}

    if not messages.messages:
        return pyrogram.List()

    parsed_messages = []

    for message in messages.messages:
        parsed_messages.append(await pyrogram.Message._parse(client, message, users, chats, replies=0))

    if replies:
        messages_with_replies = {i.id: getattr(i, "reply_to_msg_id", None) for i in messages.messages}
        reply_message_ids = [i[0] for i in filter(lambda x: x[1] is not None, messages_with_replies.items())]

        if reply_message_ids:
            reply_messages = await client.get_messages(
                parsed_messages[0].chat.id,
                reply_to_message_ids=reply_message_ids,
                replies=replies - 1
            )

            for message in parsed_messages:
                reply_id = messages_with_replies[message.message_id]

                for reply in reply_messages:
                    if reply.message_id == reply_id:
                        message.reply_to_message = reply

    return pyrogram.List(parsed_messages)


def parse_deleted_messages(client, update) -> List["pyrogram.Message"]:
    messages = update.messages
    channel_id = getattr(update, "channel_id", None)

    parsed_messages = []

    for message in messages:
        parsed_messages.append(
            pyrogram.Message(
                message_id=message,
                chat=pyrogram.Chat(
                    id=int("-100" + str(channel_id)),
                    type="channel",
                    client=client
                ) if channel_id is not None else None,
                client=client
            )
        )

    return pyrogram.List(parsed_messages)


def unpack_inline_message_id(inline_message_id: str) -> types.InputBotInlineMessageID:
    r = inline_message_id + "=" * (-len(inline_message_id) % 4)
    r = struct.unpack("<iqq", base64.b64decode(r, altchars="-_"))

    return types.InputBotInlineMessageID(
        dc_id=r[0],
        id=r[1],
        access_hash=r[2]
    )
