document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('site-search');
  const resultsContainer = document.getElementById('search-results');
  if (!searchInput || !resultsContainer) return;

  let searchIndex = [];

  // Load Index
  fetch('search.json')
    .then(response => response.json())
    .then(data => {
      searchIndex = data;
    })
    .catch(err => console.error('Failed to load search index:', err));

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    resultsContainer.innerHTML = '';
    
    if (query.length < 2) return;

    const results = searchIndex.filter(item => {
      return item.title.toLowerCase().includes(query) || 
             item.content.toLowerCase().includes(query);
    });

    if (results.length === 0) {
      resultsContainer.innerHTML = '<p class="no-results">No matches found.</p>';
      return;
    }

    results.forEach(result => {
      const div = document.createElement('div');
      div.className = 'search-result';
      // Create a snippet context
      const lowerContent = result.content.toLowerCase();
      const idx = lowerContent.indexOf(query);
      let snippet = result.content.substring(0, 100) + '...';
      if (idx > -1) {
        const start = Math.max(0, idx - 40);
        const end = Math.min(result.content.length, idx + 60);
        snippet = (start > 0 ? '...' : '') + result.content.substring(start, end) + (end < result.content.length ? '...' : '');
      }

      div.innerHTML = `
        <a href="${result.url}">
          <h4>${result.title}</h4>
          <p>${snippet}</p>
        </a>
      `;
      resultsContainer.appendChild(div);
    });
  });
});
