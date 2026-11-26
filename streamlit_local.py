"""Host the local ImmuNiche interface through Streamlit Components."""
from functools import lru_cache
from pathlib import Path
import importlib
import json
import os
import sys
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'code/webapp'))
from analysis import INPUT, OUTPUT
from example_io import load_counts
from deepseek_agent import Agent, AgentError
import component_api
# A live deployment can leave the previous API module in the running process.
if not hasattr(component_api, 'RequestError'):
    importlib.reload(component_api)
from component_api import RequestError, bootstrap, route_request


def read_service_key():
    try:
        value = st.secrets.get('DEEPSEEK_API_KEY', '')
        if not value:
            value = st.secrets.get('deepseek', {}).get('api_key', '')
        return str(value or os.environ.get('DEEPSEEK_API_KEY', '')).strip()
    except (FileNotFoundError, KeyError):
        return os.environ.get('DEEPSEEK_API_KEY', '').strip()


@lru_cache(maxsize=3)
def matrix_for(dataset_id):
    manifest = json.loads((INPUT / 'manifest.json').read_text(encoding='utf8'))
    item = next((d for d in manifest['datasets'] if d['dataset_id'] == dataset_id), None)
    if item is None:
        raise KeyError('Unknown dataset')
    return load_counts(INPUT / item['counts']), pd.read_csv(INPUT / item['genes'], sep='\t')['gene'].tolist()


@st.cache_resource(show_spinner=False)
def analysis_payload():
    return bootstrap(False)


@st.cache_resource(show_spinner=False)
def configured_agent(key):
    agent = Agent(OUTPUT, matrix_for)
    agent.configure(key)
    return agent


def main():
    st.set_page_config(page_title='ImmuNiche', page_icon='◈', layout='wide', initial_sidebar_state='collapsed')
    st.markdown('<style>.block-container{padding:0!important;max-width:none!important}[data-testid=stHeader]{background:transparent;height:0}[data-testid=stToolbar],[data-testid=stAppDeployButton],footer{display:none!important}.stMain{padding:0!important}iframe{border:0}</style>', unsafe_allow_html=True)
    service_key = read_service_key()
    initial = dict(analysis_payload())
    initial['/api/agent/status'] = {'configured': bool(service_key)}
    ui = components.declare_component('immuniche_local_ui', path=str(ROOT / 'code/webapp/component'))
    request = ui(bootstrap=initial, reply=st.session_state.get('ui_reply'), default=None, key='local_ui')
    if isinstance(request, dict) and request.get('id') and request['id'] != st.session_state.get('ui_processed'):
        try:
            result = route_request(request, matrix_for, lambda: configured_agent(service_key))
        except AgentError as error:
            result = {'data': {'error': str(error)}}
        except RequestError as error:
            result = {'data': {'error': str(error)}, 'status': 400}
        except Exception:
            result = {'data': {'error': '分析服务暂时不可用，请重试。'}, 'status': 500}
        st.session_state['ui_processed'] = request['id']
        st.session_state['ui_reply'] = {'id': request['id'], **result}
        st.rerun()


if __name__ == '__main__':
    main()
