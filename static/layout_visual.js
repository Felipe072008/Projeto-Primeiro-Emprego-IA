/* A mesma montagem é usada no editor e no site. Os nós originais conservam seus eventos. */
window.SiteLayout = (() => {
  function makeBoard(doc, page, catalog) {
    const host = doc.querySelector(page === 'login' ? '.login-composition' : '#page-' + page);
    const board = doc.createElement('div');
    board.dataset.layoutBoard = page;
    const sources = new Map();
    for (const [key, [,selector]] of Object.entries(catalog)) {
      const node = (page==='login' && key.startsWith('block_') ? host.closest('main') : host).querySelector(selector);
      if (!node) continue;
      const marker = doc.createComment('layout');
      node.before(marker);
      sources.set(key, {node, marker});
    }
    function textNode(node) {
      return node.matches('img') ? null : node.querySelector('button[data-go],#logout-button') || node.querySelector('h1,h2') || node;
    }
    function reset() {
      for (const {node, marker} of sources.values()) {
        if (node.parentElement === board) marker.after(node);
        if (node.hasAttribute('data-original-label')) {
          if (node.matches('img')) node.alt = node.dataset.originalLabel;
          else textNode(node).replaceChildren(...originalText.get(node));
          delete node.dataset.originalLabel;
        }
        delete node.dataset.layer;
      }
      board.remove();
      host.classList.remove('custom-board-host');
    }
    const originalText = new WeakMap();
    function extra(item) {
      const tag = {image:'img',button:'a',faq:'details',text:'p',notice:'aside',card:'article',shape:'div'}[item.kind];
      const node = doc.createElement(item.items ? 'section' : tag);
      node.className = 'layout-extra layout-' + item.kind;
      if (item.kind === 'image') {node.src='/static/escada-transparente.webp';node.alt=item.text;return node}
      if (item.kind === 'button') {
        node.href = item.url;
        node.classList.add('button','button--primary');
      }
      if (item.items) {
        for(const pair of item.items){
          const entry=doc.createElement('details'),question=doc.createElement('summary'),answer=doc.createElement('p');
          question.textContent=pair.question;answer.textContent=pair.answer;entry.append(question,answer);node.append(entry);
        }
      } else if (item.kind === 'shape') node.setAttribute('aria-hidden','true');
      else if (item.kind === 'faq') {
        const summary = doc.createElement('summary');
        summary.textContent = item.text;
        const answer = doc.createElement('p');
        answer.textContent = item.body;
        node.append(summary,answer);
      } else node.textContent = item.text;
      if(item.heading){
        const heading=doc.createElement('h2');heading.textContent=item.heading;node.prepend(heading);
      }
      return node;
    }
    function apply(layout) {
      reset();
      if (!layout) return;
      board.replaceChildren();
      host.classList.add('custom-board-host');
      host.prepend(board);
      for (const [key,item] of Object.entries(layout).sort((a,b)=>a[1].y-b[1].y || a[1].x-b[1].x)) {
        const node = sources.get(key)?.node || (item.kind && extra(item));
        if (!node) continue;
        if(sources.get(key)?.marker.parentElement?.closest('[data-section-key][hidden]')) continue;
        if (sources.has(key) && item.label) {
          node.dataset.originalLabel = node.matches('img') ? node.alt : '';
          if (node.matches('img')) node.alt = item.label;
          else {
            const target = textNode(node);
            originalText.set(node,Array.from(target.childNodes));
            target.textContent = item.label;
          }
        }
        node.dataset.layer = key;
        board.append(node);
      }
    }
    return {host, board, sources, apply, reset};
  }
  const media = matchMedia('(min-width:900px)');
  for (const host of document.querySelectorAll('[data-page-design]')) {
    const {page,catalog,desktop,mobile} = JSON.parse(host.dataset.pageDesign);
    const design = makeBoard(document,page,catalog);
    const render = () => design.apply(media.matches ? desktop : mobile);
    render();
    media.addEventListener('change',render);
  }
  return {makeBoard};
})();
