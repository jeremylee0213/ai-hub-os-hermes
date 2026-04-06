// ── Slash commands ──────────────────────────────────────────────────────────
// Built-in commands intercepted before send(). Each command runs locally
// (no round-trip to the agent) and shows feedback via toast or local message.

const COMMANDS=[
  {name:'help',      desc:'사용 가능한 명령어 보기',                 fn:cmdHelp},
  {name:'clear',     desc:'현재 대화 메시지 지우기',                 fn:cmdClear},
  {name:'compact',   desc:'대화 컨텍스트 압축하기',                 fn:cmdCompact},
  {name:'model',     desc:'모델 전환 (예: /model gpt-4o)',         fn:cmdModel,     arg:'model_name'},
  {name:'workspace', desc:'이름으로 작업공간 전환',                 fn:cmdWorkspace, arg:'name'},
  {name:'new',       desc:'새 대화 세션 시작',                      fn:cmdNew},
  {name:'usage',     desc:'토큰 사용량 표시 켜기/끄기',             fn:cmdUsage},
  {name:'theme',     desc:'테마 전환 (dark/light/slate/solarized/monokai/nord)', fn:cmdTheme, arg:'name'},
];

function parseCommand(text){
  if(!text.startsWith('/'))return null;
  const parts=text.slice(1).split(/\s+/);
  const name=parts[0].toLowerCase();
  const args=parts.slice(1).join(' ').trim();
  return {name,args};
}

function executeCommand(text){
  const parsed=parseCommand(text);
  if(!parsed)return false;
  const cmd=COMMANDS.find(c=>c.name===parsed.name);
  if(!cmd)return false;
  cmd.fn(parsed.args);
  return true;
}

function getMatchingCommands(prefix){
  const q=prefix.toLowerCase();
  return COMMANDS.filter(c=>c.name.startsWith(q));
}

// ── Command handlers ────────────────────────────────────────────────────────

function cmdHelp(){
  const lines=COMMANDS.map(c=>{
    const usage=c.arg?` <${c.arg}>`:'';
    return `  /${c.name}${usage} — ${c.desc}`;
  });
  const msg={role:'assistant',content:'**사용 가능한 명령어:**\n'+lines.join('\n')};
  S.messages.push(msg);
  renderMessages();
  showToast('/ 를 입력하면 명령어를 볼 수 있습니다');
}

function cmdClear(){
  if(!S.session)return;
  S.messages=[];S.toolCalls=[];
  clearLiveToolCards();
  renderMessages();
  $('emptyState').style.display='';
  showToast('대화를 지웠습니다');
}

async function cmdModel(args){
  if(!args){showToast('사용법: /model <name>');return;}
  const sel=$('modelSelect');
  if(!sel)return;
  const q=args.toLowerCase();
  // Fuzzy match: find first option whose label or value contains the query
  let match=null;
  for(const opt of sel.options){
    if(opt.value.toLowerCase().includes(q)||opt.textContent.toLowerCase().includes(q)){
      match=opt.value;break;
    }
  }
  if(!match){showToast(`"${args}"에 맞는 모델이 없습니다`);return;}
  sel.value=match;
  await sel.onchange();
  showToast(`모델을 전환했습니다: ${match}`);
}

async function cmdWorkspace(args){
  if(!args){showToast('사용법: /workspace <name>');return;}
  try{
    const data=await api('/api/workspaces');
    const q=args.toLowerCase();
    const ws=(data.workspaces||[]).find(w=>
      (w.name||'').toLowerCase().includes(q)||w.path.toLowerCase().includes(q)
    );
    if(!ws){showToast(`"${args}"에 맞는 작업공간이 없습니다`);return;}
    if(!S.session)return;
    await api('/api/session/update',{method:'POST',body:JSON.stringify({
      session_id:S.session.session_id,workspace:ws.path,model:S.session.model
    })});
    S.session.workspace=ws.path;
    syncTopbar();await loadDir('.');
    showToast(`작업공간을 전환했습니다: ${ws.name||ws.path}`);
  }catch(e){showToast('작업공간 전환 실패: '+e.message);}
}

async function cmdNew(){
  await newSession();
  await renderSessionList();
  $('msg').focus();
  showToast('새 세션을 만들었습니다');
}

function cmdCompact(){
  // Send as a regular message to the agent -- the agent's run_conversation
  // preflight will detect the high token count and trigger _compress_context.
  // We send a user message so it appears in the conversation.
  $('msg').value='Please compress and summarize the conversation context to free up space.';
  send();
  showToast('컨텍스트 압축을 요청했습니다...');
}

async function cmdUsage(){
  const next=!window._showTokenUsage;
  window._showTokenUsage=next;
  try{
    await api('/api/settings',{method:'POST',body:JSON.stringify({show_token_usage:next})});
  }catch(e){}
  // Update the settings checkbox if the panel is open
  const cb=$('settingsShowTokenUsage');
  if(cb) cb.checked=next;
  renderMessages();
  showToast('토큰 사용량 표시 '+(next?'켜짐':'꺼짐'));
}

async function cmdTheme(args){
  const themes=['dark','light','slate','solarized','monokai','nord','cherry-blossom','neo-brutalism','gucci'];
  if(!args||!themes.includes(args.toLowerCase())){
    showToast('사용법: /theme '+themes.join('|'));
    return;
  }
  const t=args.toLowerCase();
  document.documentElement.dataset.theme=t;
  localStorage.setItem('hermes-theme',t);
  try{await api('/api/settings',{method:'POST',body:JSON.stringify({theme:t})});}catch(e){}
  // Update settings dropdown if panel is open
  const sel=$('settingsTheme');
  if(sel)sel.value=t;
  showToast('테마: '+t);
}

// ── Autocomplete dropdown ───────────────────────────────────────────────────

let _cmdSelectedIdx=-1;

function showCmdDropdown(matches){
  const dd=$('cmdDropdown');
  if(!dd)return;
  dd.innerHTML='';
  _cmdSelectedIdx=-1;
  for(let i=0;i<matches.length;i++){
    const c=matches[i];
    const el=document.createElement('div');
    el.className='cmd-item';
    el.dataset.idx=i;
    const usage=c.arg?` <span class="cmd-item-arg">${esc(c.arg)}</span>`:'';
    el.innerHTML=`<div class="cmd-item-name">/${esc(c.name)}${usage}</div><div class="cmd-item-desc">${esc(c.desc)}</div>`;
    el.onmousedown=(e)=>{
      e.preventDefault();
      $('msg').value='/'+c.name+(c.arg?' ':'');
      hideCmdDropdown();
      $('msg').focus();
    };
    dd.appendChild(el);
  }
  dd.classList.add('open');
}

function hideCmdDropdown(){
  const dd=$('cmdDropdown');
  if(dd)dd.classList.remove('open');
  _cmdSelectedIdx=-1;
}

function navigateCmdDropdown(dir){
  const dd=$('cmdDropdown');
  if(!dd)return;
  const items=dd.querySelectorAll('.cmd-item');
  if(!items.length)return;
  items.forEach(el=>el.classList.remove('selected'));
  _cmdSelectedIdx+=dir;
  if(_cmdSelectedIdx<0)_cmdSelectedIdx=items.length-1;
  if(_cmdSelectedIdx>=items.length)_cmdSelectedIdx=0;
  items[_cmdSelectedIdx].classList.add('selected');
}

function selectCmdDropdownItem(){
  const dd=$('cmdDropdown');
  if(!dd)return;
  const items=dd.querySelectorAll('.cmd-item');
  if(_cmdSelectedIdx>=0&&_cmdSelectedIdx<items.length){
    items[_cmdSelectedIdx].onmousedown({preventDefault:()=>{}});
  } else if(items.length===1){
    items[0].onmousedown({preventDefault:()=>{}});
  }
  hideCmdDropdown();
}
