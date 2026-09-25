#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""由 teachers.json + 工作簿1.csv(导师名单) 生成单文件浏览页 teachers/index.html。

- 侧栏置顶「★ 导师名单」板块，仅展示 CSV 中的导师（按 CSV 顺序）
- 其余视图里，导师卡片带 ★ 标记
"""

import csv
import io
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
SRC_DIR = os.path.join(BASE_DIR, "src")
JSON_PATH = os.path.join(SRC_DIR, "teachers.json")
CSV_PATH = os.path.join(BASE_DIR, "工作簿1.csv")
HTML_PATH = os.path.join(BASE_DIR, "index.html")

ALIAS = {"俞献邦": "俞猷邦", "姜微": "姜薇"}


def norm(s):
    s = (s or "").strip()
    s = re.sub(r"^实验室人员简介[—\-–]*", "", s)
    s = s.replace("老师", "")
    s = s.replace("•", "·").replace("．", "·").replace("・", "·")
    return re.sub(r"\s+", "", s)


def load_mentor_names():
    if not os.path.exists(CSV_PATH):
        return []
    raw = open(CSV_PATH, "rb").read()
    text = None
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return []
    rows = list(csv.reader(io.StringIO(text)))
    names = []
    for i, r in enumerate(rows):
        if not r or not r[0].strip():
            continue
        c = r[0].strip()
        if i == 0 and ("姓名" in c or c in ("名字", "教师", "老师")):
            continue
        names.append(c)
    return names


def build_mentors(data, names):
    for r in data:
        r["_n"] = norm(r["name"])
        r["mentor"] = False
    mentors, mentor_set = [], set()
    for cn in names:
        c = norm(ALIAS.get(cn, cn))
        exact = [j for j, r in enumerate(data) if r["_n"] == c]
        if exact:
            for j in exact:
                mentor_set.add(j)
            j = max(exact, key=lambda k: len(data[k].get("text") or ""))
        else:
            cand = [
                j for j, r in enumerate(data)
                if r["_n"] and (r["_n"] in c or c in r["_n"]) and j not in mentor_set
            ]
            if len(cand) == 1:
                j = cand[0]
                mentor_set.add(j)
            else:
                j = None
        mentors.append({"n": cn, "i": j})
    for j in mentor_set:
        data[j]["mentor"] = True
    return mentors


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>学院队伍 · 教师简历</title>
<style>
:root{
  --bg:#f5f6f8; --panel:#fff; --line:#e6e8eb; --ink:#1f2329; --muted:#7a828c;
  --brand:#c0392b; --brand2:#e04b37; --chip:#f0f1f3; --gold:#b8860b;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{background:var(--bg);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
a{color:var(--brand);text-decoration:none}
header{position:sticky;top:0;z-index:20;background:var(--panel);border-bottom:1px solid var(--line);
  padding:14px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
header h1{font-size:18px;margin:0;white-space:nowrap}
header h1 b{color:var(--brand)}
.count{color:var(--muted);font-size:13px}
.search{margin-left:auto;position:relative}
.search input{width:260px;max-width:60vw;padding:8px 12px 8px 32px;border:1px solid var(--line);
  border-radius:20px;font-size:14px;outline:none;background:var(--bg)}
.search input:focus{border-color:var(--brand2);background:#fff}
.search::before{content:"\1F50D";position:absolute;left:11px;top:50%;transform:translateY(-50%);
  font-size:13px;opacity:.55}
.layout{display:flex;align-items:flex-start;gap:0}
aside{width:220px;flex:0 0 220px;position:sticky;top:57px;height:calc(100vh - 57px);overflow:auto;
  padding:14px 10px;border-right:1px solid var(--line);background:var(--panel)}
aside .sec{display:flex;justify-content:space-between;gap:8px;padding:7px 10px;border-radius:8px;
  cursor:pointer;font-size:14px;color:#333}
aside .sec:hover{background:var(--chip)}
aside .sec.on{background:var(--brand);color:#fff}
aside .sec.on .n{color:#fff}
aside .sec .n{color:var(--muted);font-size:12px}
aside .sec.pin{font-weight:700;color:var(--gold);border:1px solid #f0e2bd;background:#fdf8ec;margin-bottom:6px}
aside .sec.pin.on{background:var(--gold);color:#fff;border-color:var(--gold)}
aside hr{border:0;border-top:1px solid var(--line);margin:8px 4px}
main{flex:1;padding:18px;min-width:0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;
  cursor:pointer;transition:.15s;display:flex;flex-direction:column;position:relative}
.card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.09);border-color:#d5d8dc}
.card.pin-on{border-color:#e8d49a}
.photo{height:230px;background:linear-gradient(135deg,#eceff1,#dfe3e7);position:relative;overflow:hidden}
.photo img{width:100%;height:100%;object-fit:cover;object-position:center 22%;display:block}
.ini{width:100%;height:100%;display:flex;align-items:center;justify-content:center;
  font-size:52px;color:#fff;background:linear-gradient(135deg,#c0392b,#e07a5f)}
.ini.gray{background:linear-gradient(135deg,#9aa4ad,#c3cbd2)}
.star{position:absolute;top:8px;right:8px;width:26px;height:26px;border-radius:50%;
  background:var(--gold);color:#fff;display:flex;align-items:center;justify-content:center;
  font-size:14px;box-shadow:0 1px 5px rgba(0,0,0,.28)}
.card .body{padding:11px 13px 14px}
.card .name{font-size:16px;font-weight:600}
.chip{display:inline-block;margin-top:6px;padding:2px 8px;border-radius:20px;background:var(--chip);
  color:#5b636d;font-size:12px}
.card .date{margin-top:6px;color:var(--muted);font-size:12px}
.empty{padding:60px;text-align:center;color:var(--muted)}
.mask{position:fixed;inset:0;background:rgba(20,24,30,.55);display:none;z-index:50;
  align-items:center;justify-content:center;padding:20px}
.mask.on{display:flex}
.modal{background:#fff;border-radius:14px;max-width:820px;width:100%;max-height:88vh;overflow:auto;
  display:flex;flex-direction:column;position:relative}
.modal .mhead{display:flex;gap:18px;padding:20px 22px 0}
.modal .mpic{width:150px;height:190px;flex:0 0 150px;border-radius:10px;overflow:hidden;background:#eee}
.modal .mpic img{width:100%;height:100%;object-fit:cover;object-position:center 20%}
.modal h2{margin:0 0 6px;font-size:22px}
.modal .meta{color:var(--muted);font-size:13px;margin-bottom:10px}
.modal .txt{padding:6px 22px 24px;white-space:pre-wrap;font-size:15px;text-indent:2em}
.modal .txt p{margin:0 0 10px}
.x{position:absolute;right:16px;top:12px;font-size:26px;color:#9aa0a6;cursor:pointer;border:0;background:none}
.modal .bar{display:flex;justify-content:space-between;padding:4px 22px 18px;gap:10px}
.btn{border:1px solid var(--line);background:#fff;border-radius:8px;padding:7px 14px;cursor:pointer;font-size:14px}
.btn:hover{background:var(--chip)}
.btn[disabled]{opacity:.4;cursor:default}
.note{padding:20px 22px 26px;color:var(--muted)}
@media(max-width:720px){
  .layout{display:block}
  aside{position:static;width:auto;height:auto;flex:none;display:flex;gap:8px;overflow-x:auto;
    padding:10px 12px;border-right:0;border-bottom:1px solid var(--line);white-space:nowrap}
  aside .sec{flex:0 0 auto}
  aside .sec.pin{margin-bottom:0}
  aside hr{display:none}
  main{padding:14px}
  .grid{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:12px}
  .photo{height:180px}
  .modal .mhead{flex-direction:column}
  .modal .mpic{width:120px;height:150px;flex:0 0 auto}
}
</style>
</head>
<body>
<header>
  <h1>信息技术与工程学院 · <b>教师简历</b></h1>
  <span class="count" id="count"></span>
  <div class="search"><input id="q" type="search" placeholder="搜索姓名 / 简介关键词…"></div>
</header>
<div class="layout">
  <aside id="side"></aside>
  <main><div class="grid" id="grid"></div><div class="empty" id="empty" style="display:none">没有匹配的老师</div></main>
</div>

<div class="mask" id="mask"><div class="modal" id="modal"></div></div>

<script>
const DATA = __DATA__;
const MENTORS = __MENTORS__;
const MENTOR_CNT = __MENTOR_CNT__;
const PH_CNT = __PH_CNT__;
const IMG_BASE = "src/";
let curSec = "__m__", curQ = "", shown = [];

const side = document.getElementById('side');
const grid = document.getElementById('grid');
const countEl = document.getElementById('count');

function esc(t){return String(t??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function sections(){
  const m = new Map();
  DATA.forEach(r => m.set(r.section, (m.get(r.section)||0)+1));
  return [...m.entries()];
}
function buildSide(){
  let h = `<div class="sec pin ${curSec==='__m__'?'on':''}" data-s="__m__">★ 导师名单<span class="n">${MENTOR_CNT}</span></div><hr>`;
  h += `<div class="sec ${curSec===''?'on':''}" data-s="">全部<span class="n">${DATA.length}</span></div>`;
  for(const [s,n] of sections())
    h += `<div class="sec ${curSec===s?'on':''}" data-s="${esc(s)}">${esc(s)}<span class="n">${n}</span></div>`;
  side.innerHTML = h;
  side.querySelectorAll('.sec').forEach(el=>el.onclick=()=>{curSec=el.dataset.s;buildSide();render();});
}
function card(rec){
  const r = rec.r;
  const img = r.images && r.images[0];
  const star = r.mentor ? `<div class="star">★</div>` : ``;
  const pic = img
    ? `<img loading="lazy" src="${esc(IMG_BASE+img)}" onerror="this.parentNode.innerHTML='<div class=&quot;ini&quot;>${esc((r.name||'?')[0])}</div>'">`
    : `<div class="ini">${esc((r.name||'?')[0])}</div>`;
  return `<div class="card ${r.mentor?'pin-on':''}" data-i="${rec.i}">
    <div class="photo">${pic}${star}</div>
    <div class="body"><div class="name">${esc(r.name)}</div>
      <span class="chip">${esc(r.section)}</span>
      <div class="date">${esc(r.date||'')}</div></div></div>`;
}
function phCard(ph){
  return `<div class="card" data-i="${ph.i}">
    <div class="photo"><div class="ini gray">${esc((ph.n||'?')[0])}</div></div>
    <div class="body"><div class="name">${esc(ph.n)}</div>
      <span class="chip">导师</span>
      <div class="date">官网暂未收录简介</div></div></div>`;
}
function matchesRec(r){
  if(!curQ) return true;
  const q = curQ.toLowerCase();
  return (r.name||'').toLowerCase().includes(q) || (r.text||'').toLowerCase().includes(q);
}
function render(){
  if(curSec === '__m__'){
    const list = [];
    MENTORS.forEach((m, idx)=>{
      if(m.i !== null){
        const r = DATA[m.i];
        if(matchesRec(r)) list.push({type:'rec', r, i:list.length});
      }else if(!curQ || m.n.toLowerCase().includes(curQ.toLowerCase())){
        list.push({type:'ph', n:m.n});
      }
    });
    list.forEach((x,i)=>x.i=i);
    shown = list;
    countEl.textContent = `导师 ${MENTOR_CNT} 名 · 已收录简介 ${MENTOR_CNT-PH_CNT} 条 · 当前 ${shown.length}`;
    document.getElementById('empty').style.display = shown.length? 'none':'block';
    grid.innerHTML = shown.map(x=> x.type==='rec'? card(x) : phCard(x)).join('');
  }else{
    const recs = DATA.filter(r => (!curSec || r.section===curSec) && matchesRec(r));
    shown = recs.map((r,i)=>({type:'rec', r, i}));
    countEl.textContent = `共 ${shown.length} 位`;
    document.getElementById('empty').style.display = shown.length? 'none':'block';
    grid.innerHTML = shown.map(card).join('');
  }
  grid.querySelectorAll('.card').forEach(el=>el.onclick=()=>openModal(+el.dataset.i));
}

const mask = document.getElementById('mask'), modal = document.getElementById('modal');
let curIdx = -1;
function openModal(i){
  curIdx = i; const it = shown[i];
  if(it.type === 'ph'){
    modal.innerHTML = `<button class="x" onclick="closeModal()">×</button>
      <div class="mhead"><div class="mpic"><div class="ini gray" style="font-size:46px">${esc((it.n||'?')[0])}</div></div>
      <div><h2>${esc(it.n)}</h2><div class="meta">导师</div></div></div>
      <div class="note">该导师在学院官网暂未收录个人简介，可尝试站内搜索。</div>
      <div class="bar"><button class="btn" ${i<=0?'disabled':''} onclick="openModal(${i-1})">← 上一位</button>
      <button class="btn" ${i>=shown.length-1?'disabled':''} onclick="openModal(${i+1})">下一位 →</button></div>`;
    mask.classList.add('on'); modal.scrollTop = 0; return;
  }
  const r = it.r;
  const img = r.images && r.images[0];
  const pic = img ? `<img src="${esc(IMG_BASE+img)}">` : `<div class="ini">${esc((r.name||'?')[0])}</div>`;
  const paras = (r.text||'（无简介正文）').split(/\n{2,}/).map(p=>`<p>${esc(p)}</p>`).join('');
  modal.innerHTML = `
    <button class="x" onclick="closeModal()">×</button>
    <div class="mhead"><div class="mpic">${pic}</div>
      <div><h2>${r.mentor?'★ ':''}${esc(r.name)}</h2>
        <div class="meta">${esc(r.section)} · ${esc(r.date||'')}</div>
        <a class="btn" href="${esc(r.url)}" target="_blank" rel="noopener">查看官网原文 ↗</a></div></div>
    <div class="txt">${paras}</div>
    <div class="bar"><button class="btn" ${i<=0?'disabled':''} onclick="openModal(${i-1})">← 上一位</button>
      <button class="btn" ${i>=shown.length-1?'disabled':''} onclick="openModal(${i+1})">下一位 →</button></div>`;
  mask.classList.add('on'); modal.scrollTop = 0;
}
function closeModal(){mask.classList.remove('on');}
mask.onclick = e=>{if(e.target===mask) closeModal();};
document.addEventListener('keydown', e=>{
  if(!mask.classList.contains('on')) return;
  if(e.key==='Escape') closeModal();
  if(e.key==='ArrowLeft' && curIdx>0) openModal(curIdx-1);
  if(e.key==='ArrowRight' && curIdx<shown.length-1) openModal(curIdx+1);
});
document.getElementById('q').oninput = e=>{curQ=e.target.value.trim(); render();};

buildSide(); render();
</script>
</body>
</html>
"""


def main():
    if not os.path.exists(JSON_PATH):
        print(f"[错误] 找不到 {JSON_PATH}，请先运行 crawl_teachers.py")
        return 1
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    names = load_mentor_names()
    mentors = build_mentors(data, names)
    ph_cnt = sum(1 for m in mentors if m["i"] is None)

    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    mpayload = json.dumps(mentors, ensure_ascii=False).replace("</", "<\\/")
    html = (
        TEMPLATE.replace("__DATA__", payload)
        .replace("__MENTORS__", mpayload)
        .replace("__MENTOR_CNT__", str(len(mentors)))
        .replace("__PH_CNT__", str(ph_cnt))
    )
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[完成] 教师 {len(data)} 位 | 导师 {len(mentors)} 名（已收录 {len(mentors)-ph_cnt}，缺简介 {ph_cnt}）")
    print(f"       -> {HTML_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
