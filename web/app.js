const $ = s => document.querySelector(s);
const names = {inbox:'收集箱', next_actions:'下一步行动', waiting_for:'等待跟进', projects:'项目', someday_maybe:'将来 / 也许', materials:'资料库', memories:'记忆'};
let category='inbox', records=[], editing=null, pendingAction='create', loading=false;
const el = (tag, text, className) => {const n=document.createElement(tag); if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;};
async function api(data){const r=await fetch('/api/records',data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{});const body=await r.json();if(!r.ok)throw new Error(body.error||'操作失败');return body;}
async function refresh(){if(loading)return;loading=true;try{const data=await api();records=data.records;$('#directory').textContent=data.directory;render();}catch(e){$('#status').textContent=e.message;}finally{loading=false;}}
function actionButton(text,fn,cls){const b=el('button',text,cls);b.type='button';b.onclick=fn;return b;}
function render(){
 $('#heading').textContent=names[category];$('#nav').replaceChildren();
 for(const [key,name] of Object.entries(names)){const b=actionButton(name,()=>{category=key;render();},key===category?'active':'');b.append(el('small',records.filter(r=>r.category===key&&!r.done).length));b.setAttribute('aria-current',key===category?'page':'false');$('#nav').append(b);}
 const query=$('#search').value.trim().toLowerCase();
 const items=records.filter(r=>r.category===category&&($('#show-done').checked||!r.done)&&JSON.stringify([r.title,r.raw,r.card,r.memory]).toLowerCase().includes(query));
 $('#status').textContent=`${items.length} 条记录`;$('#list').replaceChildren();
 if(!items.length){const empty=el('div',undefined,'empty');empty.append(el('strong',query?'没有找到匹配内容':'这里暂时没有记录'),el('span',query?'试试其他关键词，或切换分类。':'点击右上角新建，也可以通过对话收集。'));$('#list').append(empty);}
 for(const item of items){const row=el('article',undefined,'record'+(item.done?' done':''));const body=el('div',undefined,'body');body.append(el('h3',item.title));const card=item.card;body.append(el('p',card?[item.id,(card.tags||[]).join(' · '),card.summary||card.note?.slice(0,200)].filter(Boolean).join('\n'):item.raw.split('\n').slice(1).join('\n').trim()|| (item.done?'已完成':'未完成')));
 if(item.memory){body.querySelector('p').textContent=[item.id, (item.memory.tags||[]).join(' · '), '更新于 '+item.memory.updated_at, item.memory.source].filter(Boolean).join('\n');}
 body.append(attachmentLinks(item),relatedLinks(item));
 const actions=el('div',undefined,'actions');actions.append(actionButton(card?'查看 / 编辑':'编辑',()=>openEditor(item)));
 if(item.category==='inbox')actions.append(actionButton('整理',()=>openProcess(item)));
 if(!item.done&&['next_actions','waiting_for','projects','someday_maybe'].includes(item.category))actions.append(actionButton('完成',()=>mutate(item,'complete')));
 actions.append(actionButton('删除',()=>{if(confirm(item.memory?`删除这条记忆？历史记录会保留，可通过对话恢复。`:`删除「${item.title}」？记录将留存到 web-trash，附件会保留。`))mutate(item,'delete');},'danger'));row.append(body,actions);$('#list').append(row);}
}
async function mutate(item,action){try{await api({id:item.id,revision:item.revision,action});await refresh();}catch(e){$('#status').textContent=e.message;}}
function field(name,label,value='',type='text'){const l=el('label',label);l.htmlFor='field-'+name;const n=el(type==='textarea'?'textarea':'input');if(type!=='textarea')n.type=type;n.id='field-'+name;n.name=name;n.value=value;$('#fields').append(l,n);return n;}
function openEditor(item=null){editing=item;pendingAction=item?'update':'create';$('#fields').replaceChildren();$('#form-error').textContent='';$('#dialog-title').textContent=item?'编辑记录':`新建 · ${names[category]}`;
 if((item?.category||category)==='memories'){
  field('content','记住什么',item?.memory.content||'','textarea').required=true;field('tags','标签（逗号分隔）',(item?.memory.tags||[]).join(', '));field('source','来源 / 上下文（可选）',item?.memory.source||'');$('#fields').append(el('p','记录价格、数量、位置或习惯等小事实。保留“一般”“大约”等限定语，信息变化时可编辑。','hint'));
 }else if((item?.category||category)==='materials'){
  field('title','标题',item?.title||'').required=true;field('note','备注',item?.card.note||'','textarea');field('tags','标签（逗号分隔）',(item?.card.tags||[]).join(', '));
  if(!item)field('url','链接（可选）','','url');
  if(item){$('#fields').append(attachmentLinks(item));relatedPicker(item);const details=el('details');details.append(el('summary','原文、附件与整理信息'),el('pre',JSON.stringify(item.card,null,2)));$('#fields').append(details);const url=item.card.url;if(url&&/^https?:\/\//i.test(url)){const a=el('a','打开资料链接');a.href=url;a.target='_blank';a.rel='noopener noreferrer';$('#fields').append(a);}}
 }else if(item){field('raw','记录内容',item.raw.trimEnd(),'textarea').required=true;$('#fields').append(el('p','保留 Markdown 标记和编号，可修改正文及括号中的情境、日期等信息。','hint'));}
 else{field('content','任务内容').required=true;if(category==='next_actions'){field('context','情境（可选）','@任意');field('deadline','截止日期（可选）','','date');}}
 if(item)$('#fields').append(relatedLinks(item));
 $('#editor').showModal();
}
function openProcess(item){editing=item;pendingAction='process';$('#fields').replaceChildren();$('#form-error').textContent='';$('#dialog-title').textContent='整理收集箱';$('#fields').append(el('p',item.title,'hint'));const label=el('label','移至');label.htmlFor='target';const select=el('select');select.name='target';select.id='target';for(const key of ['next_actions','waiting_for','projects','someday_maybe','materials','memories']){const opt=el('option',names[key]);opt.value=key;select.append(opt);}$('#fields').append(label,select);$('#editor').showModal();}
$('#form').onsubmit=async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{const data=Object.fromEntries(new FormData(e.target));if(editing?.card&&pendingAction==='update')data.related_items=[...document.querySelectorAll('[name=related_items]:checked')].map(n=>n.value);await api({...data,action:pendingAction,category,id:editing?.id,revision:editing?.revision});$('#editor').close();await refresh();}catch(error){$('#form-error').textContent=error.message;}finally{button.disabled=false;}};
$('#create').onclick=()=>openEditor();$('#refresh').onclick=refresh;$('#search').oninput=render;$('#show-done').onchange=render;$('#close').onclick=$('#cancel').onclick=()=>$('#editor').close();window.addEventListener('focus',()=>{if(!$('#editor').open)refresh();});refresh();

function relatedLinks(item){
 const box=el('div',undefined,'relations');
 if(!item.card&&!item.number)return box;
 box.append(el('span',item.card?'关联任务':'关联资料','relation-label'));
 if(!item.related?.some(r=>r.linked)){box.append(el('span','暂无关联','hint'));return box;}
 for(const relation of item.related.filter(r=>r.linked)){
  const label=[relation.number,relation.title].filter(Boolean).join(' · ')+(relation.source?'（来源）':'');
  if(!relation.id){box.append(el('span',label,'hint'));continue;}
  box.append(actionButton(label,()=>{const target=records.find(r=>r.id===relation.id);if(!target)return;$('#editor').close();category=target.category;$('#search').value='';if(target.done)$('#show-done').checked=true;render();openEditor(target);},'relation-link'));
 }
 return box;
}
function relatedPicker(item){
 const group=el('fieldset',undefined,'relation-picker');group.append(el('legend','关联任务 / 项目'));
 const previous=item.card.related_items||[];
 const tasks=records.filter(r=>r.number);
 if(!tasks.length)group.append(el('p','先创建下一步行动、等待跟进或项目，即可在此关联。','hint'));
 for(const task of tasks){
  const label=el('label');const input=el('input');input.type='checkbox';input.name='related_items';input.value=task.number;input.checked=previous.includes(task.number);
  label.append(input,el('span',`${task.number} · ${task.title}${task.done?'（已完成）':''}`));group.append(label);
 }
 for(const number of previous.filter(n=>!tasks.some(t=>t.number===n))){const label=el('label');const input=el('input');input.type='checkbox';input.name='related_items';input.value=number;input.checked=true;label.append(input,el('span',number+' · 已归档或不在当前列表'));group.append(label);}
 group.append(el('p','勾选后保存，任务和资料两侧都会显示关联。取消关联不会删除任何任务、资料或历史来源证据。','hint'));
 $('#fields').append(group);
}

function attachmentLinks(item){
 const box=el('div',undefined,'attachments');
 if(!item.downloads?.length)return box;
 box.append(el('div',`附件 · ${item.downloads.length}`,'relation-label'));
 for(const file of item.downloads){
  const row=el('div',undefined,'attachment-row');
  const info=el('div');info.append(el('span',file.name,'attachment-name'));
  if(Number.isFinite(file.size))info.append(el('small',file.size<1024?`${file.size} B`:file.size<1048576?`${(file.size/1024).toFixed(1)} KB`:`${(file.size/1048576).toFixed(1)} MB`));
  row.append(info);
  if(file.available){const link=el('a','下载原文件');link.href=file.url;link.download=file.name;row.append(link);}
  else row.append(el('span','文件缺失','danger'));
  box.append(row);
 }
 return box;
}
