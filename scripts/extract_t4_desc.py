from pathlib import Path
import json

html = Path(r'C:\Users\andre\Downloads\ES_TJ_Trader_6.1.html').read_text(encoding='utf-8', errors='ignore')
start = html.index('const T4_DESC=')
tail = html[start + len('const T4_DESC='):]
end = tail.index(';</script>')
j = tail[:end]
desc = json.loads(j)
out = Path(r'C:\Users\andre\Kivaro\kivaro-investor-reports\trading_agent\t4_desc.json')
out.write_text(j, encoding='utf-8')
print('ok', len(j), list(desc['nested']['t4proto']['nested']['v2']['nested'].keys()))
