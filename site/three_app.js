(function(){
const SCENE = __SCENE__;
const stage = document.getElementById('m3stage'), canvas = document.getElementById('m3canvas');
const info = document.getElementById('m3info'), tip = document.getElementById('m3tip'), legendEl = document.getElementById('m3legend');
if (!window.THREE || !THREE.OrbitControls) { document.getElementById('m3fallback').hidden = false; return; }
let renderer;
try { renderer = new THREE.WebGLRenderer({canvas, antialias:true, preserveDrawingBuffer:true}); }
catch(e){ document.getElementById('m3fallback').hidden = false; return; }
renderer.setPixelRatio(Math.min(window.devicePixelRatio||1, 2));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(38, 1.6, 0.5, 600);
const controls = new THREE.OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = 0.08; controls.maxPolarAngle = Math.PI*0.48;
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a9590, 0.85));
const sun = new THREE.DirectionalLight(0xffffff, 0.55); sun.position.set(-30, 60, 25); scene.add(sun);

const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function applyTheme(){ scene.background = new THREE.Color(css('--panel') || '#FAFBF9'); }
applyTheme();
try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme); new MutationObserver(applyTheme).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']}); } catch(e){}

const CODE_COL = {"DE-01":"#4F8EF0","DT-01":"#EFA43A","DT-02":"#46B05A","DT-03":"#E26A4C","CT-01":"#9640B8","CT-02":"#E856D9","CT-03":"#4CC3C3"};
const NONE_COL = "#A9B1AD", NEUTRAL = "#D5DBD8";
const pale = (hex) => { const c=new THREE.Color(hex); c.lerp(new THREE.Color('#ffffff'), 0.5); return '#'+c.getHexString(); };
const ERR_COL = {good:"#2E9E4B", warn:"#E3A12F", bad:"#D9432A"};
const NAME_FIX = {"(수유실)":"여직원휴게실 (수유실)", "DT-03 구역":"사무실 (총무·공보·입법 등)"};
const norm = s => String(s||'').replace(/\(.*?\)/g,'').replace(/배석.*$/,'').replace(/\s+/g,'');
const roomIdx = {}; (window.ROOMS_DATA||[]).forEach(r => roomIdx[r.floor+'|'+norm(r.room)] = r);
const FLOORS = ['B1','2F','3F'];
const LEVEL_ALL = {B1:0, '2F':6.5, '3F':13};
let mode = 'code', floorSel = 'ALL';
const groups = {}, cellMeshes = [];
const boxGeo = new THREE.BoxGeometry(1,1,1);
const wallMat = new THREE.MeshStandardMaterial({color:0x7d8a85, roughness:0.9});
const glassMat = new THREE.MeshStandardMaterial({color:0x7fb7d9, transparent:true, opacity:0.35, roughness:0.2});
const plateMat = new THREE.MeshStandardMaterial({color:0xe7ece9, roughness:1});

FLOORS.forEach(F => {
  const fd = SCENE.floors[F]; const g = new THREE.Group(); g.userData.floor = F;
  let xs=[], ys=[]; fd.walls.forEach(s=>{xs.push(s[0],s[2]); ys.push(s[1],s[3]);});
  const minx=Math.min(...xs)/1000, maxx=Math.max(...xs)/1000, miny=Math.min(...ys)/1000, maxy=Math.max(...ys)/1000;
  const cx=(minx+maxx)/2, cz=(miny+maxy)/2; g.userData.size=[maxx-minx, maxy-miny];
  const plate = new THREE.Mesh(boxGeo, plateMat); plate.scale.set(maxx-minx+1.2, 0.18, maxy-miny+1.2); plate.position.set(0,-0.1,0); g.add(plate);
  fd.cells.forEach(c => {
    const shape = new THREE.Shape(c.poly.map(p => new THREE.Vector2(p[0]/1000-cx, -(p[1]/1000-cz))));
    c.holes.forEach(h => shape.holes.push(new THREE.Path(h.map(p => new THREE.Vector2(p[0]/1000-cx, -(p[1]/1000-cz))))));
    const geo = new THREE.ExtrudeGeometry(shape, {depth:0.06, bevelEnabled:false});
    geo.rotateX(-Math.PI/2);
    const mat = new THREE.MeshStandardMaterial({color:0xffffff, roughness:0.8});
    const m = new THREE.Mesh(geo, mat); m.position.y = 0.0;
    const name = NAME_FIX[c.name] || c.name;
    m.userData = {floor:F, name, code:c.code, kind:c.kind, cell:c.cell_area_m2, region:c.region_area_m2, room: roomIdx[F+'|'+norm(name)]};
    g.add(m); cellMeshes.push(m);
  });
  function addSegs(segs, mat, h, t){
    if(!segs.length) return;
    const im = new THREE.InstancedMesh(boxGeo, mat, segs.length); const o = new THREE.Object3D();
    segs.forEach((s,i)=>{ const x1=s[0]/1000-cx, z1=s[1]/1000-cz, x2=s[2]/1000-cx, z2=s[3]/1000-cz;
      const L=Math.hypot(x2-x1,z2-z1); o.position.set((x1+x2)/2, h/2, (z1+z2)/2); o.rotation.set(0,-Math.atan2(z2-z1,x2-x1),0); o.scale.set(L+t*0.5, h, t); o.updateMatrix(); im.setMatrixAt(i,o.matrix); });
    g.add(im);
  }
  addSegs(fd.walls.concat(fd.cols), wallMat, 1.1, 0.07);
  addSegs(fd.glass, glassMat, 1.1, 0.05);
  scene.add(g); groups[F] = g;
});

function errOf(r, v){ if(!r || r[v]==null) return null; return (r[v]-r.ref)/r.ref*100; }
function colorFor(u){
  if(mode==='code') return u.code ? CODE_COL[u.code] : NONE_COL;
  if(!u.code) return NONE_COL;
  const e = errOf(u.room, mode); if(e===null) return pale(CODE_COL[u.code]||NEUTRAL);
  const a=Math.abs(e); return a<=5?ERR_COL.good : a<=10?ERR_COL.warn : ERR_COL.bad;
}
function legend(){
  if(mode==='code') legendEl.innerHTML = Object.entries(CODE_COL).map(([k,v])=>`<span><i style="background:${v}"></i>${k}</span>`).join('')+`<span><i style="background:${NONE_COL}"></i>코드 없음</span>`;
  else legendEl.innerHTML = `<span><i style="background:${ERR_COL.good}"></i>±5% 이내</span><span><i style="background:${ERR_COL.warn}"></i>±10% 이내</span><span><i style="background:${ERR_COL.bad}"></i>10% 넘음</span><span><i style="background:${pale('#46B05A')}"></i>검증 세트 밖(옅은 코드색)</span>`;
}
function recolor(){ cellMeshes.forEach(m => m.material.color.set(colorFor(m.userData))); legend(); }

function layout(){
  FLOORS.forEach(F => { const g=groups[F]; const on = floorSel==='ALL' || floorSel===F; g.visible = on; g.position.y = floorSel==='ALL' ? LEVEL_ALL[F] : 0; });
}
function fitView(animate=true){
  const target = new THREE.Vector3(0, floorSel==='ALL'?6.5:0, 0);
  const pos = floorSel==='ALL' ? new THREE.Vector3(-27, 31, 33) : new THREE.Vector3(-15, 23, 20);
  if(animate) tweenCam(pos, target, 900); else { camera.position.copy(pos); controls.target.copy(target); }
}
let tw=null;
function tweenCam(pos, target, ms){ tw={p0:camera.position.clone(), t0:controls.target.clone(), p1:pos.clone(), t1:target.clone(), s:performance.now(), ms}; }
function setTabs(id, attr, val){ document.querySelectorAll(`#${id} button`).forEach(b=>b.setAttribute('aria-selected', b.dataset[attr]===val?'true':'false')); }
document.querySelectorAll('#m3floor button').forEach(b=>b.addEventListener('click',()=>{ floorSel=b.dataset.f; setTabs('m3floor','f',floorSel); layout(); fitView(); }));
document.querySelectorAll('#m3mode button').forEach(b=>b.addEventListener('click',()=>{ mode=b.dataset.m; setTabs('m3mode','m',mode); recolor(); }));

const fmt = v => v==null?'—':v.toFixed(2)+'㎡';
const chipE = e => { if(e===null) return ''; const a=Math.abs(e); const c=a<=5?'c-good':a<=10?'c-warn':'c-bad'; return `<span class="chip ${c}">${e>0?'+':''}${e.toFixed(1)}%</span>`; };
const esc = s => String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
let picked=null;
function select(m){
  if(picked) picked.material.emissive.setHex(0x000000);
  picked=m; if(!m) return; m.material.emissive.setHex(0x333333);
  const u=m.userData, r=u.room;
  const area = r ? r.ref : (u.kind==='closed' ? u.region : u.cell);
  let html = `<span class="label">${u.floor} · ${esc(u.name)} · ${u.code||'코드 없음'}</span><span>실측 <b class="mono">${fmt(area)}</b>${u.kind==='open_group'?' <span style="color:var(--muted)">(열린 공간, 기하 분할 값)</span>':''}</span>`;
  if(r) html += `<span>AI v2 <b class="mono">${fmt(r.v2)}</b> ${chipE(errOf(r,'v2'))} → v6 <b class="mono">${fmt(r.v6)}</b> ${chipE(errOf(r,'v6'))}</span><span class="mono">${esc((r.basis||'').slice(0,420))}${(r.basis||'').length>420?' …':''}</span>`;
  else if(u.code) html += `<span style="color:var(--muted)">검증 세트 밖의 구역입니다. 벽으로 닫혀 있지 않거나 경계 해석이 갈리는 곳이라 채점에서 뺐습니다.</span>`;
  else html += `<span style="color:var(--muted)">마감 코드 태그가 없는 실입니다. 내역서와의 차이 후보입니다.</span>`;
  info.innerHTML = html;
}
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(); let down=null;
function hit(ev){ const r=canvas.getBoundingClientRect(); mouse.set(((ev.clientX-r.left)/r.width)*2-1, -((ev.clientY-r.top)/r.height)*2+1); ray.setFromCamera(mouse,camera);
  const vis = cellMeshes.filter(m=>m.parent.visible); const h=ray.intersectObjects(vis,false); return h.length?h[0].object:null; }
canvas.addEventListener('pointerdown', e=>{ down=[e.clientX,e.clientY]; stopTour(); });
canvas.addEventListener('pointerup', e=>{ if(down && Math.hypot(e.clientX-down[0],e.clientY-down[1])<5){ const m=hit(e); if(m) select(m);} down=null; });
canvas.addEventListener('pointermove', e=>{ if(e.pointerType!=='mouse') return; const m=hit(e); if(m){ const r=stage.getBoundingClientRect(); tip.hidden=false; tip.style.left=(e.clientX-r.left)+'px'; tip.style.top=(e.clientY-r.top)+'px'; tip.textContent=`${m.userData.floor} ${m.userData.name}`; } else tip.hidden=true; });
canvas.addEventListener('pointerleave', ()=>tip.hidden=true);

function resize(){ const w=stage.clientWidth, h=stage.clientHeight; renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix(); }
new ResizeObserver(resize).observe(stage); resize();

// 자동 둘러보기 (영상 녹화용)
const tourBtn=document.getElementById('m3tour'); let tour=null;
const find=(F,n)=>cellMeshes.find(m=>m.userData.floor===F && norm(m.userData.name)===norm(n));
function centerOf(m){ scene.updateMatrixWorld(true); const b=new THREE.Box3().setFromObject(m); return b.getCenter(new THREE.Vector3()); }
const STEPS=[
  {t:0, run:()=>{ floorSel='ALL'; setTabs('m3floor','f','ALL'); layout(); mode='code'; setTabs('m3mode','m','code'); recolor(); select(null); info.innerHTML='<span class="label">1 · 도면 벡터에서 세운 3개 층</span><span>벽·창호·기둥은 PDF의 CAD 레이어, 바닥 색은 마감 코드입니다.</span>'; tweenCam(new THREE.Vector3(-27,31,33), new THREE.Vector3(0,6.5,0), 1200); }},
  {t:4200, run:()=>{ tweenCam(new THREE.Vector3(28,30,32), new THREE.Vector3(0,6.5,0), 3500); }},
  {t:8000, run:()=>{ mode='v2'; setTabs('m3mode','m','v2'); recolor(); info.innerHTML='<span class="label">2 · AI v2 오차</span><span>표 형식만 지시했을 때. 빨강은 실측보다 10% 넘게 틀린 방입니다.</span>'; }},
  {t:11500, run:()=>{ mode='v6'; setTabs('m3mode','m','v6'); recolor(); info.innerHTML='<span class="label">3 · AI v6 오차</span><span>고해상도 판독 + 실무 규칙 + 오차 패턴 규칙 후. 방 단위 평균 오차 16.3% → 4.3%.</span>'; }},
  {t:15000, run:()=>{ floorSel='2F'; setTabs('m3floor','f','2F'); layout(); const m=find('2F','소회의실-2'); const c=m?centerOf(m):new THREE.Vector3(); tweenCam(new THREE.Vector3(c.x-3, c.y+10, c.z+10), c, 1800); }},
  {t:17200, run:()=>{ mode='v2'; setTabs('m3mode','m','v2'); recolor(); const m=find('2F','소회의실-1'); if(m) select(m); }},
  {t:20500, run:()=>{ mode='v6'; setTabs('m3mode','m','v6'); recolor(); const m=find('2F','소회의실-1'); if(m) select(m); }},
  {t:24500, run:()=>{ floorSel='ALL'; setTabs('m3floor','f','ALL'); layout(); mode='code'; setTabs('m3mode','m','code'); recolor(); fitView(); info.innerHTML='<span class="label">끝</span><span>방을 직접 눌러 근거를 확인해 보세요.</span>'; }},
  {t:26500, run:()=>stopTour()},
];
function startTour(){ tour={s:performance.now(), i:0}; tourBtn.setAttribute('aria-pressed','true'); tourBtn.textContent='둘러보기 멈춤'; }
function stopTour(){ if(!tour) return; tour=null; tourBtn.setAttribute('aria-pressed','false'); tourBtn.textContent='자동 둘러보기'; }
tourBtn.addEventListener('click',()=> tour?stopTour():startTour());
window.__m3tour = startTour;

function loop(now){
  if(tour){ while(tour && tour.i<STEPS.length && now-tour.s>=STEPS[tour.i].t){ const st=STEPS[tour.i]; tour.i++; st.run(); } }
  if(tw){ const k=Math.min(1,(now-tw.s)/tw.ms), e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2; camera.position.lerpVectors(tw.p0,tw.p1,e); controls.target.lerpVectors(tw.t0,tw.t1,e); if(k>=1) tw=null; }
  controls.update(); renderer.render(scene,camera); requestAnimationFrame(loop);
}
layout(); recolor(); fitView(false); requestAnimationFrame(loop);
})();
