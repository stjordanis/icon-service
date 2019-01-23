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
from typing import TYPE_CHECKING

from ..base.address import Address
from ..icon_constant import BUILTIN_SCORE_ADDRESS_MAPPER
from .icon_score_deploy_storage import IconScoreDeployInfo, DeployState

if TYPE_CHECKING:
    from .icon_score_deploy_engine import IconScoreDeployEngine
    from ..iconscore.icon_score_context import IconScoreContext


class IconBuiltinScoreLoader(object):
    """Its roles:
    - Save IconScoreDeployInfos of builtin scores to DB.
    -

    """

    @staticmethod
    def _pre_builtin_score_root_path():
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        return os.path.join(root_path, 'builtin_scores')

    def __init__(self,
                 deploy_engine: 'IconScoreDeployEngine') -> None:
        """Constructor
        """

        self._deploy_engine = deploy_engine

    def load_builtin_scores(self, context: 'IconScoreContext', builtin_score_owner_str: str):
        builtin_score_owner = Address.from_string(builtin_score_owner_str)
        for key, value in BUILTIN_SCORE_ADDRESS_MAPPER.items():
            address = Address.from_string(value)
            self._load_builtin_score(context, key, address, builtin_score_owner)

    def _load_builtin_score(self, context: 'IconScoreContext',
                            score_name: str,
                            score_address: 'Address',
                            builtin_score_owner: 'Address'):
        score_deploy_storage: 'IconScoreDeployStorage' = self._deploy_engine.icon_deploy_storage

        # If builtin score has been already deployed, skip the process below.
        if score_deploy_storage.is_score_active(context, score_address):
            return

        # score_path is the path that contains governance SCORE files in iconservice package.
        score_path = os.path.join(IconBuiltinScoreLoader._pre_builtin_score_root_path(), score_name)

        # Save deploy_info for a builtin score to score_deploy_storage.
        deploy_info = IconScoreDeployInfo(score_address, DeployState.ACTIVE, builtin_score_owner, None, None)
        score_deploy_storage.put_deploy_info(context, deploy_info)

        self._deploy_engine.deploy_for_builtin(context, score_address, score_path)
