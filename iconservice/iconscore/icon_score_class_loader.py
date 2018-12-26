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

import importlib.util
import json
import sys
from os import path

from typing import TYPE_CHECKING

from .score_package_validator import ScorePackageValidator

if TYPE_CHECKING:
    from ..base.address import Address


class IconScoreClassLoader(object):
    """IconScoreBase subclass Loader

    """

    _PACKAGE_JSON_FILE = 'package.json'
    _MAIN_SCORE = 'main_score'
    _MAIN_FILE = 'main_file'

    def __init__(self, score_root_path: str):
        self._score_root_path = score_root_path
        if score_root_path not in sys.path:
            sys.path.append(score_root_path)

    @property
    def score_root_path(self) -> str:
        return self._score_root_path

    @staticmethod
    def _load_package_json(score_path: str) -> dict:
        """Loads package.json in SCORE

        :param score_path:
        :return:
        """
        pkg_json_path = path.join(score_path, IconScoreClassLoader._PACKAGE_JSON_FILE)
        with open(pkg_json_path, 'r') as f:
            return json.load(f)

    def make_score_path(self, score_address: 'Address', tx_hash: bytes) -> str:
        return path.join(self._score_root_path, score_address.to_bytes().hex(), f'0x{tx_hash.hex()}')

    def try_score_package_validate(self, import_whitelist: dict, score_path: str):
        pkg_root_import: str = self._convert_path_to_package_name(score_path)
        ScorePackageValidator().execute(import_whitelist, score_path, pkg_root_import)

    def run(self, score_path: str) -> type:
        """Load a IconScoreBase subclass and return it

        :param score_path:
        :return: subclass derived from IconScoreBase
        """

        score_package_info: dict = self._load_package_json(score_path)
        package_name: str = self._convert_path_to_package_name(score_path)

        # in order for the new module to be noticed by the import system
        importlib.invalidate_caches()
        module = importlib.import_module(f".{score_package_info[self._MAIN_FILE]}", package_name)

        return getattr(module, score_package_info[self._MAIN_SCORE])

    def _convert_path_to_package_name(self, score_path: str) -> str:
        """
        score_root_path: .../.score

        :param score_path: ex) .../.score/address/tx_hash
        :return: address.tx_hash
        """

        text = score_path[len(self.score_root_path):].strip('/')
        return '.'.join(text.split('/'))
