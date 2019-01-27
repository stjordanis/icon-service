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
from shutil import copytree
from typing import TYPE_CHECKING

from iconcommons.logger import Logger

from .icon_score_deploy_storage import IconScoreDeployInfo, DeployState
from ..base.address import Address
from ..icon_constant import BUILTIN_SCORE_ADDRESS_MAPPER, ZERO_TX_HASH, ICON_DEPLOY_LOG_TAG
from ..iconscore.icon_score_context_util import IconScoreContextUtil

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class IconBuiltinScoreLoader(object):
    """Before activating icon_service_engine, deploy builtin scores which has never been deployed.
    """

    @staticmethod
    def _pre_builtin_score_root_path():
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        return os.path.join(root_path, 'builtin_scores')

    def __init__(self):
        super().__init__()

    def load_builtin_scores(self, context: 'IconScoreContext', builtin_score_owner_str: str):
        score_deploy_storage: 'IconScoreDeployStorage' =\
            context.icon_score_deploy_engine.icon_deploy_storage

        builtin_score_owner = Address.from_string(builtin_score_owner_str)
        for score_name, value in BUILTIN_SCORE_ADDRESS_MAPPER.items():
            score_address = Address.from_string(value)

            # If builtin score has been already deployed, exit.
            if not score_deploy_storage.is_score_active(context, score_address):
                self._load_builtin_score(context, score_name, score_address, builtin_score_owner)

    @staticmethod
    def _load_builtin_score(context: 'IconScoreContext',
                            score_name: str,
                            score_address: 'Address',
                            builtin_score_owner: 'Address'):
        score_deploy_storage: 'IconScoreDeployStorage' = \
            context.icon_score_deploy_engine.icon_deploy_storage

        # score_path is the path that contains governance SCORE files in iconservice package.
        score_source_path_in_package: str = os.path.join(
            IconBuiltinScoreLoader._pre_builtin_score_root_path(), score_name)

        # Save deploy_info for a builtin score to score_deploy_storage.
        deploy_info = IconScoreDeployInfo(
            score_address=score_address,
            deploy_state=DeployState.ACTIVE,
            owner=builtin_score_owner,
            current_tx_hash=ZERO_TX_HASH,
            next_tx_hash=ZERO_TX_HASH)

        tx_hash: bytes = deploy_info.current_tx_hash

        # score_path is score_root_path/score_address/next_tx_hash/ directory.
        score_root_path = IconScoreContextUtil.get_score_root_path(context)
        score_deploy_path: str = os.path.join(
            score_root_path,
            score_address.to_bytes().hex(),
            f'0x{tx_hash.hex()}')

        # Make a directory for a builtin score with a given score_address.
        os.makedirs(score_deploy_path, exist_ok=True)

        try:
            # Copy builtin score source files from iconservice package to score_path
            copytree(score_source_path_in_package, score_deploy_path)
        except FileExistsError:
            pass

        try:
            # Import score class from deployed builtin score sources
            score_info: 'IconScoreInfo' =\
                context.icon_score_mapper.load_score_info(score_address, tx_hash)

            # Create a score instance from the imported score class.
            score = score_info.create_score()

            # Call on_install() to initialize the score database of the builtin score.
            score.on_install()

            score_deploy_storage.put_deploy_info(context, deploy_info)
        except BaseException as e:
            Logger.exception(
                f'Failed to deploy a builtin score: {score_address}\n'
                f'{str(e)}',
                ICON_DEPLOY_LOG_TAG)
            raise e
