(function(){
  'use strict';
  const data=JSON.parse(document.getElementById('daily-route-data').textContent);
  const config=data.dailyRoutes, points=config.points;
  const modal=document.getElementById('city-journey');
  const title=document.getElementById('city-title'), tabs=document.getElementById('city-dates');
  const content=document.getElementById('city-content'), routes=document.getElementById('city-route-list');
  const mapNode=document.getElementById('city-map'), status=document.getElementById('city-map-status');
  let map,layer,city,currentIndex,focusBack,localOnly=true;
  const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
  const link=(name)=>{const n=el('a','在高德查看 ↗');n.href='https://www.amap.com/search?query='+encodeURIComponent(name);n.target='_blank';n.rel='noopener noreferrer';return n;};
  const sights=new Set(Object.keys(points).filter(id=>points[id].kind==='sight'));
  const restaurants=new Set(Object.keys(points).filter(id=>points[id].kind==='restaurant'));
  const mapped=p=>Array.isArray(p.p)&&p.p.length===2&&p.p.every(Number.isFinite);
  const prefix=id=>restaurants.has(id)?'餐饮 · ':sights.has(id)?'★ ':'';
  function overviewRoute(){return {stops:[...new Set(config.cityDays[city].flatMap(i=>config.days[i].stops))].filter(id=>points[id].city===city),legs:[]};}
  function visitDates(id){return config.cityDays[city].filter(i=>config.days[i].stops.includes(id)).map(i=>data.days[i].date.slice(5).replace("-","/")).join("、");}
  function fit(){
    if(!map)return;
    const r=currentIndex===-1?overviewRoute():config.days[currentIndex];
    let nodes=r.stops.map(id=>points[id]).filter(mapped);
    if(localOnly)nodes=nodes.filter(p=>p.city===city);
    if(!nodes.length)nodes=r.stops.map(id=>points[id]).filter(mapped);if(!nodes.length){map.setView([35,105],4);return;}
    map.invalidateSize();map.fitBounds(nodes.map(p=>p.p),{padding:[42,42],maxZoom:13});
    document.getElementById('city-local').setAttribute('aria-pressed',String(localOnly));
    document.getElementById('city-whole').setAttribute('aria-pressed',String(!localOnly));
  }
  function render(index){
    currentIndex=index;const overview=index===-1;const day=overview?{date:"",weekday:"",theme:city+"全部游玩地点",stay:"详见各日安排",activities:config.cityDays[city].flatMap(i=>data.days[i].activities.map(a=>({time:data.days[i].date+" · "+a.time,description:a.description})))}:data.days[index],r=overview?overviewRoute():config.days[index];
    document.getElementById("city-whole").textContent=overview?"全城总览":"当天全程";
    document.querySelector("#city-route-list").previousElementSibling.textContent=overview?"全城地点与游玩日期":"当天完整路线";
    tabs.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.index)===index)));
    content.replaceChildren(el('h3',day.date+' '+day.weekday+'｜'+day.theme),el('p','夜宿：'+day.stay));
    const timeline=el('div');timeline.className='city-timeline';
    day.activities.forEach(a=>{const item=el('article');item.append(el('h4',a.time),el('p',a.description));timeline.append(item);});
    content.append(timeline);
    routes.replaceChildren();
    r.stops.forEach((id,i)=>{const p=points[id],li=el('li');li.append(el('strong',prefix(id)+p.name));li.append(el('small','安排日期：'+visitDates(id)));
      if(p.address)li.append(el('small','地址：'+p.address));
      li.append(el('small',!mapped(p)?'坐标待核 · 地图暂不标点':p.approx?'待确认具体位置 · 区域示意':'地点位置示意 · 入口以导航为准'));
      if(p.navigationQuery || !p.approx)li.append(link(p.navigationQuery || p.name));
      if(i<r.legs.length){const leg=el('p','↓ '+r.legs[i]);leg.className='route-leg';li.append(leg);}
      routes.append(li);
    });
    if(!window.L){mapNode.textContent='地图暂时无法加载，请查看下方完整路线与地点导航。';status.textContent='地图组件加载失败；日期切换和每日行程仍可使用。';document.getElementById('city-local').disabled=true;document.getElementById('city-whole').disabled=true;return;}
    if(!map){mapNode.replaceChildren();map=L.map(mapNode,{scrollWheelZoom:false});L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map).on('tileerror',()=>{status.textContent='部分底图加载失败；路线标记和下方路线文字仍可查看。';});layer=L.layerGroup().addTo(map);}
    layer.clearLayers();const missing=r.stops.filter((id,i,a)=>a.indexOf(id)===i&&!mapped(points[id]));status.textContent=config.coordinateNote+(missing.length?' 本次有'+missing.length+'处餐厅未标点，地址和导航见下方。':'');
    const unique=new Map();r.stops.forEach((id,i)=>{if(!unique.has(id))unique.set(id,[]);unique.get(id).push(i+1);});
    unique.forEach((numbers,id)=>{const p=points[id];if(!mapped(p))return;const pop=el('div');pop.append(el('b',numbers.join(' / ')+' · '+p.name),el('p','安排日期：'+visitDates(id)),el('p',p.note || (p.approx?'坐标未核验，标记仅表示区域':'位置示意，具体入口以导航为准')));if(p.navigationQuery || !p.approx)pop.append(link(p.navigationQuery || p.name));
      L.marker(p.p,{title:p.name,icon:L.divIcon({className:restaurants.has(id)?'trip-pin restaurant-pin':'trip-pin',html:'<span>'+(restaurants.has(id)?'🍴':numbers.join('/'))+'</span>',iconSize:[34,34],iconAnchor:[17,17]})}).addTo(layer).bindPopup(pop).bindTooltip(el('span',prefix(id)+p.name+' · '+visitDates(id)),{permanent:sights.has(id)||restaurants.has(id),direction:'top',offset:[0,-18],className:restaurants.has(id)?'city-restaurant-label':'city-sight-label'});
    });
    r.legs.forEach((label,i)=>{if(!mapped(points[r.stops[i]])||!mapped(points[r.stops[i+1]]))return;const color=/航班|飞机|飞行/.test(label)?'#8653ad':/动车|高铁|火车|铁路|卧铺/.test(label)?'#2563a6':'#bd641f';const pop=el('div',label);L.polyline([points[r.stops[i]].p,points[r.stops[i+1]].p],{color,weight:4,dashArray:'7 6'}).addTo(layer).bindPopup(pop);});
    requestAnimationFrame(fit);
  }
  function open(name,index){
    if(!config.cityDays[name])return;
    focusBack=document.activeElement;city=name;localOnly=true;title.textContent=city+' · 每日行程';
    tabs.replaceChildren();const all=el('button','景点与餐厅总览');all.type='button';all.dataset.index=-1;all.onclick=()=>render(-1);tabs.append(all);config.cityDays[city].forEach(i=>{const b=el('button',data.days[i].date.slice(5).replace('-','/')+' '+data.days[i].weekday);b.type='button';b.dataset.index=i;b.onclick=()=>render(i);tabs.append(b);});
    if(!modal.open)modal.showModal();document.body.classList.add('city-open');
    render(config.cityDays[city].includes(index)?index:-1);modal.scrollTop=0;
  }
  document.getElementById('city-close').onclick=()=>modal.close();
  modal.addEventListener('close',()=>{document.body.classList.remove('city-open');if(focusBack&&focusBack.isConnected)focusBack.focus();});
  modal.addEventListener('click',e=>{if(e.target===modal){const b=modal.getBoundingClientRect();if(e.clientX<b.left||e.clientX>b.right||e.clientY<b.top||e.clientY>b.bottom)modal.close();}});
  document.getElementById('city-local').onclick=()=>{localOnly=true;fit();};document.getElementById('city-whole').onclick=()=>{localOnly=false;fit();};

  function fromHash(){
    if(location.hash.startsWith('#city=')){
      let name;try{name=decodeURIComponent(location.hash.slice(6));}catch{return;}
      if(config.cityDays[name])open(name);
    }else if(modal.open)modal.close();
  }
  document.addEventListener('click',e=>{
    const link=e.target.closest('a[data-city]');
    if(!link)return;
    e.preventDefault();
    const name=link.dataset.city;
    if(!config.cityDays[name])return;
    const hash='#city='+encodeURIComponent(name);
    if(location.hash===hash)open(name);else location.hash=hash;
  });
  window.addEventListener('hashchange',fromHash);
  modal.addEventListener('close',()=>{
    if(location.hash.startsWith('#city='))history.replaceState(null,'',location.pathname+location.search+'#route-map');
  });
  const fallback=document.getElementById('city-fallback');
  if(!window.L){
    fallback.hidden=false;
    const select=document.getElementById('city-select');
    Object.keys(config.cityDays).forEach(name=>{const option=el('option',name);option.value=name;select.append(option);});
    select.onchange=()=>{if(select.value)location.hash='#city='+encodeURIComponent(select.value);};
  }
  fromHash();
})();
