async function cancelStream(){
  const streamId = S.activeStreamId;
  if(!streamId) return;
  try{
    await fetch(new URL(`/api/chat/cancel?stream_id=${encodeURIComponent(streamId)}`,location.origin).href,{credentials:'include'});
    const btn=$('btnCancel');if(btn)btn.style.display='none';
    setStatus('Cancelling…');
  }catch(e){setStatus('Cancel failed: '+e.message);}
}

// ── Mobile navigation ──────────────────────────────────────────────────────
function toggleMobileSidebar(){
  const sidebar=document.querySelector('.sidebar');
  const overlay=$('mobileOverlay');
  if(!sidebar)return;
  const isOpen=sidebar.classList.contains('mobile-open');
  if(isOpen){closeMobileSidebar();}
  else{sidebar.classList.add('mobile-open');if(overlay)overlay.classList.add('visible');}
}
function closeMobileSidebar(){
  const sidebar=document.querySelector('.sidebar');
  const overlay=$('mobileOverlay');
  if(sidebar)sidebar.classList.remove('mobile-open');
  if(overlay)overlay.classList.remove('visible');
}
function toggleMobileFiles(){
  const panel=document.querySelector('.rightpanel');
  if(!panel)return;
  panel.classList.toggle('mobile-open');
}
function mobileSwitchPanel(name){
  // Switch the panel content view
  switchPanel(name);
  // For non-chat panels (tasks, skills, memory, spaces), open the sidebar
  // so the panel is visible. For 'chat', the content is in the main area —
  // just close the sidebar so the chat view is unobstructed.
  if(name==='chat'){
    closeMobileSidebar();
  } else {
    const sidebar=document.querySelector('.sidebar');
    const overlay=$('mobileOverlay');
    if(sidebar){
      sidebar.classList.add('mobile-open');
      if(overlay)overlay.classList.add('visible');
    }
  }
  // Update bottom nav active state
  document.querySelectorAll('.mobile-nav-btn').forEach(btn=>{
    btn.classList.toggle('active',btn.dataset.panel===name);
  });
}

$('btnSend').onclick=()=>{if(window._micActive)_stopMic();send();};
$('btnAttach').onclick=()=>$('fileInput').click();

// ── Voice input (Web Speech API) ─────────────────────────────────────────
(function(){
  const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SpeechRecognition) return; // Browser unsupported — mic button stays hidden

  const btn=$('btnMic');
  const status=$('micStatus');
  const ta=$('msg');
  btn.style.display=''; // Show button — browser supports speech

  const recognition=new SpeechRecognition();
  recognition.continuous=false;
  recognition.interimResults=true;
  recognition.lang=(navigator.language||'ko-KR');

  let _finalText='';
  let _prefix='';

  function _setRecording(on){
    window._micActive=on;
    btn.classList.toggle('recording',on);
    status.style.display=on?'':'none';
    if(!on){ _finalText=''; _prefix=''; }
  }

  recognition.onstart=()=>{ _finalText=''; };

  recognition.onresult=(event)=>{
    let interim='';
    let final=_finalText;
    for(let i=event.resultIndex;i<event.results.length;i++){
      const t=event.results[i][0].transcript;
      if(event.results[i].isFinal){ final+=t; _finalText=final; }
      else{ interim+=t; }
    }
    // Append to whatever was already in the textarea before mic started
    ta.value=_prefix+(final||interim);
    autoResize();
  };

  recognition.onend=()=>{
    // Commit: prefix + final transcription; trim trailing space if prefix was non-empty
    const committed=_finalText
      ? (_prefix&&!_prefix.endsWith(' ')&&!_prefix.endsWith('\n')
          ? _prefix+' '+_finalText.trimStart()
          : _prefix+_finalText)
      : ta.value; // no speech detected — leave whatever is there
    _setRecording(false);
    ta.value=committed;
    autoResize();
  };

  recognition.onerror=(event)=>{
    _setRecording(false);
    const msgs={
      'not-allowed':'마이크 권한이 차단되었습니다. 브라우저 사이트 권한에서 마이크를 허용해 주세요.',
      'service-not-allowed':'이 브라우저/환경에서 음성 인식 서비스 사용이 차단되었습니다.',
      'no-speech':'음성이 감지되지 않았습니다. 다시 시도해 주세요.',
      'audio-capture':'마이크를 찾지 못했습니다. 입력 장치를 확인해 주세요.',
      'network':'음성 인식 서비스를 사용할 수 없습니다. 네트워크 또는 브라우저 지원 여부를 확인해 주세요.',
    };
    showToast(msgs[event.error]||('음성 입력 오류: '+event.error));
  };

  function _stopMic(){
    if(window._micActive){ recognition.stop(); }
  }
  window._stopMic=_stopMic; // expose for send-guard above

  btn.onclick=()=>{
    if(window._micActive){
      recognition.stop();
      // _setRecording(false) will be called by onend
    } else {
      _finalText='';
      // Snapshot existing textarea content so we append rather than replace
      _prefix=ta.value;
      showToast(`음성 인식 시작 (${recognition.lang})`);
      recognition.start();
      _setRecording(true);
    }
  };
})();
window._micActive=window._micActive||false;
$('fileInput').onchange=e=>{addFiles(Array.from(e.target.files));e.target.value='';};
$('btnNewChat').onclick=async()=>{await newSession();await renderSessionList();$('msg').focus();};
$('btnDownload').onclick=()=>{
  if(!S.session)return;
  const blob=new Blob([transcript()],{type:'text/markdown'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=`hermes-${S.session.session_id}.md`;a.click();URL.revokeObjectURL(a.href);
};
$('btnExportJSON').onclick=()=>{
  if(!S.session)return;
  const url=`/api/session/export?session_id=${encodeURIComponent(S.session.session_id)}`;
  const a=document.createElement('a');a.href=url;
  a.download=`hermes-${S.session.session_id}.json`;a.click();
};
$('btnImportJSON').onclick=()=>$('importFileInput').click();
$('importFileInput').onchange=async(e)=>{
  const file=e.target.files[0];
  if(!file)return;
  e.target.value='';
  try{
    const text=await file.text();
    const data=JSON.parse(text);
    const res=await api('/api/session/import',{method:'POST',body:JSON.stringify(data)});
    if(res.ok&&res.session){
      await loadSession(res.session.session_id);
      await renderSessionList();
      showToast('Session imported');
    }
  }catch(err){
    showToast('Import failed: '+(err.message||'Invalid JSON'));
  }
};
// btnRefreshFiles is now panel-icon-btn in header (see HTML)
function clearPreview(){
  const pa=$('previewArea');if(pa)pa.classList.remove('visible');
  const pi=$('previewImg');if(pi){pi.onerror=null;pi.src='';}
  const pm=$('previewMd');if(pm)pm.innerHTML='';
  const pc=$('previewCode');if(pc)pc.textContent='';
  const pp=$('previewPathText');if(pp)pp.textContent='';
  const ft=$('fileTree');if(ft)ft.style.display='';
  const we=$('workspaceEmpty');if(we)we.style.display='flex';
  _previewCurrentPath='';_previewCurrentMode='';_previewDirty=false;
}
$('btnClearPreview').onclick=clearPreview;
// workspacePath click handler removed -- use topbar workspace chip dropdown instead
$('modelSelect').onchange=async()=>{
  if(!S.session)return;
  const selectedModel=$('modelSelect').value;
  localStorage.setItem('hermes-webui-model', selectedModel);
  await api('/api/session/update',{method:'POST',body:JSON.stringify({session_id:S.session.session_id,workspace:S.session.workspace,model:selectedModel})});
  S.session.model=selectedModel;syncTopbar();
};
$('msg').addEventListener('input',()=>{
  autoResize();
  updateSendBtn();
  const text=$('msg').value;
  if(text.startsWith('/')&&text.indexOf('\n')===-1){
    const prefix=text.slice(1);
    const matches=getMatchingCommands(prefix);
    if(matches.length)showCmdDropdown(matches); else hideCmdDropdown();
  } else {
    hideCmdDropdown();
  }
});
let _msgComposing=false;
$('msg').addEventListener('compositionstart',()=>{ _msgComposing=true; });
$('msg').addEventListener('compositionend',()=>{ _msgComposing=false; });
$('msg').addEventListener('keydown',e=>{
  if(e.isComposing||_msgComposing)return;
  // Autocomplete navigation when dropdown is open
  const dd=$('cmdDropdown');
  const dropdownOpen=dd&&dd.classList.contains('open');
  if(dropdownOpen){
    if(e.key==='ArrowUp'){e.preventDefault();navigateCmdDropdown(-1);return;}
    if(e.key==='ArrowDown'){e.preventDefault();navigateCmdDropdown(1);return;}
    if(e.key==='Tab'){e.preventDefault();selectCmdDropdownItem();return;}
    if(e.key==='Escape'){e.preventDefault();hideCmdDropdown();return;}
    if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();selectCmdDropdownItem();return;}
  }
  // Send key: respect user preference
  if(e.key==='Enter'){
    if(window._sendKey==='ctrl+enter'){
      if(e.ctrlKey||e.metaKey){e.preventDefault();send();}
    } else {
      if(!e.shiftKey){e.preventDefault();send();}
    }
  }
});
// B14: Cmd/Ctrl+K creates a new chat from anywhere
document.addEventListener('keydown',async e=>{
  if((e.metaKey||e.ctrlKey)&&e.key==='k'){
    e.preventDefault();
    if(!S.busy){await newSession();await renderSessionList();$('msg').focus();}
  }
  if(e.key==='Escape'){
    // Close settings overlay if open
    const settingsOverlay=$('settingsOverlay');
    if(settingsOverlay&&settingsOverlay.style.display!=='none'){_closeSettingsPanel();return;}
    // Close workspace dropdown
    closeWsDropdown();
    // Clear session search
    const ss=$('sessionSearch');
    if(ss&&ss.value){ss.value='';filterSessions();}
    // Cancel any active message edit
    const editArea=document.querySelector('.msg-edit-area');
    if(editArea){
      const bar=editArea.closest('.msg-row')&&editArea.closest('.msg-row').querySelector('.msg-edit-bar');
      if(bar){const cancel=bar.querySelector('.msg-edit-cancel');if(cancel)cancel.click();}
    }
  }
});
$('msg').addEventListener('paste',e=>{
  const items=Array.from(e.clipboardData?.items||[]);
  const imageItems=items.filter(i=>i.type.startsWith('image/'));
  if(!imageItems.length)return;
  e.preventDefault();
  const files=imageItems.map(i=>{
    const blob=i.getAsFile();
    const ext=i.type.split('/')[1]||'png';
    return new File([blob],`screenshot-${Date.now()}.${ext}`,{type:i.type});
  });
  addFiles(files);
  setStatus(`Image pasted: ${files.map(f=>f.name).join(', ')}`);
});
document.querySelectorAll('.suggestion').forEach(btn=>{
  btn.onclick=()=>{$('msg').value=btn.dataset.msg;send();};
});

const QUICK_ACTION_TEMPLATES={
  'workspace-summary':'현재 작업공간을 빠르게 훑고, 중요한 파일/폴더와 지금 바로 할 수 있는 작업 5가지를 요약해줘.',
  'note-draft':'이 대화나 현재 작업을 바탕으로 바로 저장 가능한 Obsidian 노트 초안을 만들어줘. frontmatter와 읽기 좋은 구조를 포함해줘.',
  'blog-post':'이 주제를 바탕으로 블로그 포스트 또는 /posting 초안 방향을 잡아줘. 핵심 논지, 구조, 시각화 아이디어까지 제안해줘.',
  'schedule-task':'이 작업을 나중에 자동으로 반복하려면 어떤 cron job 이 좋은지 제안하고, 바로 만들 수 있게 초안을 작성해줘.'
};
document.querySelectorAll('.quick-action').forEach(btn=>{
  btn.onclick=()=>{
    const key=btn.dataset.template;
    const text=QUICK_ACTION_TEMPLATES[key]||'';
    if(!text)return;
    $('msg').value=text;
    autoResize();
    $('msg').focus();
    showToast('빠른 작업 템플릿을 입력창에 넣었습니다');
  };
});

function buildArtifactPrompt(kind){
  const title=(S.session&&S.session.title)||'현재 작업';
  const workspace=(S.session&&S.session.workspace)||'';
  const lead=`현재 세션 제목은 "${title}"이고 작업공간은 "${workspace}" 입니다. `;
  if(kind==='obsidian-note'){
    return lead + '지금까지의 대화와 작업 맥락을 바탕으로, 바로 저장 가능한 Obsidian 노트 초안을 만들어줘. frontmatter, 가독성 높은 구조, 필요하면 시각화 아이디어도 포함해줘.';
  }
  if(kind==='share-note'){
    return lead + '지금까지의 내용을 바탕으로 ShareNote 생성까지 염두에 둔 공개 가능한 노트 초안을 만들어줘. Obsidian 스타일, frontmatter, 요약, 핵심 포인트, 공유용 구조를 포함해줘.';
  }
  if(kind==='posting-brief'){
    return lead + '이 대화 내용을 /posting 으로 발전시키기 위한 브리프를 만들어줘. 주제, 핵심 메시지, 독자, 섹션 구조, 필요한 자료, 시각화 1~2개 아이디어를 정리해줘.';
  }
  if(kind==='schedule-followup'){
    return lead + '이 작업을 후속 자동화로 이어가려면 어떤 예약작업이 좋은지 제안하고, cron 자연어 요청 한 줄과 구체 프롬프트 초안을 함께 만들어줘.';
  }
  return '';
}
document.querySelectorAll('.artifact-action').forEach(btn=>{
  if(btn.dataset.workflow) return;
  btn.onclick=()=>{
    const kind=btn.dataset.artifact;
    const text=buildArtifactPrompt(kind);
    if(!text)return;
    $('msg').value=text;
    autoResize();
    $('msg').focus();
    showToast('아티팩트 작업 프롬프트를 입력창에 넣었습니다');
  };
});

function buildWorkflowPrompt(kind){
  const title=(S.session&&S.session.title)||'현재 작업';
  const workspace=(S.session&&S.session.workspace)||'';
  const lead=`현재 세션 제목은 "${title}"이고 작업공간은 "${workspace}" 입니다. `;
  if(kind==='generate-note'){
    return lead + '지금까지의 대화를 바탕으로 저장 가능한 정리 노트를 만들어줘. 가능하면 Obsidian 친화적으로 작성하고, 저장 전 핵심 구조를 먼저 제안해줘.';
  }
  if(kind==='generate-posting'){
    return lead + '이 대화를 /posting 가능한 브리프로 전환해줘. 핵심 주제, 메시지, 독자, 구조, 시각화 아이디어를 정리해줘.';
  }
  if(kind==='save-memory'){
    return lead + '현재 대화에서 장기적으로 유용한 사용자 선호, 환경 정보, workflow 규칙이 있다면 memory 또는 user profile 에 저장해줘. 저장한 항목도 짧게 요약해줘.';
  }
  if(kind==='telegram-handoff'){
    return lead + '현재 작업을 텔레그램 구찌에서도 바로 이어갈 수 있도록 handoff summary 를 만들어줘. 핵심 맥락, 다음 액션, 기억해둘 사항을 간단히 정리하고 memory 저장이 필요하면 함께 반영해줘.';
  }
  return '';
}

document.querySelectorAll('.artifact-action[data-workflow]').forEach(btn=>{
  btn.onclick=async()=>{
    const kind=btn.dataset.workflow;
    const text=buildWorkflowPrompt(kind);
    if(!text)return;
    if(S.busy){showToast('현재 작업이 끝난 뒤 다시 시도해 주세요');return;}
    $('msg').value=text;
    autoResize();
    $('msg').focus();
    showToast('워크플로우 작업을 바로 실행합니다');
    await send();
  };
});

function _artifactStoreKey(){
  const sid=S.session&&S.session.session_id;
  return sid?`hermes-webui-artifacts:${sid}`:'hermes-webui-artifacts:global';
}
function _loadArtifacts(){
  try{return JSON.parse(localStorage.getItem(_artifactStoreKey())||'[]');}catch(e){return [];}
}
function _saveArtifacts(items){
  localStorage.setItem(_artifactStoreKey(), JSON.stringify(items.slice(0,20)));
}
function registerArtifact(item){
  const items=_loadArtifacts().filter(x=>x.path!==item.path);
  items.unshift({...item,created_at:new Date().toISOString()});
  _saveArtifacts(items);
  renderArtifactList();
}
function removeArtifactRecord(path){
  const items=_loadArtifacts().filter(x=>x.path!==path);
  _saveArtifacts(items);
  renderArtifactList();
}
function buildArtifactActionPrompt(path, action){
  if(action==='share') return `워크스페이스의 ${path} 파일을 기준으로 ShareNote 공유용으로 다듬어줘. 공유 전 체크포인트와 ShareNote 링크 생성 흐름도 함께 안내해줘.`;
  if(action==='telegram') return `워크스페이스의 ${path} 파일을 기준으로 텔레그램 handoff summary 를 만들어줘. 텔레그램 구찌에서 바로 이어갈 수 있게 핵심 맥락과 다음 액션을 정리해줘.`;
  if(action==='memory') return `워크스페이스의 ${path} 파일과 현재 대화를 참고해서 장기적으로 기억할 만한 선호/환경/workflow 규칙이 있으면 memory 또는 user profile 에 저장해줘.`;
  return '';
}
async function runArtifactWorkflow(path, action){
  if(!path)return;
  const text=buildArtifactActionPrompt(path, action);
  if(!text)return;
  if(S.busy){showToast('현재 작업이 끝난 뒤 다시 시도해 주세요');return;}
  $('msg').value=text;
  autoResize();
  $('msg').focus();
  showToast('아티팩트 워크플로우를 실행합니다');
  await send();
}
function renderArtifactList(){
  const wraps=[$('artifactList'), $('artifactListSidebar')].filter(Boolean);
  if(!wraps.length)return;
  const items=_loadArtifacts();
  if(!items.length){
    wraps.forEach(w=>w.innerHTML='<div class="artifact-empty">아직 아티팩트가 없습니다. 아티팩트 추가 또는 AI로 만들기 버튼을 눌러 시작해보세요.</div>');
    return;
  }
  const html=items.map(item=>`<div class="artifact-item"><div class="artifact-item-main"><div class="artifact-item-title">${esc(item.name||item.path)}</div><div class="artifact-item-meta">${esc(item.type||'artifact')} · ${esc(item.path||'')}</div></div><div class="artifact-item-actions"><button class="artifact-mini-btn" onclick="openArtifactPath('${esc(item.path)}')">열기</button><button class="artifact-mini-btn" onclick="runArtifactWorkflow('${esc(item.path)}','share')">Share</button><button class="artifact-mini-btn" onclick="runArtifactWorkflow('${esc(item.path)}','telegram')">Telegram</button><button class="artifact-mini-btn" onclick="runArtifactWorkflow('${esc(item.path)}','memory')">Memory</button><button class="artifact-mini-btn" onclick="deleteArtifactPath('${esc(item.path)}','${esc(item.name||item.path)}')">삭제</button></div></div>`).join('');
  wraps.forEach(w=>w.innerHTML=html);
}
async function openArtifactPath(path){
  if(!path||!S.session)return;
  await loadDir('.');
  openFile(path);
}
async function deleteArtifactPath(path,name){
  if(!path||!S.session)return;
  await deleteWorkspaceFile(path,name||path);
  removeArtifactRecord(path);
}
function promptAiArtifact(){
  const text='현재 대화를 바탕으로 바로 작업할 수 있는 아티팩트 초안을 하나 만들어줘. 적절한 아티팩트 유형(note, posting brief, memo, research brief)을 추천하고, 파일명 제안과 함께 저장 가능한 초안을 작성해줘.';
  $('msg').value=text; autoResize(); $('msg').focus(); showToast('AI 아티팩트 생성 프롬프트를 입력창에 넣었습니다');
}
function openArtifactModal(){
  const overlay=$('artifactModalOverlay');
  if(!overlay)return;
  $('artifactModalError').style.display='none';
  $('artifactType').value='note';
  $('artifactName').value='';
  $('artifactSeed').value='';
  $('artifactUseAi').checked=false;
  overlay.style.display='flex';
  $('artifactName').focus();
}
function closeArtifactModal(){
  const overlay=$('artifactModalOverlay');
  if(overlay) overlay.style.display='none';
}
async function submitArtifactModal(){
  const type=($('artifactType').value||'note').trim();
  const name=($('artifactName').value||'').trim();
  const seed=($('artifactSeed').value||'').trim();
  const useAi=$('artifactUseAi').checked;
  const err=$('artifactModalError');
  err.style.display='none';
  if(!name){err.textContent='파일 이름이 필요합니다';err.style.display='';return;}
  const cleanName=name.endsWith('.md')?name:name+'.md';
  const relPath=S.currentDir==='.'?cleanName:(S.currentDir+'/'+cleanName);
  const templateMap={
    note:'---\ntitle: '+cleanName.replace(/\.md$/,'')+'\ncreated: '+new Date().toISOString().slice(0,10)+'\n---\n\n# '+cleanName.replace(/\.md$/,'')+'\n\n'+(seed?seed+'\n\n':'')+'- 요약\n- 핵심 포인트\n',
    posting:'# Posting Brief\n\n'+(seed?seed+'\n\n':'')+'## Topic\n\n## Audience\n\n## Key message\n',
    brief:'# Brief\n\n'+(seed?seed+'\n\n':'')+'## Goal\n\n## Inputs\n\n## Next steps\n',
    memo:'# Memo\n\n'+(seed?seed+'\n\n':'')+'- Idea\n- Context\n- Follow-up\n',
    research:'# Research Brief\n\n'+(seed?seed+'\n\n':'')+'## Question\n\n## Hypothesis\n\n## Sources\n'
  };
  try{
    await api('/api/file/create',{method:'POST',body:JSON.stringify({session_id:S.session.session_id,path:relPath,content:templateMap[type]||templateMap.note})});
    registerArtifact({name:cleanName,path:relPath,type});
    closeArtifactModal();
    showToast('아티팩트를 만들었습니다');
    await loadDir(S.currentDir);
    openFile(relPath);
    if(useAi){
      $('msg').value=`방금 생성한 ${cleanName} 파일을 바탕으로 ${type} 아티팩트를 더 완성해줘. 사용자 메모: ${seed||'없음'}`;
      autoResize();
      $('msg').focus();
    }
  }catch(e){err.textContent='생성 실패: '+e.message;err.style.display='';}
}
if($('btnAddArtifact')) $('btnAddArtifact').onclick=openArtifactModal;
if($('btnAddArtifactSidebar')) $('btnAddArtifactSidebar').onclick=openArtifactModal;
if($('btnAiArtifact')) $('btnAiArtifact').onclick=promptAiArtifact;
if($('btnAiArtifactSidebar')) $('btnAiArtifactSidebar').onclick=promptAiArtifact;
if($('btnArtifactCancel')) $('btnArtifactCancel').onclick=closeArtifactModal;
if($('btnCloseArtifactModal')) $('btnCloseArtifactModal').onclick=closeArtifactModal;
if($('btnArtifactCreate')) $('btnArtifactCreate').onclick=submitArtifactModal;
renderArtifactList();

function _setupPackStoreKey(){
  return 'hermes-webui-setup-pack-history';
}
function _loadSetupPackHistory(){
  try{return JSON.parse(localStorage.getItem(_setupPackStoreKey())||'[]');}catch(e){return [];}
}
function _saveSetupPackHistory(items){
  localStorage.setItem(_setupPackStoreKey(), JSON.stringify(items.slice(0,12)));
}
function recordSetupPackRun(pack){
  const items=_loadSetupPackHistory().filter(x=>x.pack!==pack);
  items.unshift({pack, ran_at:new Date().toISOString(), status:'running'});
  _saveSetupPackHistory(items);
  renderSetupPackHistory();
}
function updateSetupPackStatus(pack, status){
  const items=_loadSetupPackHistory();
  const idx=items.findIndex(x=>x.pack===pack);
  if(idx>=0){
    items[idx].status=status;
    items[idx].updated_at=new Date().toISOString();
    _saveSetupPackHistory(items);
    renderSetupPackHistory();
  }
}
function renderSetupPackHistory(){
  const wraps=[$('setupPackHistory'), $('setupPackHistorySidebar')].filter(Boolean);
  if(!wraps.length)return;
  const items=_loadSetupPackHistory();
  if(!items.length){
    wraps.forEach(w=>w.innerHTML='<div class="artifact-empty">아직 실행한 setup pack 이 없습니다.</div>');
    return;
  }
  const html=items.map(item=>`<div class="artifact-item"><div class="artifact-item-main"><div class="artifact-item-title">${esc(item.pack)}</div><div class="artifact-item-meta">${esc(item.status)} · ${esc(item.updated_at||item.ran_at)}</div></div><div class="artifact-item-actions"><button class="artifact-mini-btn" onclick="rerunSetupPack('${esc(item.pack)}')">재실행</button><button class="artifact-mini-btn" onclick="updateSetupPackStatus('${esc(item.pack)}','done')">완료</button><button class="artifact-mini-btn" onclick="updateSetupPackStatus('${esc(item.pack)}','needs-approval')">승인필요</button></div></div>`).join('');
  wraps.forEach(w=>w.innerHTML=html);
}

const SETUP_PACK_TEMPLATES={
  'obsidian-starter':'내 환경에서 Obsidian Starter Pack 을 설치해줘. Obsidian vault 확인, note 작성에 필요한 기본 도구/스킬 점검, Obsidian 친화 markdown workflow 확인까지 진행해줘. 무엇을 설치/설정했는지 마지막에 요약해줘.',
  'sharenote-telegram':'ShareNote + Telegram Publishing Pack 을 설치해줘. Obsidian ShareNote 플러그인/Advanced URI/공유 링크 생성 도우미/텔레그램 전달 흐름을 점검하고 설정해줘. 환경별 승인 필요한 단계가 있으면 설명하고 진행해줘.',
  'obsidian-power':'Obsidian Power Workflow Pack 을 설치해줘. Obsidian note 작성, posting, ShareNote 생성, Telegram handoff 까지 이어지는 범용 워크플로우를 점검/설정하고 최종 사용법을 정리해줘.',
  'memory-sync':'Memory Sync Pack 을 점검해줘. WebUI, CLI, Telegram 간에 이어서 작업하기 좋은 memory/workflow 규칙을 확인하고, 필요한 공유 기억/핸드오프 사용법을 정리해줘.',
  'telegram-onboarding':'Hermes Telegram onboarding pack 을 실행해줘. 텔레그램에서 Hermes 봇을 아직 써보지 않은 사용자도 쉽게 시작할 수 있도록 필요한 설정, 계정 연결, 기본 사용 흐름, 점검 항목을 단계별로 정리하고 가능한 부분은 직접 세팅해줘. 마지막에는 초보자용 사용 가이드를 짧게 써줘.'
};
document.querySelectorAll('.setup-pack').forEach(btn=>{
  btn.onclick=async()=>{
    const key=btn.dataset.pack;
    const text=SETUP_PACK_TEMPLATES[key]||'';
    if(!text)return;
    if(S.busy){showToast('현재 작업이 끝난 뒤 다시 시도해 주세요');return;}
    recordSetupPackRun(key);
    $('msg').value=text;
    autoResize();
    $('msg').focus();
    showToast('설치 팩 작업을 바로 실행합니다');
    await send();
  };
});
async function rerunSetupPack(key){
  const text=SETUP_PACK_TEMPLATES[key]||'';
  if(!text)return;
  if(S.busy){showToast('현재 작업이 끝난 뒤 다시 시도해 주세요');return;}
  recordSetupPackRun(key);
  $('msg').value=text;
  autoResize();
  $('msg').focus();
  showToast('설치 팩을 다시 실행합니다');
  await send();
}

function runPreflight(kind){
  const artifacts=_loadArtifacts();
  const modalOpen=$('artifactModalOverlay') && $('artifactModalOverlay').style.display!=='none';
  const artifactName=($('artifactName')&&$('artifactName').value||'').trim();
  const artifactType=($('artifactType')&&$('artifactType').value||'note').trim();
  const cronSchedule=($('cronFormSchedule')&&$('cronFormSchedule').value||'').trim();
  const cronPrompt=($('cronFormPrompt')&&$('cronFormPrompt').value||'').trim();
  const cronVibe=($('cronFormVibe')&&$('cronFormVibe').value||'').trim();

  if(kind==='note'){
    const details=[]; let status='pass';
    if(modalOpen && !artifactName){status='warn'; details.push('아티팩트 모달에서 파일 이름이 비어 있습니다');}
    if(modalOpen && artifactType!=='note'){status='warn'; details.push('현재 모달 유형이 Note가 아닙니다');}
    if(!artifacts.some(a => String(a.type||'').includes('note'))){status=status==='pass'?'warn':status; details.push('최근 note 아티팩트가 없습니다');}
    details.push('frontmatter/Obsidian 구조 확인 권장');
    return {title:'Note Check',status,details};
  }
  if(kind==='posting'){
    const details=[]; let status='warn';
    if(artifacts.some(a => String(a.type||'').includes('posting'))){status='pass'; details.push('최근 posting 계열 아티팩트가 있습니다');}
    else details.push('posting 아티팩트가 아직 없습니다');
    details.push('독자/핵심 메시지/시각화 1~2개 아이디어 포함 권장');
    details.push('최종 ShareNote/배포 경로 확인 권장');
    return {title:'Posting Check',status,details};
  }
  if(kind==='cron'){
    const details=[]; let status='warn';
    if(cronSchedule) details.push(`스케줄 입력됨: ${cronSchedule}`); else details.push('스케줄 입력이 없습니다');
    if(cronPrompt || cronVibe) details.push('작업 설명이 입력되어 있습니다'); else details.push('작업 설명이 부족합니다');
    if(cronSchedule && (cronPrompt || cronVibe)) status='pass';
    if(!cronSchedule && !(cronPrompt || cronVibe)) status='fail';
    details.push('deliver 채널과 self-contained prompt 확인 권장');
    return {title:'Cron Check',status,details};
  }
  return {title:'Check',status:'fail',details:['검사 항목을 찾을 수 없습니다']};
}
function renderPreflightResult(kind){
  const wraps=[$('preflightList'), $('preflightListSidebar')].filter(Boolean);
  if(!wraps.length)return;
  const res=runPreflight(kind);
  const klass=res.status==='pass'?'preflight-pass':res.status==='warn'?'preflight-warn':'preflight-fail';
  const html=`<div class="artifact-item ${klass}"><div class="artifact-item-main"><div class="artifact-item-title">${esc(res.title)}</div><div class="artifact-item-meta">${esc(res.status.toUpperCase())}</div><div class="artifact-item-meta">${res.details.map(esc).join(' · ')}</div></div></div>`;
  wraps.forEach(w=>w.innerHTML=html);
}
document.querySelectorAll('.preflight-run').forEach(btn=>{
  btn.onclick=()=>{
    renderPreflightResult(btn.dataset.preflight);
    showToast('Preflight 점검 결과를 업데이트했습니다');
  };
});
renderSetupPackHistory();

async function loadPersonalizationCard(){
  const card=$('personalizationCard');
  if(!card)return;
  try{
    const data=await api('/api/memory');
    const memory=(data.memory||'').trim();
    const user=(data.user||'').trim();
    if(!memory && !user){
      card.style.display='none';
      return;
    }
    const summarize = (text)=> text.split(/\n+/).map(s=>s.replace(/^[-*#\s]+/,'').trim()).filter(Boolean).slice(0,3);
    const userPoints=summarize(user);
    const memPoints=summarize(memory);
    const bullets=[...userPoints.slice(0,2), ...memPoints.slice(0,2)].slice(0,4);
    card.innerHTML=`<div class="personalization-card-title">개인화 미리보기</div><div class="personalization-card-body">이 WebUI 는 사용자의 Hermes memory 와 profile 을 읽어 점점 더 개인화됩니다.${bullets.length?'<ul>'+bullets.map(b=>`<li>${esc(b)}</li>`).join('')+'</ul>':''}</div>`;
    card.style.display='block';
  }catch(e){
    card.style.display='none';
  }
}

async function applyBotName(){
  try{
    const settings=await api('/api/settings');
    const name=(settings.bot_name||'Hermes').trim() || 'Hermes';
    const titleEl=$('topbarTitle');
    if(titleEl && (!$('msgInner') || !$('msgInner').children.length)) titleEl.textContent=name;
    document.querySelectorAll('.assistant-name-dynamic').forEach(el=>el.textContent=name);
    const msgBox=$('msg');
    if(msgBox) msgBox.placeholder=`${name}에게 메시지 보내기…`;
    const meta=$('topbarMeta');
    if(meta && (!$('msgInner') || !$('msgInner').children.length)) meta.textContent=`${name}와 새 대화를 시작해보세요`;
  }catch(e){}
}

// Boot: restore last session or start fresh
// ── Resizable panels ──────────────────────────────────────────────────────
(function(){
  const SIDEBAR_MIN=180, SIDEBAR_MAX=420;
  const PANEL_MIN=180,   PANEL_MAX=500;

  function initResize(handleId, targetEl, edge, minW, maxW, storageKey){
    const handle = $(handleId);
    if(!handle || !targetEl) return;

    // Restore saved width
    const saved = localStorage.getItem(storageKey);
    if(saved) targetEl.style.width = saved + 'px';

    let startX=0, startW=0;

    handle.addEventListener('mousedown', e=>{
      e.preventDefault();
      startX = e.clientX;
      startW = targetEl.getBoundingClientRect().width;
      handle.classList.add('dragging');
      document.body.classList.add('resizing');

      const onMove = ev=>{
        const delta = edge==='right' ? ev.clientX - startX : startX - ev.clientX;
        const newW = Math.min(maxW, Math.max(minW, startW + delta));
        targetEl.style.width = newW + 'px';
      };
      const onUp = ()=>{
        handle.classList.remove('dragging');
        document.body.classList.remove('resizing');
        localStorage.setItem(storageKey, parseInt(targetEl.style.width));
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
      };
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  // Run after DOM ready (called from boot)
  window._initResizePanels = function(){
    const sidebar    = document.querySelector('.sidebar');
    const rightpanel = document.querySelector('.rightpanel');
    initResize('sidebarResize',    sidebar,    'right', SIDEBAR_MIN, SIDEBAR_MAX, 'hermes-sidebar-w');
    initResize('rightpanelResize', rightpanel, 'left',  PANEL_MIN,   PANEL_MAX,   'hermes-panel-w');
  };
})();

(async()=>{
  // Load send key preference
  try{const s=await api('/api/settings');window._sendKey=s.send_key||'enter';window._showTokenUsage=!!s.show_token_usage;window._showCliSessions=!!s.show_cli_sessions;const _theme=s.theme||'dark';document.documentElement.dataset.theme=_theme;localStorage.setItem('hermes-theme',_theme);}catch(e){window._sendKey='enter';window._showTokenUsage=false;window._showCliSessions=false;}
  // Fetch active profile
  try{const p=await api('/api/profile/active');S.activeProfile=p.name||'default';}catch(e){S.activeProfile='default';}
  // Update profile chip label immediately
  const profileLabel=$('profileChipLabel');
  if(profileLabel) profileLabel.textContent=S.activeProfile||'default';
  // Fetch available models from server and populate dropdown dynamically
  await populateModelDropdown();
  await applyBotName();
  await loadPersonalizationCard();
  // Restore last-used model preference
  const savedModel=localStorage.getItem('hermes-webui-model');
  if(savedModel && $('modelSelect')){
    $('modelSelect').value=savedModel;
    // If the value didn't take (model not in list), clear the bad pref
    if($('modelSelect').value!==savedModel) localStorage.removeItem('hermes-webui-model');
  }
  // Pre-load workspace list so sidebar name is correct from first render
  await loadWorkspaceList();
  _initResizePanels();
  const saved=localStorage.getItem('hermes-webui-session');
  if(saved){
    try{await loadSession(saved);await renderSessionList();await checkInflightOnBoot(saved);return;}
    catch(e){localStorage.removeItem('hermes-webui-session');}
  }
  // no saved session - show empty state, wait for user to hit +
  $('emptyState').style.display='';
  await renderSessionList();
})();

