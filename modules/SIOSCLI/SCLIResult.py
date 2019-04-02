import re
import logging


class SCLIResultGeneral(object):
    def __init__(self, result: dict):
        self.status = result['status']
        self.result = result['result']
        self.command = result['command']
        self.logger = logging.getLogger('SCLIResult')

        # CUSTOM REWORK FOR FALSE-GOOD and FALSE-BAD RESULTS
        if self.command == 'unmap_volume_from_sdc':
            # In some cases you may try to unmap a non-mapped volume
            #  We don't need to rise any exception in this case
            if self.status is False:
                if 'The volume is not mapped to SDC' in result['result']:
                    self.status = True

    def to_list(self):
        #  If no other function overwrites this method -> unsupported for an object
        raise Exception

    def to_dict(self):
        #  If no other function overwrites this method -> unsupported for an object
        raise Exception

    def get_id(self):
        #  If no other function overwrites this method -> unsupported for an object
        #  Returns:
        #  snapshot_volume: ID of a new created snapshot
        #  map_volume_to_sdc: ID of a mapped volume
        raise Exception


class SCLIResultQueryProperties(SCLIResultGeneral):
    def __init__(self, result: dict):
        SCLIResultGeneral.__init__(self, result)

    def to_list(self):
        self.logger.debug('Starting to_list validation, result = "' + self.result + '"')
        if self.status is False:
            raise Exception  # TODO: add SCLIResult like "SCLIResult func cannot be used due to a faulty answer"

        # IDENTIFYING WHICH OBJECT TYPE WAS REQUESTED:
        result_lines = str(self.result).splitlines()
        first_line = result_lines[0]
        regex = r'\s*(\w*)\s*'
        line_regex = re.compile(regex)
        match = line_regex.match(first_line)
        if match:
            requested_object_type = match.group(1)
        else:
            return None
        if requested_object_type == 'No':
            self.logger.warning('Requested properties list is empty due to no requested objects were found')
            return []

        # MAKING A LIST for requested_object_type:
        properties = {}
        final_list = []
        regex = r'\s*(\w*)\s*(.*)'
        line_regex = re.compile(regex)
        for each_line in result_lines:
            if each_line.replace(' ', '').startswith(requested_object_type):
                # need to start a new dict
                if len(properties) > 0:
                    final_list.append(properties)
                    properties = {}
            else:
                match = line_regex.match(each_line)
                if match:
                    if len(match.group(1)) > 0 and len(match.group(2)) > 0:
                        properties.update({match.group(1): match.group(2)})
        final_list.append(properties)
        return final_list

    def to_dict(self):
        if self.status is False:
            raise Exception  # TODO: add SCLIResult like "SCLIResult func cannot be used due to a faulty answer"

        # IDENTIFYING WHICH OBJECT TYPE WAS REQUESTED:
        result_lines = str(self.result).splitlines()
        first_line = result_lines[0]
        regex = r'\s*(\w*)\s*'
        line_regex = re.compile(regex)
        match = line_regex.match(first_line)
        if match:
            requested_object_type = match.group(1)
        else:
            return None
        if requested_object_type == 'No':
            self.logger.warning('Requested properties list is empty due to no requested objects were found')
            return []

        # MAKING A DICT for requested_object_type:
        final_dict = {}
        current_node_id = None
        regex = r'\s*(\w*)\s*(.*)'
        line_regex = re.compile(regex)
        for each_line in result_lines:
            if each_line.replace(' ', '').startswith(requested_object_type):
                current_node_id = each_line.replace(requested_object_type+" ", '').replace(':', '').replace(' ', '')
                final_dict.update({current_node_id: {}})
            if current_node_id is not None:
                match = line_regex.match(each_line)
                if match:
                    final_dict[current_node_id].update({match.group(1): match.group(2)})
        return final_dict


class SCLIResultQueryVtree(SCLIResultGeneral):
    def __init__(self, result: dict):
        SCLIResultGeneral.__init__(self, result)

    def to_list(self):
        self.logger.debug('Starting to_list validation, result = "' + self.result + '"')
        if self.status is False:
            raise Exception  # TODO: add SCLIResult like "SCLIResult func cannot be used due to a faulty answer"
        result_by_nodes = str(self.result).split('>>')
        vtree_info_raw = result_by_nodes.pop(0)
        volumes_info = []

        def make_volume_info_dict(each_volume_func):
            volume_info_dict = {
                'type': None,
                'ID': None,
                'name': None,
                'size_in_gb': None,  # check for variants
                'creation_time': None,
                'num_of_direct_snaps': None,
                'reads': None,
                'writes': None,
                'mappings': None,
                'SCSI_reserv': None,
                'RAM_RC': None,
                'provisioning': None,  # volume_only
                'parent_volume': None,
                'capacity_in_use_mg': None  # volume_only # check for variants
            }
            values_regex_dict = {
                'ID': [r'Volume ID:\s([\d\w]{16})'],
                'name': [r"\sName:\s([-\w]*)\s"],  # watch out for SDC names
                'size_in_gb': [r'Size:\s[^(]*\((\d*)'],
                'creation_time': [r'Creation time:\s(\d)*'],
                'num_of_direct_snaps': [r'Number of Direct Snapshots:\s(\d)*'],
                'reads': [r'Reads:\s*(\d)*'],
                'writes': [r'Writes:\s*(\d)*'],
                'mappings': [
                    r'(Volume is not mapped)',
                    r'\sSDC ID:\s([\w]{16}) IP:\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\sName:\s(.[^\s]*)\s',
                    # All about SDCs, (ID), (IP), (NAME)
                ],
                'SCSI_reserv': None,  # TODO: ADD  SCSI_reserv parsing for query_volume_tree # {No SCSI reservations, ---}
                'RAM_RC': None,  # TODO: ADD  RAM_RC parsing for query_volume_tree {doesn't use RAM Read Cache, ---}
                'provisioning&parent_volume': [r'Provisioning: (\w*)',  # volume_only
                                               r'Snapshot of ([-\w_]*)'],
                'capacity_in_use_mg': [r'Capacity in use:\s[^(]*\((\d*)']  # volume_only
            }
            for each_value, each_regex_list in values_regex_dict.items():
                def parse_by_list(volume_info_to_parse: str, each_regex_list_func):
                    if type(each_regex_list_func) == list:
                        pass
                    else:
                        # unsupported value
                        return None
                    found_value_func = []
                    try:
                        for each_regex in each_regex_list_func:

                            matches_func = re.finditer(each_regex, volume_info_to_parse.replace('\n', ' ').replace('\t',
                                                                                                                   '').replace(
                                '\r', '').rstrip(), re.MULTILINE | re.IGNORECASE)
                            if matches_func:
                                for matchNum, match in enumerate(matches_func, start=1):
                                    if 'SDC ID' in each_regex:
                                        found_value_func.append(
                                            {'ID': match.group(1), 'IP': match.group(2), 'name': match.group(3)})
                                    else:
                                        found_value_func.append(match.group(1))

                            else:
                                self.logger.debug('failed to parse: ' + str(each_regex_list_func) + ', ' + volume_info_to_parse)
                                continue
                        if len(found_value_func) == 0:
                            self.logger.debug(
                                'failed to parse: ' + str(each_regex_list_func) + ', ' + volume_info_to_parse)
                            return None
                        else:
                            return found_value_func
                    except re.error:
                        self.logger.error('Parsing failed on: ' + str(each_regex_list_func) + ', ' + volume_info_to_parse)
                        return None

                found_value = parse_by_list(each_volume_func, each_regex_list)
                if found_value and len(found_value) == 1:
                    found_value = found_value[0]
                if each_value == 'provisioning&parent_volume':
                    if found_value in ('Thin', 'Thick'):
                        volume_info_dict['provisioning'] = found_value
                        volume_info_dict['type'] = 'volume'
                    else:
                        volume_info_dict['parent_volume'] = found_value
                        volume_info_dict['type'] = 'snapshot'
                elif each_value == 'mappings':
                    if found_value == 'Volume is not mapped':
                        volume_info_dict[each_value] = None
                    elif found_value is None:
                        volume_info_dict[each_value] = found_value
                    else:
                        # Adding SDCs
                        volume_info_dict[each_value] = found_value
                elif each_value == 'name':
                    volume_info_dict[each_value] = found_value
                else:
                    volume_info_dict[each_value] = found_value
            return volume_info_dict

        def make_vtree_info_dict(vtree_info_raw_func):
            vtree_info_raw_func = vtree_info_raw_func.replace('\n', ' ').replace('\t', '')
            vtree_info_dict = {
                'sp_id': None,
                'sp_name': None,
                'pd_id': None,
                'pd_name': None,
                'ID': None,
                'name': None,
                'data_layout': None,
                'num_of_vols': None,
                'migration': None,
                'provisioning': None,
                'snapshots_capacity': None,
                'capacity_in_use_mg': None,
                'base_capacity_in_use_mg': None
            }
            values_regex_dict = {
                'sp_id': [r'Storage Pool\s([\w]{16})\sName'],
                'sp_name': [r'\sName:\s.*\sName:\s(.*)\sProtection'],
                'pd_id': [r'Protection Domain\s([\w]{16})'],
                'pd_name': [r'\sName:\s(\w*)\sData layout'],
                'ID': [r'VTree ID:\s([\d\w]{16})'],
                'name': [r"\sName:\s(.*)\sStor"],  # watch out for other names
                'data_layout': [r'\sData layout:\s([\w\s]*)\sProvisioning'],
                'num_of_vols': [r'Number of Volumes:\s(\d*)\sMigration'],
                'migration': [r'Migration status:\s([\w\s]*)'],
                'provisioning': [r'Provisioning:\s(\w*)\sTotal'],
                'snapshots_capacity': [r'Total snapshots capacity:\s(\d*)\s'],
                'base_capacity_in_use_mg': [r'Total base capacity in use:\s.[^\(]*\((\d*)\s.[^\)]*'],
                'capacity_in_use_mg': [r'Total capacity in use:\s.[^\(]*\((\d*)\s.[^\)]*']
            }
            for each_value, each_regex_list in values_regex_dict.items():
                def parse_by_list(vtree_info_to_parse: str, each_regex_list):
                    if type(each_regex_list) == list:
                        pass
                    else:
                        # unsupported value
                        return None
                    found_value_func = []
                    try:
                        for each_regex in each_regex_list:
                            matches_func = re.finditer(each_regex, vtree_info_to_parse, re.MULTILINE | re.IGNORECASE)
                            if matches_func:
                                for matchNum, match in enumerate(matches_func, start=1):
                                    found_value_func.append(match.group(1))

                            else:
                                self.logger.warning('failed to parse: ' + str(each_regex_list) + ', ' + vtree_info_to_parse)
                                continue
                        if len(found_value_func) == 0:
                            self.logger.warning(
                                'failed to parse: ' + str(each_regex_list) + ', ' + vtree_info_to_parse)
                            return None
                        else:
                            return found_value_func
                    except re.error:
                        self.logger.error('Parsing failed on: ' + str(each_regex_list) + ', ' + vtree_info_to_parse)
                        return None

                found_value = parse_by_list(vtree_info_raw_func, each_regex_list)
                if found_value and len(found_value) == 1:
                    found_value = found_value[0]

                if each_value == 'migration':
                    if 'Not in migration' in found_value:
                        vtree_info_dict[each_value] = False
                elif found_value is None:
                    vtree_info_dict[each_value] = found_value
                else:
                    vtree_info_dict[each_value] = found_value
            return vtree_info_dict

        # searching for volumes&information
        for each_volume in result_by_nodes:
            volumes_info.append(make_volume_info_dict(each_volume))
        vtree_info = make_vtree_info_dict(vtree_info_raw)
        return vtree_info, volumes_info


class SCLIResultSnapshotVolume(SCLIResultGeneral):
    def __init__(self, result: dict):
        SCLIResultGeneral.__init__(self, result)

    def get_id(self):
        self.logger.debug('Starting get_id validation, result = "' + self.result + '"')
        if self.status is False:
            raise Exception  # TODO: add SCLIResult like "SCLIResult func cannot be used due to a faulty answer"
        regex = r"=>\s(([\d\w]{16}))\s"
        matches = re.finditer(regex, self.result, re.MULTILINE | re.IGNORECASE)
        if matches:
            for matchNum, match in enumerate(matches, start=1):
                snapshot_id = match.group(1)
                return snapshot_id
        else:
            raise Exception  # TODO: add get_id parsing error


class SCLIResultMapVolumeToSdc(SCLIResultGeneral):
    def __init__(self, result: dict):
        SCLIResultGeneral.__init__(self, result)

    def get_id(self):
        self.logger.debug('Starting get_id validation, result = "' + self.result + '"')
        if self.status is False:
            raise Exception  # TODO: add SCLIResult like "SCLIResult func cannot be used due to a faulty answer"
        regex = r"Successfully mapped volume with ID\s(([\d\w]{16}))\sto SDC"
        matches = re.finditer(regex, self.result, re.MULTILINE | re.IGNORECASE)
        if matches:
            for matchNum, match in enumerate(matches, start=1):
                volume_id = match.group(1)
                return volume_id
        else:
            raise Exception  # TODO: add get_id parsing error