/* Local editors. Optional anonymous analytics never include editor contents. */
(() => {
  'use strict';
  const config = JSON.parse(document.getElementById('resource-data').textContent);
  const status = document.getElementById('editor-status');
  const table = document.getElementById('resource-table');
  const svg = document.querySelector('#graphic-preview svg');
  const buttons = document.querySelector('.js-tools');
  const initialSvg = svg?.outerHTML;
  let serial = table ? table.rows.length : 0;
  let started = false;
  const track = (name, data={}) => window.hoopcutTrack?.(name, {tool:config.slug,...data});
  const start = () => { if (!started) { started = true; track('tool_start'); } };
  document.getElementById('workspace').addEventListener('input', start);
  buttons.hidden = false;
  const message = text => { status.textContent = text; };
  function download(blob, suffix) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = config.slug + '.' + suffix;
    document.body.append(link); link.click(); link.remove();
    track('export_success', {format:suffix});
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  function rowValues() { return [...table.tBodies[0].rows].map(row => [...row.querySelectorAll('textarea')].map(input => input.value)); }
  function numeric(value) { return value.trim() === '' ? 0 : Number(value); }
  function calculate() {
    if (config.kind !== 'budget') return true;
    let total = 0, valid = true;
    rowValues().forEach((row, rowIndex) => {
      const vals = row.slice(1,4).map(numeric);
      vals.forEach((value,i) => {
        const input = table.tBodies[0].rows[rowIndex].querySelectorAll('textarea')[i+1];
        const ok = Number.isFinite(value) && value >= 0;
        input.setAttribute('aria-invalid', String(!ok));
        valid = valid && ok;
      });
      const line = vals[0]*vals[1]+vals[2];
      if (!Number.isFinite(line)) valid = false;
      else total += line;
    });
    valid = valid && Number.isFinite(total);
    document.getElementById('budget-total').textContent = valid ? `Estimated total: $${total.toFixed(2)} USD · quantity × unit cost + extras` : 'Check the highlighted costs: use non-negative numbers, without currency symbols.';
    return valid;
  }
  function makeRow(values) {
    const tr = document.createElement('tr'); serial += 1;
    config.columns.forEach((label,i) => {
      const td = document.createElement('td'), input = document.createElement('textarea');
      input.rows=2; input.maxLength=500; input.value=values?.[i] || '';
      input.setAttribute('aria-label', `Row ${serial}: ${label}`); td.append(input); tr.append(td);
    });
    const td = document.createElement('td'), remove = document.createElement('button');
    td.className='screen-only'; remove.type='button'; remove.dataset.remove=''; remove.textContent='Remove';
    remove.setAttribute('aria-label', `Remove row ${serial}`); td.append(remove); tr.append(td);
    return tr;
  }
  function fit(node) {
    node.removeAttribute('textLength'); node.removeAttribute('lengthAdjust');
    const base = Number(node.dataset.baseSize), limit = Number(node.dataset.max);
    node.setAttribute('font-size', base);
    const length = node.getComputedTextLength();
    if (length > limit) node.setAttribute('font-size', Math.max(10,base*limit/length));
  }
  function updateGraphic() {
    const current = document.querySelector('#graphic-preview svg');
    document.querySelectorAll('[data-field]').forEach(input => {
      const n=Number(input.dataset.field), node=current.querySelector(`#slot-${n}`);
      const prefix = n===1 && ['recruiting','table-card','memory'].includes(current.dataset.layout) ? '#' : '';
      node.textContent=prefix+input.value; fit(node);
    });
    current.querySelectorAll('[data-accent]').forEach(node => node.setAttribute(node.dataset.accent, document.getElementById('accent').value));
    current.querySelector('title').textContent = `${config.fields[0][0]}: ${document.querySelector('[data-field="0"]').value}`;
  }
  if (svg) {
    const layout = { 'basketball-recruiting-title-card':'recruiting','basketball-senior-night-table-card':'table-card','basketball-senior-memory-card':'memory' }[config.slug] || '';
    svg.dataset.layout=layout;
    document.querySelectorAll('[data-field], #accent').forEach(input => input.addEventListener('input', updateGraphic));
    updateGraphic();
  }
  if (table) {
    table.addEventListener('input',calculate);
    table.addEventListener('click', event => {
      if (!event.target.matches('[data-remove]')) return;
      const row=event.target.closest('tr'), next=row.nextElementSibling || row.previousElementSibling;
      if (table.tBodies[0].rows.length === 1) { message('Keep at least one row; clear its fields to start again.'); return; }
      row.remove(); calculate(); next?.querySelector('textarea')?.focus(); message('Row removed.');
    });
    document.getElementById('add-row').addEventListener('click',()=>{
      const row=makeRow(); table.tBodies[0].append(row); row.querySelector('textarea').focus(); calculate(); message('Blank row added.');
    });
    calculate();
  }
  document.getElementById('reset-resource').addEventListener('click',()=>{
    if (table) {
      table.tBodies[0].replaceChildren(...config.rows.map(makeRow)); calculate();
    } else {
      document.querySelectorAll('[data-field]').forEach(input=>{input.value=config.fields[Number(input.dataset.field)][1];});
      document.getElementById('accent').value='#ad4726'; updateGraphic();
    }
    message('Original fictional example restored.');
  });
  function printMirror() {
    const workspace=document.getElementById('workspace');
    workspace.querySelector('.print-output')?.remove();
    const out=document.createElement('div'); out.className='print-output';
    if (config.kind==='graphic') {
      out.append(document.querySelector('#graphic-preview svg').cloneNode(true));
    } else if (config.kind==='interview') {
      rowValues().forEach(row=>{
        const card=document.createElement('section'); card.className='print-prompt-card';
        row.forEach((value,i)=>{const p=document.createElement(i===1?'h3':'p');p.textContent=`${config.columns[i]}: ${value}`;card.append(p);});out.append(card);
      });
    } else {
      const clone=document.createElement('table');
      const caption=document.createElement('caption'); caption.textContent=document.title.replace(' | Hoopcut','');clone.append(caption);
      [config.columns,...rowValues()].forEach((row,j)=>{
        const tr=document.createElement('tr'); row.forEach(value=>{const cell=document.createElement(j?'td':'th');cell.textContent=value;tr.append(cell);});clone.append(tr);
      });out.append(clone);
      if(config.kind==='budget'){const p=document.createElement('p');p.textContent=document.getElementById('budget-total').textContent;out.append(p);}
    }
    workspace.append(out);
  }
  window.addEventListener('beforeprint',printMirror);
  document.getElementById('print-resource').addEventListener('click',()=>{
    if(!calculate()){message('Correct the budget inputs before printing.');return;}
    start(); track('print_click'); printMirror(); window.print();
  });
  document.querySelectorAll('[data-export]').forEach(button=>button.addEventListener('click',async()=>{
    start();
    try {
      const type=button.dataset.export;
      if(type==='csv') {
        if(!calculate()){message('Correct the budget inputs before downloading.');return;}
        let rows=[config.columns,...rowValues()];
        if(config.kind==='budget') {
          rows[0]=[...rows[0],'Line total (USD)'];
          rows=rows.map((r,i)=>i?[...r,(numeric(r[1])*numeric(r[2])+numeric(r[3])).toFixed(2)]:r);
        }
        const safe=value=>{let v=String(value); if(/^[\s]*[=+@-]/.test(v))v="'"+v; return '"'+v.replaceAll('"','""')+'"';};
        download(new Blob(['\uFEFF'+rows.map(row=>row.map(safe).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),'csv');
      } else {
        updateGraphic();
        const current=document.querySelector('#graphic-preview svg').cloneNode(true);
        current.removeAttribute('role');current.removeAttribute('aria-label');
        const xml=new XMLSerializer().serializeToString(current);
        const blob=new Blob([xml],{type:'image/svg+xml;charset=utf-8'});
        if(type==='svg') download(blob,'svg');
        else {
          const image=new Image(), url=URL.createObjectURL(blob);
          try {
            await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=url;});
            const canvas=document.createElement('canvas');canvas.width=Number(current.getAttribute('width'));canvas.height=Number(current.getAttribute('height'));
            canvas.getContext('2d').drawImage(image,0,0);
            const png=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
            if(!png)throw Error('PNG export unavailable');download(png,'png');
          } finally {URL.revokeObjectURL(url);}
        }
      }
      message('Download prepared. Open the file and check your details before sharing or printing.');
    } catch(error) { message('The download could not be created. Try the original SVG or CSV link below, or use Print.'); }
  }));
})();
