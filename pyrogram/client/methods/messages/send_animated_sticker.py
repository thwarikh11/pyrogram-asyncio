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

import os
from typing import Union

import pyrogram
from pyrogram.api import functions, types
from pyrogram.client.ext import BaseClient, utils
from pyrogram.errors import FilePartMissing


class SendAnimatedSticker(BaseClient):
    def send_animated_sticker(
        self,
        chat_id: Union[int, str],
        animated_sticker: str,
        disable_notification: bool = None,
        reply_to_message_id: int = None,
        reply_markup: Union[
            "pyrogram.InlineKeyboardMarkup",
            "pyrogram.ReplyKeyboardMarkup",
            "pyrogram.ReplyKeyboardRemove",
            "pyrogram.ForceReply"
        ] = None,
        progress: callable = None,
        progress_args: tuple = ()
    ) -> Union["pyrogram.Message", None]:
        """Send .tgs animated stickers.

        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).

            animated_sticker (``str``):
                Animated sticker to send.
                Pass a file_id as string to send a animated sticker that exists on the Telegram servers,
                pass an HTTP URL as a string for Telegram to get a .webp animated sticker file from the Internet, or
                pass a file path as string to upload a new animated sticker that exists on your local machine.

            disable_notification (``bool``, *optional*):
                Sends the message silently.
                Users will receive a notification with no sound.

            reply_to_message_id (``int``, *optional*):
                If the message is a reply, ID of the original message.

            reply_markup (:obj:`InlineKeyboardMarkup` | :obj:`ReplyKeyboardMarkup` | :obj:`ReplyKeyboardRemove` | :obj:`ForceReply`, *optional*):
                Additional interface options. An object for an inline keyboard, custom reply keyboard,
                instructions to remove reply keyboard or to force a reply from the user.

            progress (``callable``, *optional*):
                Pass a callback function to view the upload progress.
                The function must take *(client, current, total, \*args)* as positional arguments (look at the section
                below for a detailed description).

            progress_args (``tuple``, *optional*):
                Extra custom arguments for the progress callback function. Useful, for example, if you want to pass
                a chat_id and a message_id in order to edit a message with the updated progress.

        Other Parameters:
            client (:obj:`Client`):
                The Client itself, useful when you want to call other API methods inside the callback function.

            current (``int``):
                The amount of bytes uploaded so far.

            total (``int``):
                The size of the file.

            *args (``tuple``, *optional*):
                Extra custom arguments as defined in the *progress_args* parameter.
                You can either keep *\*args* or add every single extra argument in your function signature.

        Returns:
            :obj:`Message` | ``None``: On success, the sent animated sticker message is returned, otherwise, in case the
            upload is deliberately stopped with :meth:`~Client.stop_transmission`, None is returned.
        Raises:
            RPCError: In case of a Telegram RPC error.
        """
        file = None

        try:
            if os.path.exists(animated_sticker):
                file = self.save_file(animated_sticker, progress=progress, progress_args=progress_args)
                media = types.InputMediaUploadedDocument(
                    mime_type=self.guess_mime_type(animated_sticker) or "application/x-tgsticker",
                    file=file,
                    attributes=[
                        types.DocumentAttributeFilename(file_name=os.path.basename(animated_sticker))
                    ]
                )
            elif animated_sticker.startswith("http"):
                media = types.InputMediaDocumentExternal(
                    url=animated_sticker
                )
            else:
                media = utils.get_input_media_from_file_id(animated_sticker, 5)

            while True:
                try:
                    r = self.send(
                        functions.messages.SendMedia(
                            peer=self.resolve_peer(chat_id),
                            media=media,
                            silent=disable_notification or None,
                            reply_to_msg_id=reply_to_message_id,
                            random_id=self.rnd_id(),
                            reply_markup=reply_markup.write() if reply_markup else None,
                            message=""
                        )
                    )
                except FilePartMissing as e:
                    self.save_file(animated_sticker, file_id=file.id, file_part=e.x)
                else:
                    for i in r.updates:
                        if isinstance(i, (types.UpdateNewMessage, types.UpdateNewChannelMessage)):
                            return pyrogram.Message._parse(
                                self, i.message,
                                {i.id: i for i in r.users},
                                {i.id: i for i in r.chats}
                            )
        except BaseClient.StopTransmission:
            return None
