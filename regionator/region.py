import json
import os
import uuid

from json import JSONEncoder

import parser


DEFAULT_REGIONATOR_NAME = '{0} - Generated by Regionator'


def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)

_default.default = JSONEncoder().default
JSONEncoder.default = _default


class Mod(object):
  def __init__(self, region, identifier, params={}, additional_params={},
      contained_mods=[]):
    self.region = region
    self.identifier = identifier
    self.params = params
    self.additional_params = additional_params
    self.contained_mods = contained_mods
    self.id = str(uuid.uuid4())[:4]

  def __repr__(self):
    return '<Mod(identifier="{0}", params={1})>'.format(self.identifier, self.params)

  @property
  def neohabitat_ascii_params(self):
    params_with_numeric_keys = {
      int(param[0]): param[1] for param in self.additional_params.items()
    }
    ascii_list = []
    for param_key in sorted(params_with_numeric_keys.keys()):
      ascii_list.append(int(params_with_numeric_keys[param_key]))
    return ascii_list

  @property
  def neohabitat_mod(self):
    mod_json = {
      'type': self.neohabitat_name,
      'x': int(self.params['x']),
      'y': int(self.params['y']),
      'orientation': int(self.params['or']),
    }
    if 'style' in self.params:
      mod_json['style'] = int(self.params['style'])
    if 'gr_state' in self.params:
      mod_json['gr_state'] = int(self.params['gr_state'])
    if self.additional_params:
      mod_json['ascii'] = self.neohabitat_ascii_params
    return mod_json

  @property
  def neohabitat_name(self):
    return self.identifier.capitalize()

  @property
  def neohabitat_ref(self):
    return 'item-{0}{1}.{2}'.format(self.identifier, self.id,
        self.region.neohabitat_context)

  def to_json(self):
    return {
      'type': 'item',
      'ref': self.neohabitat_ref,
      'name': self.neohabitat_name,
      'in': self.region.neohabitat_context,
      'mods': [self.neohabitat_mod],
    }


class Region(object):
  def __init__(self, name, params=None, mods=None, parse_results=None):
    self.name = name
    
    if params is None:
      self.params = {}
    else:
      self.params = params
    
    if mods is None:
      self.mods = []
    else:
      self.mods = mods

    if parse_results is not None:
      # It's much easier to work with the pure Python representation of a
      # pyparsing.ParseResults, hence this horrible hack.
      exec('self.raw_results = ' + parse_results.__repr__())
      self.results_dict = self.raw_results[1]

  def __repr__(self):
    return '<Region(name="{0}", params={1}, mods={2})>'.format(self.name, self.params,
        self.mods)

  @classmethod
  def from_rdl_file(cls, rdl_file):
    # For now, we'll assume a 1-to-1 mapping between the region file name and the name
    # of the region
    region_name = os.path.basename(rdl_file.split('.')[-2])
    with open(rdl_file, 'r') as rdlfile:
      rdlfile_text = rdlfile.read()
      results = parser.region.parseString(rdlfile_text)
      return cls.from_parse_results(region_name, results)

  @classmethod
  def from_parse_results(cls, name, parse_results):
    region = cls(name=name, parse_results=parse_results)
    region._parse_params_from_results()
    region._parse_mods_from_results()
    return region

  @property
  def neohabitat_context(self):
    return 'context-{0}'.format(self.name)

  def _parse_params_from_results(self):
    self.params = self._parse_params(self.results_dict['region_params'][0][0])

  def _parse_params(self, param_tokens):
    params = {}
    param_name = None
    param_value = None
    on_name = True
    for token in param_tokens:
      if token == '\n':
        pass
      elif ':' in token:
        on_name = False
      elif token == ';':
        params[param_name] = param_value
        on_name = True
      elif on_name:
        param_name = token
      else:
        param_value = token
    return params

  def _parse_mods_from_results(self):
    mods = self.results_dict['mods']
    for mod in mods[0][1]['mod']:
      mod_dict = mod[1]
      mod_identifier = mod_dict['mod_identifier'][0]

      mod_params = {}
      if 'mod_params' in mod_dict:
        mod_params.update(self._parse_params(mod_dict['mod_params'][0][0]))

      mod_params_additional = {}
      if 'mod_params_additional' in mod_dict:
        mod_params_additional.update(
            self._parse_params(mod_dict['mod_params_additional'][0][0]))

      self.mods.append(Mod(region=self, identifier=mod_identifier, params=mod_params,
          additional_params=mod_params_additional))

  def to_json(self):
    region_mod = {
      'town_dir': '',
      'port_dir': '',
      'type': 'Region',
      'nitty_bits': 3,
      'neighbors': ['', '', '', ''],
    }
    if 'east' in self.params:
      region_mod['neighbors'][0] = 'context-{0}'.format(
          self.params['east'].split('.')[0])
    if 'south' in self.params:
      region_mod['neighbors'][1] = 'context-{0}'.format(
          self.params['south'].split('.')[0])
    if 'west' in self.params:
      region_mod['neighbors'][2] = 'context-{0}'.format(
          self.params['west'].split('.')[0])
    if 'north' in self.params:
      region_mod['neighbors'][3] = 'context-{0}'.format(
          self.params['north'].split('.')[0])

    region_context = {
      'type': 'context',
      'ref': self.neohabitat_context,
      'capacity': 6,
      'name': DEFAULT_REGIONATOR_NAME.format(self.name),
      'mods': [region_mod]
    }

    region_contents = [region_context] + self.mods
    return region_contents
