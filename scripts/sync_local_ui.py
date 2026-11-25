"""Prepare the local HTML/CSS/JS as a Streamlit custom component."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'code/webapp/static'
DEST = ROOT / 'code/webapp/component'


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    for filename in ['index.html', 'app.js', 'style.css']:
        shutil.copy2(SOURCE / filename, DEST / filename)
    html = (DEST / 'index.html').read_text(encoding='utf8')
    html = html.replace('href="/style.css', 'href="style.css').replace('src="/app.js', 'src="app.js')
    html = html.replace('<script src="app.js', '<script src="bridge.js"></script><script src="app.js')
    (DEST / 'index.html').write_text(html, encoding='utf8')
    shutil.copy2(ROOT / 'code/webapp/component_bridge.js', DEST / 'bridge.js')
    script = (DEST / 'app.js').read_text(encoding='utf8')
    old = "function download(url, filename) { const a = document.createElement('a'); a.href = url; if (filename) a.download = filename; a.click(); }"
    new = "async function download(url, filename) { const result=await fetch(url);if(!result.ok){toast('下载失败');return;}const objectUrl=URL.createObjectURL(await result.blob());const a=document.createElement('a');a.href=objectUrl;if(filename)a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(objectUrl),30000); }"
    if old not in script:
        raise ValueError('Local download handler changed; update the component adapter')
    (DEST / 'app.js').write_text(script.replace(old, new), encoding='utf8')
    print('Prepared local HTML interface for Streamlit')


if __name__ == '__main__':
    build()
