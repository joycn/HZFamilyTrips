#!/usr/bin/env python3
"""Generate the family itinerary page from one JSON source; standard library only."""
import argparse, copy, datetime as dt, html, json, math, re
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / 'assets'
def esc(value):
    return html.escape(str(value), quote=True)
def paragraphs(values):
    return ''.join('<p>'+esc(x)+'</p>' for x in values)
def safe_url(value):
    return isinstance(value,str) and value.startswith(('https://','http://'))
def normalize(raw):
    d=copy.deepcopy(raw)
    assert d.get('title') and d.get('travelers'), 'title/travelers required'
    days=d['days']; assert days, 'days cannot be empty'
    r=d['dailyRoutes']; points=r['points']; assert points, 'map points required'
    assert len(r['days'])==len(days), 'route/day count mismatch'
    citydays={}; last=None
    for i,day in enumerate(days):
        date=dt.date.fromisoformat(day['date'])
        assert last is None or date-last==dt.timedelta(days=1), 'dates must be consecutive'
        last=date; day['weekday']='周'+'一二三四五六日'[date.weekday()]
        assert day.get('stay') and day.get('activities'), 'stay/activities required'
        rr=r['days'][i]; assert rr['date']==day['date'], 'route date mismatch'
        assert rr['stops'] and len(rr['legs'])==len(rr['stops'])-1, 'route edge count'
        for pid in rr['stops']:
            assert pid in points, 'unknown point '+pid
            p=points[pid]
            coords=p.get('p')
            assert coords is not None or p.get('kind')=='restaurant', 'only restaurants may omit coordinates'
            lat,lon=coords if coords is not None else (0,0)
            assert all(isinstance(x,(int,float)) and math.isfinite(x) for x in [lat,lon]), 'invalid coordinate'
            assert -90<=lat<=90 and -180<=lon<=180, 'coordinate outside globe'
            assert p.get('name') and p.get('city'), 'point name/city required'
            citydays.setdefault(p['city'],[])
            if i not in citydays[p['city']]: citydays[p['city']].append(i)
    r['cityDays']=citydays
    r.setdefault('coordinateNote','点位为位置示意；虚线表示访问顺序，不是实际道路。底图需联网。')
    budget=d['budget']; items=budget['items']
    assert all(isinstance(x['amount'],(int,float)) and math.isfinite(x['amount']) and x['amount']>=0 for x in items), 'invalid budget'
    budget['total']=round(sum(x['amount'] for x in items),2)
    count=d.get('travelerCount')
    budget['perPerson']=round(budget['total']/count,2) if isinstance(count,int) and count>0 else None
    drive=d.get('drivingSummary')
    if drive:
        assert [x['date'] for x in drive['days']]==[x['date'] for x in days], 'driving dates must cover all days'
        for day, mileage in zip(days, drive['days']):
            day['activities']=[a for a in day['activities'] if a['time']!='当天自驾里程（估算）']
            day['activities'].insert(0, dict(time='当天自驾里程（估算）',description=mileage['route']+'：'+mileage['distance']+'；驾驶时长 '+mileage['duration']+'。不含游览及用餐休息。'))
    # Derive overview from route visits; avoid stale duplicated city cards or day indexes.
    stops=[]
    for city,indices in citydays.items():
        ps=[p for p in points.values() if p['city']==city]
        dates=[days[i]['date'][5:] for i in indices]
        overnight=[x['date'][5:] for x in days if x.get('stayCity',x['stay'])==city]
        stops.append(dict(name=city,p=d.get('cityCenters',{}).get(city,next(p['p'] for p in ps if p.get('p') is not None)),date=' / '.join(dates),stay='、'.join(overnight)+'住宿' if overnight else '详见每日夜宿',spots=[p['name'] for p in ps if p.get('kind')=='sight'],restaurants=[p['name'] for p in ps if p.get('kind')=='restaurant']))
    names=[x['name'] for x in stops]; legs=[]
    for rr in r['days']:
        for i,label in enumerate(rr['legs']):
            ca=points[rr['stops'][i]]['city']; cb=points[rr['stops'][i+1]]['city']
            if ca!=cb:
                color='#8653ad' if re.search('航班|飞机|飞行',label) else '#2563a6' if re.search('动车|高铁|火车|铁路|卧铺',label) else '#bd641f'
                legs.append(dict(a=names.index(ca),b=names.index(cb),label=rr['date']+' '+label,color=color))
    d['overview']=dict(stops=stops,legs=legs)
    d.setdefault('focusCities',[])
    assert not d['focusCities'] or all(c in citydays for c in d['focusCities']), 'unknown focus city'
    return d

def render(d):
    b=d['budget']; total=f"{b['total']:,.2f}"; title=esc(d['title'])
    css=(ASSETS/'style.css').read_text(); modal=(ASSETS/'city-dialog.html').read_text()
    out=['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+css+'</style><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""></head><body><main>']
    out.append('<header><h1>'+title+'</h1>'+paragraphs([d.get('dateRange',d['days'][0]['date']+' — '+d['days'][-1]['date']),d['travelers'],' → '.join(d.get('route',[x['name'] for x in d['overview']['stops']])), '全家预算 ¥'+total])+'<nav><a href="#route-map">路线地图</a><a href="#days">每日行程</a><a href="#transport">交通与里程</a><a href="#stay">住宿</a><a href="#budget">预算</a></nav></header>')
    if d.get('summary'): out.append('<div class="note">'+esc(d['summary'])+'</div>')
    out.append('<section id="route-map"><h2>完整路线地图</h2><div class="map-toolbar"><button id="map-northwest" aria-pressed="true">主要游玩区域</button> <button id="map-all" aria-pressed="false">全程路线</button></div><div id="trip-map" role="region" aria-label="城市路线地图">地图加载中；完整行程见下方。</div><p id="map-status">点击城市标记，在弹窗中查看城市行程。</p><p id="city-fallback" hidden><label for="city-select">选择城市：</label><select id="city-select"><option value="">请选择城市</option></select></p><p>蓝色：铁路 · 紫色：飞机 · 橙色：自驾/地面交通</p><small>'+esc(d['dailyRoutes']['coordinateNote'])+'</small></section><h2 id="days">每日行程</h2>')
    for day in d['days']:
        out.append('<details open><summary>'+esc(day['date']+' '+day['weekday']+'｜'+day['theme'])+'</summary><p class="tag">夜宿：'+esc(day['stay'])+'</p>')
        out.extend('<p><b>'+esc(a['time'])+'</b>　'+esc(a['description'])+'</p>' for a in day['activities'])
        meals=[(pid,d['dailyRoutes']['points'][pid]) for pid in dict.fromkeys(d['dailyRoutes']['days'][d['days'].index(day)]['stops']) if d['dailyRoutes']['points'][pid].get('kind')=='restaurant']
        if meals:
            out.append('<section class="daily-restaurants"><h3>当天餐厅与导航</h3><ul>')
            for pid,p in meals:
                from urllib.parse import quote
                query=p.get('navigationQuery') or (p['city']+' '+p['name'])
                out.append('<li><b>餐饮 · '+esc(p['name'])+'</b><br>'+esc(p.get('address','地址待确认'))+'<br><small>'+('已核店铺点位，入口以导航为准' if p.get('p') is not None else '坐标待核，地图暂不标点')+'</small> · <a target="_blank" rel="noopener noreferrer" href="https://www.amap.com/search?query='+esc(quote(query))+'">按店名导航 ↗</a></li>')
            out.append('</ul></section>')
        out.append('</details>')
    out.append('<h2 id="transport">交通与每日里程</h2>'+paragraphs(d.get('transport_notes',[])))
    for booking in d.get('bookings',[]):
        out.append('<article>'+paragraphs([booking.get('date','')+' '+booking.get('number',''),booking.get('from','')+' → '+booking.get('to',''),booking.get('departure','')+' — '+booking.get('arrival',''),booking.get('status','待核')])+'</article>')
    drive=d.get('drivingSummary')
    if drive:
        out.append('<p>'+esc(drive.get('note','估算，非实时导航'))+'</p><div class="scroll"><table><tr><th>日期</th><th>路线</th><th>里程</th><th>驾驶时长</th></tr>')
        out.extend('<tr>'+''.join('<td>'+esc(x[k])+'</td>' for k in ['date','route','distance','duration'])+'</tr>' for x in drive['days'])
        out.append('</table></div><p>合计：'+esc(drive.get('total','待核'))+'</p>')
    out.append('<h2 id="stay">住宿安排</h2><div class="grid">')
    for hotel in d.get('hotels',[]):
        out.append('<article><h3>'+esc(hotel['city']+'｜'+hotel['dates'])+'</h3>')
        out.append(paragraphs([hotel[k] for k in ['name','address','area','target','status','bookingDetails','reason','cancellation','extensionStatus'] if hotel.get(k)]))
        out.append('</article>')
    out.append('</div><h2 id="budget">预算与金额口径</h2><div class="scroll"><table><tr><th>类别</th><th>口径</th><th>可靠度</th><th>金额</th></tr>')
    out.extend('<tr>'+''.join('<td>'+esc(x.get(k,''))+'</td>' for k in ['category','description','reliability','amount'])+'</tr>' for x in b['items'])
    out.append('</table></div><p>合计 ¥'+total+(('；人均 ¥'+str(b['perPerson'])) if b['perPerson'] is not None else '')+'</p>'+paragraphs([b.get('range','动态费用以最终订单为准。')]))
    out.append('<h2>天气与实用提示</h2>'+paragraphs([str(x) for x in d.get('weather',{}).values() if x])+paragraphs(d.get('tips',[]))+'<h2>来源</h2>')
    out.extend('<p><a target="_blank" rel="noopener noreferrer" href="'+esc(x['url'])+'">'+esc(x['title'])+'</a></p>' for x in d.get('sources',[]) if safe_url(x.get('url')))
    out.append('<button onclick="window.print()">打印 / 保存PDF</button></main>'+modal)
    payload=json.dumps(d,ensure_ascii=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    out.append('<script type="application/json" id="daily-route-data">'+payload+'</script><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>')
    out.extend('<script>'+ (ASSETS/name).read_text()+'</script>' for name in ['overview.js','city.js'])
    out.append('<script>window.addEventListener("beforeprint",()=>document.querySelectorAll("details").forEach(x=>x.open=true));</script></body></html>')
    return '\n'.join(out)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('data');parser.add_argument('output');args=parser.parse_args()
    d=normalize(json.loads(Path(args.data).read_text(encoding='utf-8')))
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(render(d),encoding='utf-8')
    output.with_name('tripData.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Generated:',output)
if __name__=='__main__': main()
