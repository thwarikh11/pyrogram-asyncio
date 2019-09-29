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
import inspect
import logging
import math
import mimetypes
import os
import re
import shutil
import tempfile
import time
from configparser import ConfigParser
from hashlib import sha256, md5
from importlib import import_module
from pathlib import Path
from signal import signal, SIGINT, SIGTERM, SIGABRT
from typing import Union, List

from pyrogram.api import functions, types
from pyrogram.api.core import TLObject
from pyrogram.client.handlers import DisconnectHandler
from pyrogram.client.handlers.handler import Handler
from pyrogram.client.methods.password.utils import compute_check
from pyrogram.crypto import AES
from pyrogram.errors import (
    PhoneMigrate, NetworkMigrate, PhoneNumberInvalid,
    PhoneNumberUnoccupied, PhoneCodeInvalid, PhoneCodeHashEmpty,
    PhoneCodeExpired, PhoneCodeEmpty, SessionPasswordNeeded,
    PasswordHashInvalid, FloodWait, PeerIdInvalid, FirstnameInvalid, PhoneNumberBanned,
    VolumeLocNotFound, UserMigrate, ChannelPrivate, PhoneNumberOccupied,
    PasswordRecoveryNa, PasswordEmpty
)
from pyrogram.session import Auth, Session
from .ext import utils, Syncer, BaseClient, Dispatcher
from .ext.utils import ainput
from .methods import Methods
from .storage import Storage, FileStorage, MemoryStorage

log = logging.getLogger(__name__)


class Client(Methods, BaseClient):
    """Pyrogram Client, the main means for interacting with Telegram.

    Parameters:
        session_name (``str``):
            Pass a string of your choice to give a name to the client session, e.g.: "*my_account*". This name will be
            used to save a file on disk that stores details needed to reconnect without asking again for credentials.
            Alternatively, if you don't want a file to be saved on disk, pass the special name "**:memory:**" to start
            an in-memory session that will be discarded as soon as you stop the Client. In order to reconnect again
            using a memory storage without having to login again, you can use
            :meth:`~pyrogram.Client.export_session_string` before stopping the client to get a session string you can
            pass here as argument.

        api_id (``int``, *optional*):
            The *api_id* part of your Telegram API Key, as integer. E.g.: 12345
            This is an alternative way to pass it if you don't want to use the *config.ini* file.

        api_hash (``str``, *optional*):
            The *api_hash* part of your Telegram API Key, as string. E.g.: "0123456789abcdef0123456789abcdef".
            This is an alternative way to pass it if you don't want to use the *config.ini* file.

        app_version (``str``, *optional*):
            Application version. Defaults to "Pyrogram X.Y.Z"
            This is an alternative way to set it if you don't want to use the *config.ini* file.

        device_model (``str``, *optional*):
            Device model. Defaults to *platform.python_implementation() + " " + platform.python_version()*
            This is an alternative way to set it if you don't want to use the *config.ini* file.

        system_version (``str``, *optional*):
            Operating System version. Defaults to *platform.system() + " " + platform.release()*
            This is an alternative way to set it if you don't want to use the *config.ini* file.

        lang_code (``str``, *optional*):
            Code of the language used on the client, in ISO 639-1 standard. Defaults to "en".
            This is an alternative way to set it if you don't want to use the *config.ini* file.

        ipv6 (``bool``, *optional*):
            Pass True to connect to Telegram using IPv6.
            Defaults to False (IPv4).

        proxy (``dict``, *optional*):
            Your SOCKS5 Proxy settings as dict,
            e.g.: *dict(hostname="11.22.33.44", port=1080, username="user", password="pass")*.
            *username* and *password* can be omitted if your proxy doesn't require authorization.
            This is an alternative way to setup a proxy if you don't want to use the *config.ini* file.

        test_mode (``bool``, *optional*):
            Enable or disable login to the test servers. Defaults to False.
            Only applicable for new sessions and will be ignored in case previously
            created sessions are loaded.

        bot_token (``str``, *optional*):
            Pass your Bot API token to create a bot session, e.g.: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
            Only applicable for new sessions.

        phone_number (``str`` | ``callable``, *optional*):
            Pass your phone number as string (with your Country Code prefix included) to avoid entering it manually.
            Or pass a callback function which accepts no arguments and must return the correct phone number as string
            (e.g., "391234567890").
            Only applicable for new sessions.

        phone_code (``str`` | ``callable``, *optional*):
            Pass the phone code as string (for test numbers only) to avoid entering it manually. Or pass a callback
            function which accepts a single positional argument *(phone_number)* and must return the correct phone code
            as string (e.g., "12345").
            Only applicable for new sessions.

        password (``str``, *optional*):
            Pass your Two-Step Verification password as string (if you have one) to avoid entering it manually.
            Or pass a callback function which accepts a single positional argument *(password_hint)* and must return
            the correct password as string (e.g., "password").
            Only applicable for new sessions.

        recovery_code (``callable``, *optional*):
            Pass a callback function which accepts a single positional argument *(email_pattern)* and must return the
            correct password recovery code as string (e.g., "987654").
            Only applicable for new sessions.

        force_sms (``str``, *optional*):
            Pass True to force Telegram sending the authorization code via SMS.
            Only applicable for new sessions.

        first_name (``str``, *optional*):
            Pass a First Name as string to avoid entering it manually. Or pass a callback function which accepts no
            arguments and must return the correct name as string (e.g., "Dan"). It will be used to automatically create
            a new Telegram account in case the phone number you passed is not registered yet.
            Only applicable for new sessions.

        last_name (``str``, *optional*):
            Same purpose as *first_name*; pass a Last Name to avoid entering it manually. It can
            be an empty string: "". Only applicable for new sessions.

        workers (``int``, *optional*):
            Number of maximum concurrent workers for handling incoming updates. Defaults to 4.

        workdir (``str``, *optional*):
            Define a custom working directory. The working directory is the location in your filesystem
            where Pyrogram will store your session files. Defaults to "." (current directory).

        config_file (``str``, *optional*):
            Path of the configuration file. Defaults to ./config.ini

        plugins (``dict``, *optional*):
            Your Smart Plugins settings as dict, e.g.: *dict(root="plugins")*.
            This is an alternative way to setup plugins if you don't want to use the *config.ini* file.

        no_updates (``bool``, *optional*):
            Pass True to completely disable incoming updates for the current session.
            When updates are disabled your client can't receive any new message.
            Useful for batch programs that don't need to deal with updates.
            Defaults to False (updates enabled and always received).

        takeout (``bool``, *optional*):
            Pass True to let the client use a takeout session instead of a normal one, implies *no_updates=True*.
            Useful for exporting your Telegram data. Methods invoked inside a takeout session (such as get_history,
            download_media, ...) are less prone to throw FloodWait exceptions.
            Only available for users, bots will ignore this parameter.
            Defaults to False (normal session).
    """

    terms_of_service_displayed = False

    def __init__(
        self,
        session_name: Union[str, Storage],
        api_id: Union[int, str] = None,
        api_hash: str = None,
        app_version: str = None,
        device_model: str = None,
        system_version: str = None,
        lang_code: str = None,
        ipv6: bool = False,
        proxy: dict = None,
        test_mode: bool = False,
        bot_token: str = None,
        phone_number: str = None,
        phone_code: Union[str, callable] = None,
        password: str = None,
        recovery_code: callable = None,
        force_sms: bool = False,
        first_name: str = None,
        last_name: str = None,
        workers: int = BaseClient.WORKERS,
        workdir: str = BaseClient.WORKDIR,
        config_file: str = BaseClient.CONFIG_FILE,
        plugins: dict = None,
        no_updates: bool = None,
        takeout: bool = None
    ):
        super().__init__()

        self.session_name = session_name
        self.api_id = int(api_id) if api_id else None
        self.api_hash = api_hash
        self.app_version = app_version
        self.device_model = device_model
        self.system_version = system_version
        self.lang_code = lang_code
        self.ipv6 = ipv6
        # TODO: Make code consistent, use underscore for private/protected fields
        self._proxy = proxy
        self.test_mode = test_mode
        self.bot_token = bot_token
        self.phone_number = phone_number
        self.phone_code = phone_code
        self.password = password
        self.recovery_code = recovery_code
        self.force_sms = force_sms
        self.first_name = first_name
        self.last_name = last_name
        self.workers = workers
        self.workdir = Path(workdir)
        self.config_file = Path(config_file)
        self.plugins = plugins
        self.no_updates = no_updates
        self.takeout = takeout

        if isinstance(session_name, str):
            if session_name == ":memory:" or len(session_name) >= MemoryStorage.SESSION_STRING_SIZE:
                session_name = re.sub(r"[\n\s]+", "", session_name)
                self.storage = MemoryStorage(session_name)
            else:
                self.storage = FileStorage(session_name, self.workdir)
        elif isinstance(session_name, Storage):
            self.storage = session_name
        else:
            raise ValueError("Unknown storage engine")

        self.dispatcher = Dispatcher(self, workers)

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.stop()

    async def __aenter__(self):
        return await self.start()

    async def __aexit__(self, *args):
        await self.stop()

    @property
    def proxy(self):
        return self._proxy

    @proxy.setter
    def proxy(self, value):
        if value is None:
            self._proxy = None
            return

        if self._proxy is None:
            self._proxy = {}

        self._proxy["enabled"] = bool(value.get("enabled", True))
        self._proxy.update(value)

    async def start(self):
        """Start the Client.

        Raises:
            RPCError: In case of a Telegram RPC error.
            ConnectionError: In case you try to start an already started Client.
        """
        if self.is_started:
            raise ConnectionError("Client has already been started")

        self.load_config()
        await self.load_session()
        self.load_plugins()

        self.session = Session(self, self.storage.dc_id, self.storage.auth_key)

        await self.session.start()
        self.is_started = True

        try:
            if self.storage.user_id is None:
                if self.bot_token is None:
                    self.storage.is_bot = False
                    await self.authorize_user()
                else:
                    self.storage.is_bot = True
                    await self.authorize_bot()

            if not self.storage.is_bot:
                if self.takeout:
                    self.takeout_id = (await self.send(functions.account.InitTakeoutSession())).id
                    log.warning("Takeout session {} initiated".format(self.takeout_id))

                now = time.time()

                if abs(now - self.storage.date) > Client.OFFLINE_SLEEP:
                    await self.get_initial_dialogs()
                    await self.get_contacts()
                else:
                    await self.send(functions.messages.GetPinnedDialogs(folder_id=0))
                    await self.get_initial_dialogs_chunk()
            else:
                await self.send(functions.updates.GetState())
        except Exception as e:
            self.is_started = False
            await self.session.stop()
            raise e

        for _ in range(Client.UPDATES_WORKERS):
            self.updates_worker_tasks.append(
                asyncio.ensure_future(self.updates_worker())
            )

        log.info("Started {} UpdatesWorkerTasks".format(Client.UPDATES_WORKERS))

        for _ in range(Client.DOWNLOAD_WORKERS):
            self.download_worker_tasks.append(
                asyncio.ensure_future(self.download_worker())
            )

        log.info("Started {} DownloadWorkerTasks".format(Client.DOWNLOAD_WORKERS))

        await self.dispatcher.start()
        await Syncer.add(self)

        mimetypes.init()

        return self

    async def stop(self):
        """Stop the Client.

        Raises:
            ConnectionError: In case you try to stop an already stopped Client.
        """
        if not self.is_started:
            raise ConnectionError("Client is already stopped")

        if self.takeout_id:
            await self.send(functions.account.FinishTakeoutSession())
            log.warning("Takeout session {} finished".format(self.takeout_id))

        await Syncer.remove(self)
        await self.dispatcher.stop()

        for _ in range(Client.DOWNLOAD_WORKERS):
            self.download_queue.put_nowait(None)

        for task in self.download_worker_tasks:
            await task

        self.download_worker_tasks.clear()

        log.info("Stopped {} DownloadWorkerTasks".format(Client.DOWNLOAD_WORKERS))

        for _ in range(Client.UPDATES_WORKERS):
            self.updates_queue.put_nowait(None)

        for task in self.updates_worker_tasks:
            await task

        self.updates_worker_tasks.clear()

        log.info("Stopped {} UpdatesWorkerTasks".format(Client.UPDATES_WORKERS))

        for media_session in self.media_sessions.values():
            await media_session.stop()

        self.media_sessions.clear()

        self.is_started = False
        await self.session.stop()

        return self

    async def restart(self):
        """Restart the Client.

        Raises:
            ConnectionError: In case you try to restart a stopped Client.
        """
        await self.stop()
        await self.start()

    async def idle(self, stop_signals: tuple = (SIGINT, SIGTERM, SIGABRT)):
        """Block the main script execution until a signal (e.g.: from CTRL+C) is received.
        Once the signal is received, the client will automatically stop and the main script will continue its execution.

        This is used after starting one or more clients and is useful for event-driven applications only, that are,
        applications which react upon incoming Telegram updates through handlers, rather than executing a set of methods
        sequentially.

        The way Pyrogram works, will keep your handlers in a pool of workers, which are executed concurrently outside
        the main script; calling idle() will ensure the client(s) will be kept alive by not letting the main script to
        end, until you decide to quit.

        Parameters:
            stop_signals (``tuple``, *optional*):
                Iterable containing signals the signal handler will listen to.
                Defaults to (SIGINT, SIGTERM, SIGABRT).
        """

        # TODO: Maybe make this method static and don't automatically stop

        def signal_handler(*args):
            log.info("Stop signal received ({}). Exiting...".format(args[0]))
            self.is_idle = False

        for s in stop_signals:
            signal(s, signal_handler)

        self.is_idle = True

        while self.is_idle:
            await asyncio.sleep(1)

        await self.stop()

    def run(self, coroutine=None):
        """Start the Client and automatically idle the main script.

        This is a convenience method that literally just calls :meth:`~Client.start` and :meth:`~Client.idle`. It makes
        running a client less verbose, but is not suitable in case you want to run more than one client in a single main
        script, since :meth:`~Client.idle` will block.

        Args:
            coroutine: (``Coroutine``, *optional*):
                Pass a coroutine to run it until is complete.

        Raises:
            RPCError: In case of a Telegram RPC error.
        """
        run = asyncio.get_event_loop().run_until_complete

        run(self.start())

        run(
            coroutine if inspect.iscoroutine(coroutine)
            else coroutine() if coroutine
            else self.idle()
        )

        if self.is_started:
            run(self.stop())

        return coroutine

    def add_handler(self, handler: Handler, group: int = 0):
        """Register an update handler.

        You can register multiple handlers, but at most one handler within a group
        will be used for a single update. To handle the same update more than once, register
        your handler using a different group id (lower group id == higher priority).

        Parameters:
            handler (``Handler``):
                The handler to be registered.

            group (``int``, *optional*):
                The group identifier, defaults to 0.

        Returns:
            ``tuple``: A tuple consisting of (handler, group).
        """
        if isinstance(handler, DisconnectHandler):
            self.disconnect_handler = handler.callback
        else:
            self.dispatcher.add_handler(handler, group)

        return handler, group

    def remove_handler(self, handler: Handler, group: int = 0):
        """Remove a previously-registered update handler.

        Make sure to provide the right group that the handler was added in. You can use
        the return value of the :meth:`~Client.add_handler` method, a tuple of (handler, group), and
        pass it directly.

        Parameters:
            handler (``Handler``):
                The handler to be removed.

            group (``int``, *optional*):
                The group identifier, defaults to 0.
        """
        if isinstance(handler, DisconnectHandler):
            self.disconnect_handler = None
        else:
            self.dispatcher.remove_handler(handler, group)

    def stop_transmission(self):
        """Stop downloading or uploading a file.
        Must be called inside a progress callback function.
        """
        raise Client.StopTransmission

    async def authorize_bot(self):
        try:
            r = await self.send(
                functions.auth.ImportBotAuthorization(
                    flags=0,
                    api_id=self.api_id,
                    api_hash=self.api_hash,
                    bot_auth_token=self.bot_token
                )
            )
        except UserMigrate as e:
            await self.session.stop()

            self.storage.dc_id = e.x
            self.storage.auth_key = await Auth(self, self.storage.dc_id).create()
            self.session = Session(self, self.storage.dc_id, self.storage.auth_key)

            await self.session.start()
            await self.authorize_bot()
        else:
            self.storage.user_id = r.user.id

            print("Logged in successfully as @{}".format(r.user.username))

    async def authorize_user(self):
        phone_number_invalid_raises = self.phone_number is not None
        phone_code_invalid_raises = self.phone_code is not None
        password_invalid_raises = self.password is not None
        first_name_invalid_raises = self.first_name is not None

        async def default_phone_number_callback():
            while True:
                phone_number = await ainput("Enter phone number: ")
                confirm = await ainput("Is \"{}\" correct? (y/n): ".format(phone_number))

                if confirm in ("y", "1"):
                    return phone_number
                elif confirm in ("n", "2"):
                    continue

        while True:
            self.phone_number = (
                await default_phone_number_callback() if self.phone_number is None
                else str(await self.phone_number()) if callable(self.phone_number)
                else str(self.phone_number)
            )

            self.phone_number = self.phone_number.strip("+")

            try:
                r = await self.send(
                    functions.auth.SendCode(
                        phone_number=self.phone_number,
                        api_id=self.api_id,
                        api_hash=self.api_hash,
                        settings=types.CodeSettings()
                    )
                )
            except (PhoneMigrate, NetworkMigrate) as e:
                await self.session.stop()

                self.storage.dc_id = e.x
                self.storage.auth_key = await Auth(self, self.storage.dc_id).create()

                self.session = Session(self, self.storage.dc_id, self.storage.auth_key)

                await self.session.start()
            except (PhoneNumberInvalid, PhoneNumberBanned) as e:
                if phone_number_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE)
                    self.phone_number = None
            except FloodWait as e:
                if phone_number_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE.format(x=e.x))
                    await asyncio.sleep(e.x)
            except Exception as e:
                log.error(e, exc_info=True)
                raise
            else:
                break

        phone_registered = r.phone_registered
        phone_code_hash = r.phone_code_hash
        terms_of_service = r.terms_of_service

        if terms_of_service and not Client.terms_of_service_displayed:
            print("\n" + terms_of_service.text + "\n")
            Client.terms_of_service_displayed = True

        if self.force_sms:
            await self.send(
                functions.auth.ResendCode(
                    phone_number=self.phone_number,
                    phone_code_hash=phone_code_hash
                )
            )

        while True:
            if not phone_registered:
                self.first_name = (
                    await ainput("First name: ") if self.first_name is None
                    else str(await self.first_name()) if callable(self.first_name)
                    else str(self.first_name)
                )

                self.last_name = (
                    await ainput("Last name: ") if self.last_name is None
                    else str(await self.last_name()) if callable(self.last_name)
                    else str(self.last_name)
                )

            self.phone_code = (
                await ainput("Enter phone code: ") if self.phone_code is None
                else str(await self.phone_code(self.phone_number)) if callable(self.phone_code)
                else str(self.phone_code)
            )

            try:
                if phone_registered:
                    try:
                        r = await self.send(
                            functions.auth.SignIn(
                                phone_number=self.phone_number,
                                phone_code_hash=phone_code_hash,
                                phone_code=self.phone_code
                            )
                        )
                    except PhoneNumberUnoccupied:
                        log.warning("Phone number unregistered")
                        phone_registered = False
                        continue
                else:
                    try:
                        r = await self.send(
                            functions.auth.SignUp(
                                phone_number=self.phone_number,
                                phone_code_hash=phone_code_hash,
                                phone_code=self.phone_code,
                                first_name=self.first_name,
                                last_name=self.last_name
                            )
                        )
                    except PhoneNumberOccupied:
                        log.warning("Phone number already registered")
                        phone_registered = True
                        continue
            except (PhoneCodeInvalid, PhoneCodeEmpty, PhoneCodeExpired, PhoneCodeHashEmpty) as e:
                if phone_code_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE)
                    self.phone_code = None
            except FirstnameInvalid as e:
                if first_name_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE)
                    self.first_name = None
            except SessionPasswordNeeded as e:
                print(e.MESSAGE)

                async def default_password_callback(password_hint: str) -> str:
                    print("Hint: {}".format(password_hint))
                    return await ainput("Enter password (empty to recover): ")

                async def default_recovery_callback(email_pattern: str) -> str:
                    print("An e-mail containing the recovery code has been sent to {}".format(email_pattern))
                    return await ainput("Enter password recovery code: ")

                while True:
                    try:
                        r = await self.send(functions.account.GetPassword())

                        self.password = (
                            await default_password_callback(r.hint) if self.password is None
                            else str((await self.password(r.hint)) or "") if callable(self.password)
                            else str(self.password)
                        )

                        if self.password == "":
                            r = await self.send(functions.auth.RequestPasswordRecovery())

                            self.recovery_code = (
                                await default_recovery_callback(r.email_pattern) if self.recovery_code is None
                                else str(await self.recovery_code(r.email_pattern)) if callable(self.recovery_code)
                                else str(self.recovery_code)
                            )

                            r = await self.send(
                                functions.auth.RecoverPassword(
                                    code=self.recovery_code
                                )
                            )
                        else:
                            r = await self.send(
                                functions.auth.CheckPassword(
                                    password=compute_check(r, self.password)
                                )
                            )
                    except (PasswordEmpty, PasswordRecoveryNa, PasswordHashInvalid) as e:
                        if password_invalid_raises:
                            raise
                        else:
                            print(e.MESSAGE)
                            self.password = None
                            self.recovery_code = None
                    except FloodWait as e:
                        if password_invalid_raises:
                            raise
                        else:
                            print(e.MESSAGE.format(x=e.x))
                            await asyncio.sleep(e.x)
                            self.password = None
                            self.recovery_code = None
                    except Exception as e:
                        log.error(e, exc_info=True)
                        raise
                    else:
                        break
                break
            except FloodWait as e:
                if phone_code_invalid_raises or first_name_invalid_raises:
                    raise
                else:
                    print(e.MESSAGE.format(x=e.x))
                    await asyncio.sleep(e.x)
            except Exception as e:
                log.error(e, exc_info=True)
                raise
            else:
                break

        if terms_of_service:
            assert await self.send(
                functions.help.AcceptTermsOfService(
                    id=terms_of_service.id
                )
            )

        self.password = None
        self.storage.user_id = r.user.id

        print("Logged in successfully as {}".format(r.user.first_name))

    def fetch_peers(
        self,
        peers: List[
            Union[
                types.User,
                types.Chat, types.ChatForbidden,
                types.Channel, types.ChannelForbidden
            ]
        ]
    ) -> bool:
        is_min = False
        parsed_peers = []

        for peer in peers:
            username = None
            phone_number = None

            if isinstance(peer, types.User):
                peer_id = peer.id
                access_hash = peer.access_hash

                username = peer.username
                phone_number = peer.phone

                if peer.bot:
                    peer_type = "bot"
                else:
                    peer_type = "user"

                if access_hash is None:
                    is_min = True
                    continue

                if username is not None:
                    username = username.lower()
            elif isinstance(peer, (types.Chat, types.ChatForbidden)):
                peer_id = -peer.id
                access_hash = 0
                peer_type = "group"
            elif isinstance(peer, (types.Channel, types.ChannelForbidden)):
                peer_id = int("-100" + str(peer.id))
                access_hash = peer.access_hash

                username = getattr(peer, "username", None)

                if peer.broadcast:
                    peer_type = "channel"
                else:
                    peer_type = "supergroup"

                if access_hash is None:
                    is_min = True
                    continue

                if username is not None:
                    username = username.lower()
            else:
                continue

            parsed_peers.append((peer_id, access_hash, peer_type, username, phone_number))

        self.storage.update_peers(parsed_peers)

        return is_min

    async def download_worker(self):
        while True:
            packet = await self.download_queue.get()

            if packet is None:
                break

            temp_file_path = ""
            final_file_path = ""

            try:
                data, directory, file_name, done, progress, progress_args, path = packet

                temp_file_path = await self.get_file(
                    media_type=data.media_type,
                    dc_id=data.dc_id,
                    document_id=data.document_id,
                    access_hash=data.access_hash,
                    thumb_size=data.thumb_size,
                    peer_id=data.peer_id,
                    volume_id=data.volume_id,
                    local_id=data.local_id,
                    file_size=data.file_size,
                    is_big=data.is_big,
                    progress=progress,
                    progress_args=progress_args
                )

                if temp_file_path:
                    final_file_path = os.path.abspath(re.sub("\\\\", "/", os.path.join(directory, file_name)))
                    os.makedirs(directory, exist_ok=True)
                    shutil.move(temp_file_path, final_file_path)
            except Exception as e:
                log.error(e, exc_info=True)

                try:
                    os.remove(temp_file_path)
                except OSError:
                    pass
            else:
                # TODO: "" or None for faulty download, which is better?
                # os.path methods return "" in case something does not exist, I prefer this.
                # For now let's keep None
                path[0] = final_file_path or None
            finally:
                done.set()

    async def updates_worker(self):
        while True:
            updates = await self.updates_queue.get()

            if updates is None:
                break

            try:
                if isinstance(updates, (types.Update, types.UpdatesCombined)):
                    is_min = self.fetch_peers(updates.users) or self.fetch_peers(updates.chats)

                    users = {u.id: u for u in updates.users}
                    chats = {c.id: c for c in updates.chats}

                    for update in updates.updates:
                        channel_id = getattr(
                            getattr(
                                getattr(
                                    update, "message", None
                                ), "to_id", None
                            ), "channel_id", None
                        ) or getattr(update, "channel_id", None)

                        pts = getattr(update, "pts", None)
                        pts_count = getattr(update, "pts_count", None)

                        if isinstance(update, types.UpdateChannelTooLong):
                            log.warning(update)

                        if isinstance(update, types.UpdateNewChannelMessage) and is_min:
                            message = update.message

                            if not isinstance(message, types.MessageEmpty):
                                try:
                                    diff = await self.send(
                                        functions.updates.GetChannelDifference(
                                            channel=await self.resolve_peer(int("-100" + str(channel_id))),
                                            filter=types.ChannelMessagesFilter(
                                                ranges=[types.MessageRange(
                                                    min_id=update.message.id,
                                                    max_id=update.message.id
                                                )]
                                            ),
                                            pts=pts - pts_count,
                                            limit=pts
                                        )
                                    )
                                except ChannelPrivate:
                                    pass
                                else:
                                    if not isinstance(diff, types.updates.ChannelDifferenceEmpty):
                                        users.update({u.id: u for u in diff.users})
                                        chats.update({c.id: c for c in diff.chats})

                        self.dispatcher.updates_queue.put_nowait((update, users, chats))
                elif isinstance(updates, (types.UpdateShortMessage, types.UpdateShortChatMessage)):
                    diff = await self.send(
                        functions.updates.GetDifference(
                            pts=updates.pts - updates.pts_count,
                            date=updates.date,
                            qts=-1
                        )
                    )

                    if diff.new_messages:
                        self.dispatcher.updates_queue.put_nowait((
                            types.UpdateNewMessage(
                                message=diff.new_messages[0],
                                pts=updates.pts,
                                pts_count=updates.pts_count
                            ),
                            {u.id: u for u in diff.users},
                            {c.id: c for c in diff.chats}
                        ))
                    else:
                        self.dispatcher.updates_queue.put_nowait((diff.other_updates[0], {}, {}))
                elif isinstance(updates, types.UpdateShort):
                    self.dispatcher.updates_queue.put_nowait((updates.update, {}, {}))
                elif isinstance(updates, types.UpdatesTooLong):
                    log.warning(updates)
            except Exception as e:
                log.error(e, exc_info=True)

    async def send(self,
                   data: TLObject,
                   retries: int = Session.MAX_RETRIES,
                   timeout: float = Session.WAIT_TIMEOUT):
        """Send raw Telegram queries.

        This method makes it possible to manually call every single Telegram API method in a low-level manner.
        Available functions are listed in the :obj:`functions <pyrogram.api.functions>` package and may accept compound
        data types from :obj:`types <pyrogram.api.types>` as well as bare types such as ``int``, ``str``, etc...

        .. note::

            This is a utility method intended to be used **only** when working with raw
            :obj:`functions <pyrogram.api.functions>` (i.e: a Telegram API method you wish to use which is not
            available yet in the Client class as an easy-to-use method).

        Parameters:
            data (``RawFunction``):
                The API Schema function filled with proper arguments.

            retries (``int``):
                Number of retries.

            timeout (``float``):
                Timeout in seconds.

        Returns:
            ``RawType``: The raw type response generated by the query.

        Raises:
            RPCError: In case of a Telegram RPC error.
        """
        if not self.is_started:
            raise ConnectionError("Client has not been started")

        if self.no_updates:
            data = functions.InvokeWithoutUpdates(query=data)

        if self.takeout_id:
            data = functions.InvokeWithTakeout(takeout_id=self.takeout_id, query=data)

        r = await self.session.send(data, retries, timeout)

        self.fetch_peers(getattr(r, "users", []))
        self.fetch_peers(getattr(r, "chats", []))

        return r

    def load_config(self):
        parser = ConfigParser()
        parser.read(str(self.config_file))

        if self.api_id and self.api_hash:
            pass
        else:
            if parser.has_section("pyrogram"):
                self.api_id = parser.getint("pyrogram", "api_id")
                self.api_hash = parser.get("pyrogram", "api_hash")
            else:
                raise AttributeError(
                    "No API Key found. "
                    "More info: https://docs.pyrogram.org/intro/setup#configuration"
                )

        for option in ["app_version", "device_model", "system_version", "lang_code"]:
            if getattr(self, option):
                pass
            else:
                if parser.has_section("pyrogram"):
                    setattr(self, option, parser.get(
                        "pyrogram",
                        option,
                        fallback=getattr(Client, option.upper())
                    ))
                else:
                    setattr(self, option, getattr(Client, option.upper()))

        if self._proxy:
            self._proxy["enabled"] = bool(self._proxy.get("enabled", True))
        else:
            self._proxy = {}

            if parser.has_section("proxy"):
                self._proxy["enabled"] = parser.getboolean("proxy", "enabled", fallback=True)
                self._proxy["hostname"] = parser.get("proxy", "hostname")
                self._proxy["port"] = parser.getint("proxy", "port")
                self._proxy["username"] = parser.get("proxy", "username", fallback=None) or None
                self._proxy["password"] = parser.get("proxy", "password", fallback=None) or None

        if self.plugins:
            self.plugins = {
                "enabled": bool(self.plugins.get("enabled", True)),
                "root": self.plugins.get("root", None),
                "include": self.plugins.get("include", []),
                "exclude": self.plugins.get("exclude", [])
            }
        else:
            try:
                section = parser["plugins"]

                self.plugins = {
                    "enabled": section.getboolean("enabled", True),
                    "root": section.get("root", None),
                    "include": section.get("include", []),
                    "exclude": section.get("exclude", [])
                }

                include = self.plugins["include"]
                exclude = self.plugins["exclude"]

                if include:
                    self.plugins["include"] = include.strip().split("\n")

                if exclude:
                    self.plugins["exclude"] = exclude.strip().split("\n")

            except KeyError:
                self.plugins = None

    async def load_session(self):
        self.storage.open()

        session_empty = any([
            self.storage.test_mode is None,
            self.storage.auth_key is None,
            self.storage.user_id is None,
            self.storage.is_bot is None
        ])

        if session_empty:
            self.storage.dc_id = 1
            self.storage.date = 0

            self.storage.test_mode = self.test_mode
            self.storage.auth_key = await Auth(self, self.storage.dc_id).create()
            self.storage.user_id = None
            self.storage.is_bot = None

    def load_plugins(self):
        if self.plugins:
            plugins = self.plugins.copy()

            for option in ["include", "exclude"]:
                if plugins[option]:
                    plugins[option] = [
                        (i.split()[0], i.split()[1:] or None)
                        for i in self.plugins[option]
                    ]
        else:
            return

        if plugins.get("enabled", False):
            root = plugins["root"]
            include = plugins["include"]
            exclude = plugins["exclude"]

            count = 0

            if not include:
                for path in sorted(Path(root).rglob("*.py")):
                    module_path = '.'.join(path.parent.parts + (path.stem,))
                    module = import_module(module_path)

                    for name in vars(module).keys():
                        # noinspection PyBroadException
                        try:
                            handler, group = getattr(module, name).pyrogram_plugin

                            if isinstance(handler, Handler) and isinstance(group, int):
                                self.add_handler(handler, group)

                                log.info('[{}] [LOAD] {}("{}") in group {} from "{}"'.format(
                                    self.session_name, type(handler).__name__, name, group, module_path))

                                count += 1
                        except Exception:
                            pass
            else:
                for path, handlers in include:
                    module_path = root + "." + path
                    warn_non_existent_functions = True

                    try:
                        module = import_module(module_path)
                    except ImportError:
                        log.warning('[{}] [LOAD] Ignoring non-existent module "{}"'.format(
                            self.session_name, module_path))
                        continue

                    if "__path__" in dir(module):
                        log.warning('[{}] [LOAD] Ignoring namespace "{}"'.format(
                            self.session_name, module_path))
                        continue

                    if handlers is None:
                        handlers = vars(module).keys()
                        warn_non_existent_functions = False

                    for name in handlers:
                        # noinspection PyBroadException
                        try:
                            handler, group = getattr(module, name).pyrogram_plugin

                            if isinstance(handler, Handler) and isinstance(group, int):
                                self.add_handler(handler, group)

                                log.info('[{}] [LOAD] {}("{}") in group {} from "{}"'.format(
                                    self.session_name, type(handler).__name__, name, group, module_path))

                                count += 1
                        except Exception:
                            if warn_non_existent_functions:
                                log.warning('[{}] [LOAD] Ignoring non-existent function "{}" from "{}"'.format(
                                    self.session_name, name, module_path))

            if exclude:
                for path, handlers in exclude:
                    module_path = root + "." + path
                    warn_non_existent_functions = True

                    try:
                        module = import_module(module_path)
                    except ImportError:
                        log.warning('[{}] [UNLOAD] Ignoring non-existent module "{}"'.format(
                            self.session_name, module_path))
                        continue

                    if "__path__" in dir(module):
                        log.warning('[{}] [UNLOAD] Ignoring namespace "{}"'.format(
                            self.session_name, module_path))
                        continue

                    if handlers is None:
                        handlers = vars(module).keys()
                        warn_non_existent_functions = False

                    for name in handlers:
                        # noinspection PyBroadException
                        try:
                            handler, group = getattr(module, name).pyrogram_plugin

                            if isinstance(handler, Handler) and isinstance(group, int):
                                self.remove_handler(handler, group)

                                log.info('[{}] [UNLOAD] {}("{}") from group {} in "{}"'.format(
                                    self.session_name, type(handler).__name__, name, group, module_path))

                                count -= 1
                        except Exception:
                            if warn_non_existent_functions:
                                log.warning('[{}] [UNLOAD] Ignoring non-existent function "{}" from "{}"'.format(
                                    self.session_name, name, module_path))

            if count > 0:
                log.warning('[{}] Successfully loaded {} plugin{} from "{}"'.format(
                    self.session_name, count, "s" if count > 1 else "", root))
            else:
                log.warning('[{}] No plugin loaded from "{}"'.format(
                    self.session_name, root))

    async def get_initial_dialogs_chunk(self, offset_date: int = 0):
        while True:
            try:
                r = await self.send(
                    functions.messages.GetDialogs(
                        offset_date=offset_date,
                        offset_id=0,
                        offset_peer=types.InputPeerEmpty(),
                        limit=self.DIALOGS_AT_ONCE,
                        hash=0,
                        exclude_pinned=True
                    )
                )
            except FloodWait as e:
                log.warning("get_dialogs flood: waiting {} seconds".format(e.x))
                await asyncio.sleep(e.x)
            else:
                log.info("Total peers: {}".format(self.storage.peers_count))
                return r

    async def get_initial_dialogs(self):
        await self.send(functions.messages.GetPinnedDialogs(folder_id=0))

        dialogs = await self.get_initial_dialogs_chunk()
        offset_date = utils.get_offset_date(dialogs)

        while len(dialogs.dialogs) == self.DIALOGS_AT_ONCE:
            dialogs = await self.get_initial_dialogs_chunk(offset_date)
            offset_date = utils.get_offset_date(dialogs)

        await self.get_initial_dialogs_chunk()

    async def resolve_peer(self,
                           peer_id: Union[int, str]):
        """Get the InputPeer of a known peer id.
        Useful whenever an InputPeer type is required.

        .. note::

            This is a utility method intended to be used **only** when working with raw
            :obj:`functions <pyrogram.api.functions>` (i.e: a Telegram API method you wish to use which is not
            available yet in the Client class as an easy-to-use method).

        Parameters:
            peer_id (``int`` | ``str``):
                The peer id you want to extract the InputPeer from.
                Can be a direct id (int), a username (str) or a phone number (str).

        Returns:
            ``InputPeer``: On success, the resolved peer id is returned in form of an InputPeer object.

        Raises:
            RPCError: In case of a Telegram RPC error.
            KeyError: In case the peer doesn't exist in the internal database.
        """
        try:
            return self.storage.get_peer_by_id(peer_id)
        except KeyError:
            if type(peer_id) is str:
                if peer_id in ("self", "me"):
                    return types.InputPeerSelf()

                peer_id = re.sub(r"[@+\s]", "", peer_id.lower())

                try:
                    int(peer_id)
                except ValueError:
                    try:
                        return self.storage.get_peer_by_username(peer_id)
                    except KeyError:
                        await self.send(functions.contacts.ResolveUsername(username=peer_id
                                                                           )
                                        )

                        return self.storage.get_peer_by_username(peer_id)
                else:
                    try:
                        return self.storage.get_peer_by_phone_number(peer_id)
                    except KeyError:
                        raise PeerIdInvalid

            if peer_id > 0:
                self.fetch_peers(
                    await self.send(
                        functions.users.GetUsers(
                            id=[types.InputUser(
                                user_id=peer_id,
                                access_hash=0
                            )]
                        )
                    )
                )
            else:
                if str(peer_id).startswith("-100"):
                    await self.send(
                        functions.channels.GetChannels(
                            id=[types.InputChannel(
                                channel_id=int(str(peer_id)[4:]),
                                access_hash=0
                            )]
                        )
                    )
                else:
                    await self.send(
                        functions.messages.GetChats(
                            id=[-peer_id]
                        )
                    )

            try:
                return self.storage.get_peer_by_id(peer_id)
            except KeyError:
                raise PeerIdInvalid

    async def save_file(self,
                        path: str,
                        file_id: int = None,
                        file_part: int = 0,
                        progress: callable = None,
                        progress_args: tuple = ()
                        ):
        """Upload a file onto Telegram servers, without actually sending the message to anyone.
        Useful whenever an InputFile type is required.

        .. note::

            This is a utility method intended to be used **only** when working with raw
            :obj:`functions <pyrogram.api.functions>` (i.e: a Telegram API method you wish to use which is not
            available yet in the Client class as an easy-to-use method).

        Parameters:
            path (``str``):
                The path of the file you want to upload that exists on your local machine.

            file_id (``int``, *optional*):
                In case a file part expired, pass the file_id and the file_part to retry uploading that specific chunk.

            file_part (``int``, *optional*):
                In case a file part expired, pass the file_id and the file_part to retry uploading that specific chunk.

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
            ``InputFile``: On success, the uploaded file is returned in form of an InputFile object.

        Raises:
            RPCError: In case of a Telegram RPC error.
        """

        async def worker(session):
            while True:
                data = await queue.get()

                if data is None:
                    return

                try:
                    await asyncio.ensure_future(session.send(data))
                except Exception as e:
                    log.error(e)

        part_size = 512 * 1024
        file_size = os.path.getsize(path)

        if file_size == 0:
            raise ValueError("File size equals to 0 B")

        if file_size > 1500 * 1024 * 1024:
            raise ValueError("Telegram doesn't support uploading files bigger than 1500 MiB")

        file_total_parts = int(math.ceil(file_size / part_size))
        is_big = file_size > 10 * 1024 * 1024
        pool_size = 3 if is_big else 1
        workers_count = 4 if is_big else 1
        is_missing_part = file_id is not None
        file_id = file_id or self.rnd_id()
        md5_sum = md5() if not is_big and not is_missing_part else None
        pool = [Session(self, self.storage.dc_id, self.storage.auth_key, is_media=True) for _ in range(pool_size)]
        workers = [asyncio.ensure_future(worker(session)) for session in pool for _ in range(workers_count)]
        queue = asyncio.Queue(16)

        try:
            for session in pool:
                await session.start()

            with open(path, "rb") as f:
                f.seek(part_size * file_part)

                while True:
                    chunk = f.read(part_size)

                    if not chunk:
                        if not is_big:
                            md5_sum = "".join([hex(i)[2:].zfill(2) for i in md5_sum.digest()])
                        break

                    if is_big:
                        rpc = functions.upload.SaveBigFilePart(
                            file_id=file_id,
                            file_part=file_part,
                            file_total_parts=file_total_parts,
                            bytes=chunk
                        )
                    else:
                        rpc = functions.upload.SaveFilePart(
                            file_id=file_id,
                            file_part=file_part,
                            bytes=chunk
                        )

                    await queue.put(rpc)

                    if is_missing_part:
                        return

                    if not is_big:
                        md5_sum.update(chunk)

                    file_part += 1

                    if progress:
                        await progress(self, min(file_part * part_size, file_size), file_size, *progress_args)
        except Client.StopTransmission:
            raise
        except Exception as e:
            log.error(e, exc_info=True)
        else:
            if is_big:
                return types.InputFileBig(
                    id=file_id,
                    parts=file_total_parts,
                    name=os.path.basename(path),

                )
            else:
                return types.InputFile(
                    id=file_id,
                    parts=file_total_parts,
                    name=os.path.basename(path),
                    md5_checksum=md5_sum
                )
        finally:
            for _ in workers:
                await queue.put(None)

            await asyncio.gather(*workers)

            for session in pool:
                await session.stop()

    async def get_file(self, media_type: int,
                       dc_id: int,
                       document_id: int,
                       access_hash: int,
                       thumb_size: str,
                       peer_id: int,
                       volume_id: int,
                       local_id: int,
                       file_size: int,

                       is_big: bool,
                       progress: callable,
                       progress_args: tuple = ()) -> str:
        async with self.media_sessions_lock:
            session = self.media_sessions.get(dc_id, None)

            if session is None:
                if dc_id != self.storage.dc_id:
                    exported_auth = await self.send(
                        functions.auth.ExportAuthorization(
                            dc_id=dc_id
                        )
                    )

                    session = Session(
                        self,
                        dc_id,
                        await Auth(self, dc_id).create(), is_media=True)

                    await session.start()

                    self.media_sessions[dc_id] = session

                    await session.send(
                        functions.auth.ImportAuthorization(
                            id=exported_auth.id,
                            bytes=exported_auth.bytes
                        )
                    )
                else:
                    session = Session(self, dc_id, self.storage.auth_key, is_media=True)

                    await session.start()

                    self.media_sessions[dc_id] = session

        if media_type == 1:
            location = types.InputPeerPhotoFileLocation(
                peer=self.resolve_peer(peer_id),
                volume_id=volume_id,
                local_id=local_id,
                big=is_big or None
            )
        elif media_type in (0, 2):
            location = types.InputPhotoFileLocation(
                id=document_id,
                access_hash=access_hash,
                file_reference=b"",
                thumb_size=thumb_size
            )
        elif media_type == 14:
            location = types.InputDocumentFileLocation(
                id=document_id,
                access_hash=access_hash,
                file_reference=b"",
                thumb_size=thumb_size
            )
        else:
            location = types.InputDocumentFileLocation(
                id=document_id,
                access_hash=access_hash,
                file_reference=b"",
                thumb_size=""
            )

        limit = 1024 * 1024
        offset = 0
        file_name = ""

        try:
            r = await session.send(
                functions.upload.GetFile(
                    location=location,
                    offset=offset,
                    limit=limit
                )
            )

            if isinstance(r, types.upload.File):
                with tempfile.NamedTemporaryFile("wb", delete=False) as f:
                    file_name = f.name

                    while True:
                        chunk = r.bytes

                        if not chunk:
                            break

                        f.write(chunk)

                        offset += limit

                        if progress:
                            await progress(
                                self,
                                min(offset, file_size)
                                if file_size != 0
                                else offset,
                                file_size,
                                *progress_args
                            )

                        r = await session.send(
                            functions.upload.GetFile(
                                location=location,
                                offset=offset,
                                limit=limit
                            )
                        )

            elif isinstance(r, types.upload.FileCdnRedirect):
                async with self.media_sessions_lock:
                    cdn_session = self.media_sessions.get(r.dc_id, None)

                    if cdn_session is None:
                        cdn_session = Session(
                            self,
                            r.dc_id,
                            await Auth(self, r.dc_id).create(), is_media=True, is_cdn=True)

                        await cdn_session.start()

                        self.media_sessions[r.dc_id] = cdn_session

                try:
                    with tempfile.NamedTemporaryFile("wb", delete=False) as f:
                        file_name = f.name

                        while True:
                            r2 = await cdn_session.send(
                                functions.upload.GetCdnFile(
                                    file_token=r.file_token,
                                    offset=offset,
                                    limit=limit
                                )
                            )

                            if isinstance(r2, types.upload.CdnFileReuploadNeeded):
                                try:
                                    await session.send(
                                        functions.upload.ReuploadCdnFile(
                                            file_token=r.file_token,
                                            request_token=r2.request_token
                                        )
                                    )
                                except VolumeLocNotFound:
                                    break
                                else:
                                    continue

                            chunk = r2.bytes

                            # https://core.telegram.org/cdn#decrypting-files
                            decrypted_chunk = AES.ctr256_decrypt(
                                chunk,
                                r.encryption_key,
                                bytearray(
                                    r.encryption_iv[:-4]
                                    + (offset // 16).to_bytes(4, "big")
                                )
                            )

                            hashes = await session.send(
                                functions.upload.GetCdnFileHashes(
                                    file_token=r.file_token,
                                    offset=offset
                                )
                            )

                            # https://core.telegram.org/cdn#verifying-files
                            for i, h in enumerate(hashes):
                                cdn_chunk = decrypted_chunk[h.limit * i: h.limit * (i + 1)]
                                assert h.hash == sha256(cdn_chunk).digest(), "Invalid CDN hash part {}".format(i)

                            f.write(decrypted_chunk)

                            offset += limit

                            if progress:
                                await progress(
                                    self,
                                    min(offset, file_size)
                                    if file_size != 0
                                    else offset,
                                    file_size,
                                    *progress_args
                                )

                            if len(chunk) < limit:
                                break
                except Exception as e:
                    raise e
        except Exception as e:
            if not isinstance(e, Client.StopTransmission):
                log.error(e, exc_info=True)

            try:
                os.remove(file_name)
            except OSError:
                pass

            return ""
        else:
            return file_name

    def guess_mime_type(self, filename: str):
        extension = os.path.splitext(filename)[1]
        return self.extensions_to_mime_types.get(extension)

    def guess_extension(self, mime_type: str):
        extensions = self.mime_types_to_extensions.get(mime_type)

        if extensions:
            return extensions.split(" ")[0]

    def export_session_string(self):
        """Export the current session as serialized string.

        Returns:
            ``str``: The session serialized into a printable, url-safe string.
        """
        return self.storage.export_session_string()
