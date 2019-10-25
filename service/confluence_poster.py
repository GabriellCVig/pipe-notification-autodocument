import logging
import os
import sys
import json
import requests
import datetime

from confluence.client import Confluence
from confluence.models.content import ContentType
from confluence.exceptions import resourcenotfound, authenticationerror
from jinja2 import Template


required_env_vars = ['NODE_URL', 'JWT', 'PAGE_ID', 'CONFLUENCE_USERNAME', 'CONFLUENCE_PASSWORD']
CONFLUENCE_BASE_URL = 'https://hafslundnett.atlassian.net/wiki'
base_template = """
<html>
<body>
  <TR>
      <table>
        <TR><!-- First row has column names -->
          <TD><B>Pipe</B></TD>
          {% for type in rule_types %}
            <TD><B>{{ type }}</B></TD>
          {% endfor %}
        </TR>
        {% for pipe in pipes %} <!-- for each pipe -->
          <TR> <!-- Create row for this pipe-->
            <TD>{{ pipe['_id'] }}</TD>
            {% for type in rule_types %}<!-- for hver regel som finnes-->
              {% if type in pipe['pipe_rule_types'] %}<!-- hvis pipen har regelen -->
                <TD>
                {% for rule in pipe['rules'] %} <!-- for hver regel i pipen-->
                  {% if type == rule['type'] %}<!-- hvis denne regelen er av riktig type -->
                    {{ rule['description'] }} <!-- legg til decsription -->
                  {% endif %}
                {% endfor %}
                </TD>
              {% else %}
                <TD> &#32; </TD>
              {% endif %}
            {% endfor %}
          </TR>
        {% endfor %}
      </table>
  </TR>
</body>
</html>
"""

class AppConfig(object):
    pass


config = AppConfig()

# load variables
missing_env_vars = list()
for env_var in required_env_vars:
    value = os.getenv(env_var)
    if not value:
        missing_env_vars.append(env_var)
    setattr(config, env_var, value)


log_level = logging.getLevelName(os.environ.get('LOG_LEVEL', 'INFO'))
logging.basicConfig(level=log_level)
logging.debug(datetime.datetime.now())

def update_confulence(base_template, content):
    with Confluence(CONFLUENCE_BASE_URL, (config.CONFLUENCE_USERNAME, config.CONFLUENCE_PASSWORD)) as cfl:
        try:
            tmp_page = cfl.get_content_by_id(config.PAGE_ID)
        except resourcenotfound.ConfluenceResourceNotFound as e:
            logging.error('Could not find resource {}. Error message: \n"{}"\nExiting.'.format(config.PAGE_ID, e))
            sys.exit(-1)
        except authenticationerror.ConfluenceAuthenticationError as e:
            logging.error('Authentication failure for user "{}". Error message: \n"{}"\nExiting.'.format(config.CONFLUENCE_USERNAME, e))
            sys.exit(-1)
        cfl.update_content(
            content_id=tmp_page.id,
            content_type=ContentType.PAGE,
            new_version=tmp_page.version.number + 1,
            new_content=Template(base_template).render(**content),
            new_title=tmp_page.title.title())


class Node:
    def __init__(self, NODE_URL, JWT):
        self.NODE_URL=NODE_URL
        self.JWT=JWT
        self.Session=requests.session()

    def get_all_pipes(self):
        try:
            response= self.Session.get(url="{}/api/pipes".format(self.NODE_URL),
                                headers={'Authorization': 'bearer ' + self.JWT})
        except requests.exceptions.ConnectionError as e:
            logging.error("Connectionerror fetching pipes from node: '{}'. \nError printout below:\n{}\n".format(self.NODE_URL, e))
            sys.exit(-1)
        if response.status_code == 200:
            return json.loads(response.content)
        else:
            logging.error("Got status code: '{}' while fetching pipes from node: '{}'\nExiting.".format(response.status_code, self.NODE_URL))
            sys.exit(-1)


def pipes_with_notifications(pipes):
    pipes_with_notifications = []
    for p in pipes:
        if 'metadata' in p['config']['effective']:
            if 'notifications' in p['config']['effective']['metadata']:
                if len(p['config']['effective']['metadata']['notifications']) != 0:
                    pipes_with_notifications.append(p)
    return pipes_with_notifications


def get_distinct(list):
    output = []
    for x in list:
        if x not in output:
            output.append(x)
    return output


def get_pipe_info(pipes):
    rule_types = []
    output_pipes = []
    for p in pipes:
        pipe_rules = []
        pipe_rule_types = []
        for r in p['config']['effective']['metadata']['notifications']['rules']:
            pipe_rules.append({'type': r['type'], 'description':r['description'] + ';  '})
            rule_types.append(r['type'])
            pipe_rule_types.append(r['type'])
        output_pipes.append({'_id':p['_id'],
                             'rules': pipe_rules,
                             'pipe_rule_types': pipe_rule_types})
    return {'rule_types': get_distinct(rule_types),
              'pipes':sorted(output_pipes, key=lambda i: i['_id'])}


if __name__ == '__main__':
    if len(missing_env_vars) != 0:
        logging.error('Missing env vars: {}.\nExiting.'.format(missing_env_vars))
        sys.exit(-1)
    node = Node(config.NODE_URL, config.JWT)
    update_confulence(base_template=base_template, content=get_pipe_info(pipes_with_notifications(node.get_all_pipes())))
    logging.info('Succesfully posted pipe notifications config to confluence.')
    sys.exit(0)