# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from shutil import rmtree
from threading import Lock
from typing import TYPE_CHECKING, Optional

from iconcommons import Logger
from iconservice.builtin_scores.governance.governance import Governance
from .icon_score_mapper_object import IconScoreInfo, IconScoreMapperObject
from ..base.address import Address, GOVERNANCE_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, ServerErrorException
from ..database.db import IconScoreDatabase
from ..database.factory import ContextDatabaseFactory
from ..deploy.icon_score_deploy_engine import IconScoreDeployStorage
from ..icon_constant import DEFAULT_BYTE_SIZE

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from .icon_score_class_loader import IconScoreClassLoader


class IconScoreMapper(object):
    """Icon score information mapping table

    This instance should be used as a singletone

    key: icon_score_address
    value: IconScoreInfo
    """

    icon_score_class_loader: 'IconScoreClassLoader' = None
    deploy_storage: 'IconScoreDeployStorage' = None

    def __init__(self, is_lock: bool = False, is_new: bool = False) -> None:
        """Constructor
        """
        self._score_mapper = IconScoreMapperObject()
        self._lock = Lock()
        self._is_lock = is_lock
        # Is this a icon_score_new_mapper?
        self._is_new = is_new

    def __contains__(self, address: 'Address'):
        if self._is_lock:
            with self._lock:
                return address in self._score_mapper
        else:
            return address in self._score_mapper

    def __setitem__(self, key: 'Address', value: 'IconScoreInfo'):
        if self._is_lock:
            with self._lock:
                self._score_mapper[key] = value
        else:
            self._score_mapper[key] = value

    def get(self, key: 'Address') -> 'IconScoreInfo':
        if self._is_lock:
            with self._lock:
                return self._score_mapper.get(key)
        else:
            return self._score_mapper.get(key)

    def update(self, mapper: 'IconScoreMapper'):
        if self._is_lock:
            with self._lock:
                self._score_mapper.update(mapper._score_mapper)
        else:
            self._score_mapper.update(mapper._score_mapper)

    def close(self):
        for addr, info in self._score_mapper.items():
            info.icon_score.db.close()

    @property
    def score_root_path(self) -> str:
        return self.icon_score_class_loader.score_root_path

    def try_score_package_validate(self, address: 'Address', tx_hash: bytes):
        score_path = self.icon_score_class_loader.make_score_path(address, tx_hash)
        whitelist_table = self._get_score_package_validator_table()
        self.icon_score_class_loader.try_score_package_validate(whitelist_table, score_path)

    def _get_score_package_validator_table(self) -> dict:
        governance_info: 'IconScoreInfo' = self.get(GOVERNANCE_SCORE_ADDRESS)

        if governance_info:
            governance: 'Governance' = governance_info.icon_score
            try:
                return governance.import_white_list_cache
            except AttributeError:
                pass

        return {"iconservice": ['*']}

    def load_score_info(self, address: 'Address', tx_hash: bytes) -> Optional['IconScoreInfo']:
        """Load a deployed score package from the path indicated by address and tx_hash

        :param address:
        :param tx_hash:
        """
        score_info: 'IconScoreInfo' = self.get(address)
        score_class: type = self._load_score_class(address, tx_hash)

        if score_info is None:
            context_db = ContextDatabaseFactory.create_by_address(address)
            score_db = IconScoreDatabase(address, context_db)
        else:
            score_db: 'IconScoreDatabase' = score_info.score_db

        # Cache a new IconScoreInfo instance
        score_info = IconScoreInfo(score_class, score_db, tx_hash)
        self[address] = score_info

        return score_info

    def _load_score_class(self, address: 'Address', tx_hash: bytes) -> type:
        """Load IconScoreBase subclass from IconScore python package

        :param address: icon_score_address
        :return: IconScoreBase subclass (class object)
        """
        score_path: str = self.icon_score_class_loader.make_score_path(address, tx_hash)
        score_class: type = self.icon_score_class_loader.run(score_path)
        if score_class is None:
            raise InvalidParamsException(
                f'SCORE load failure: address({address}) txHash({tx_hash.hex()})')

        return score_class

    def clear_garbage_score(self):
        if self.icon_score_class_loader is None:
            return

        score_root_path = self.icon_score_class_loader.score_root_path
        try:
            dir_list = os.listdir(score_root_path)
        except:
            return

        for dir_name in dir_list:
            try:
                address = Address.from_bytes(bytes.fromhex(dir_name))
            except:
                continue
            deploy_info = self.deploy_storage.get_deploy_info(None, address)
            if deploy_info is None:
                self._remove_score_dir(address)
                continue
            else:
                try:
                    sub_dir_list = os.listdir(os.path.join(score_root_path, bytes.hex(address.to_bytes())))
                except:
                    continue
                for sub_dir_name in sub_dir_list:
                    try:
                        tx_hash = bytes.fromhex(sub_dir_name[2:])
                    except:
                        continue

                    if tx_hash == bytes(DEFAULT_BYTE_SIZE):
                        continue
                    if tx_hash == deploy_info.current_tx_hash:
                        continue
                    elif tx_hash == deploy_info.next_tx_hash:
                        continue
                    else:
                        self._remove_score_dir(address, sub_dir_name)

    @classmethod
    def _remove_score_dir(cls, address: 'Address', converted_tx_hash: Optional[str] = None):
        if cls.icon_score_class_loader is None:
            return
        score_root_path = cls.icon_score_class_loader.score_root_path

        if converted_tx_hash is None:
            target_path = os.path.join(score_root_path, bytes.hex(address.to_bytes()))
        else:
            target_path = os.path.join(score_root_path, bytes.hex(address.to_bytes()), converted_tx_hash)

        try:
            rmtree(target_path)
        except Exception as e:
            Logger.warning(e)
