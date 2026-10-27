(() => {
  const status = document.querySelector('#caption-copy-status');
  if (!status) return;
  document.querySelectorAll('[data-copy-caption]').forEach(button => {
    const original = button.innerHTML;
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copyCaption);
        button.textContent = 'Copied ✓';
        status.textContent = 'Caption copied. Personalize any details before posting.';
        window.setTimeout(() => { button.innerHTML = original; }, 1800);
      } catch {
        button.textContent = 'Select text to copy';
        status.textContent = 'Copy is unavailable in this browser. Select the caption text and copy it manually.';
      }
    });
  });
  const links = document.querySelectorAll('.caption-topic-nav a');
  links.forEach(link => link.addEventListener('click',()=>{
    links.forEach(other=>other.removeAttribute('aria-current'));
    link.setAttribute('aria-current','true');
  }));
})();
