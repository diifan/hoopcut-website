/* Progressive enhancement: every tool and link is present in the original HTML. */
(()=>{
  const input=document.getElementById('tool-search');
  if(!input)return;
  document.getElementById('tool-search-controls').hidden=false;
  const cards=[...document.querySelectorAll('[data-tool]')];
  const groups=[...document.querySelectorAll('[data-tool-group]')];
  const links=[...document.querySelectorAll('[data-filter]')];
  let category='all';
  function apply(){
    const words=input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    let count=0;
    cards.forEach(card=>{
      const text=card.textContent.toLowerCase();
      const match=(category==='all'||card.dataset.group===category)&&words.every(word=>text.includes(word));
      card.hidden=!match;if(match)count++;
    });
    groups.forEach(group=>{group.hidden=![...group.querySelectorAll('[data-tool]')].some(card=>!card.hidden);});
    links.forEach(link=>{if(link.dataset.filter===category)link.setAttribute('aria-current','true');else link.removeAttribute('aria-current');});
    document.getElementById('tool-count').textContent=`${count} ${count===1?'tool':'tools'}${input.value.trim()?' matching your search':' to make your own'}.`;
    document.getElementById('no-tools').hidden=count!==0;
  }
  input.addEventListener('input',apply);
  links.forEach(link=>link.addEventListener('click',event=>{event.preventDefault();category=link.dataset.filter;apply();}));
  document.getElementById('clear-search').addEventListener('click',()=>{input.value='';category='all';apply();input.focus();});
})();
