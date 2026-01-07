/**
 * Universal Search System for Academic Sites
 * Provides instant client-side search across pages, publications, and research
 */

class UniversalSearch {
  constructor() {
    this.searchIndex = [];
    this.searchInput = null;
    this.resultsContainer = null;
    this.init();
  }

  init() {
    // Check if search UI exists
    this.searchInput = document.querySelector('#search-input');
    this.resultsContainer = document.querySelector('#search-results');
    
    if (!this.searchInput) return;

    // Build search index
    this.buildSearchIndex();
    
    // Attach event listeners
    this.searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
    this.searchInput.addEventListener('focus', () => this.showResults());
    document.addEventListener('click', (e) => this.handleClickOutside(e));
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.searchInput.focus();
      }
      if (e.key === 'Escape' && this.resultsContainer) {
        this.hideResults();
      }
    });
  }

  buildSearchIndex() {
    const indexableElements = [
      // Page titles and headings
      ...document.querySelectorAll('h1, h2, h3'),
      // Publications
      ...document.querySelectorAll('.pub-title, .pub-meta'),
      // Research cards
      ...document.querySelectorAll('.research-card h3, .research-card .teaser'),
      // Team members
      ...document.querySelectorAll('.team-card h3, .team-card .role'),
      // Project cards
      ...document.querySelectorAll('.project-card-v2 h3, .project-card-v2 .keywords'),
      // Blog posts
      ...document.querySelectorAll('article h2, article .excerpt')
    ];

    this.searchIndex = indexableElements.map((el, index) => {
      const text = el.textContent.trim();
      const type = this.getElementType(el);
      const url = this.getElementUrl(el);
      
      return {
        id: index,
        text,
        type,
        url,
        element: el,
        searchText: text.toLowerCase()
      };
    }).filter(item => item.text.length > 0);
  }

  getElementType(el) {
    if (el.closest('.pub-title') || el.closest('.pub-row')) return 'publication';
    if (el.closest('.research-card')) return 'research';
    if (el.closest('.team-card')) return 'team';
    if (el.closest('.project-card-v2')) return 'project';
    if (el.closest('article')) return 'blog';
    if (el.tagName === 'H1') return 'page';
    return 'content';
  }

  getElementUrl(el) {
    // Try to find closest link
    const link = el.closest('a');
    if (link) return link.href;
    
    // Get section anchor
    const section = el.closest('section[id]');
    if (section) return `#${section.id}`;
    
    return window.location.pathname;
  }

  handleSearch(query) {
    if (!query || query.length < 2) {
      this.hideResults();
      return;
    }

    const searchTerms = query.toLowerCase().split(' ').filter(t => t.length > 0);
    const results = this.searchIndex
      .map(item => {
        let score = 0;
        searchTerms.forEach(term => {
          if (item.searchText.includes(term)) {
            // Boost score for exact matches
            if (item.searchText.startsWith(term)) score += 3;
            else if (item.text.toLowerCase().split(' ').includes(term)) score += 2;
            else score += 1;
          }
        });
        return { ...item, score };
      })
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 8); // Top 8 results

    this.displayResults(results, query);
  }

  displayResults(results, query) {
    if (!this.resultsContainer) return;

    if (results.length === 0) {
      this.resultsContainer.innerHTML = `
        <div class="search-no-results">
          <p>No results found for "${this.escapeHTML(query)}"</p>
        </div>
      `;
      this.showResults();
      return;
    }

    const groupedResults = this.groupByType(results);
    let html = '';

    Object.entries(groupedResults).forEach(([type, items]) => {
      html += `
        <div class="search-group">
          <h4 class="search-group-title">${this.capitalizeFirst(type)}s</h4>
          <div class="search-group-items">
            ${items.map(item => this.renderResultItem(item, query)).join('')}
          </div>
        </div>
      `;
    });

    this.resultsContainer.innerHTML = html;
    this.showResults();
  }

  groupByType(results) {
    return results.reduce((groups, item) => {
      if (!groups[item.type]) groups[item.type] = [];
      groups[item.type].push(item);
      return groups;
    }, {});
  }

  renderResultItem(item, query) {
    const highlightedText = this.highlightText(item.text, query);
    const typeIcon = this.getTypeIcon(item.type);
    
    return `
      <a href="${item.url}" class="search-result-item" data-type="${item.type}">
        <span class="result-icon">${typeIcon}</span>
        <div class="result-content">
          <div class="result-title">${highlightedText}</div>
          <div class="result-type">${this.capitalizeFirst(item.type)}</div>
        </div>
      </a>
    `;
  }

  highlightText(text, query) {
    const terms = query.toLowerCase().split(' ').filter(t => t.length > 0);
    let result = this.escapeHTML(text);
    
    terms.forEach(term => {
      const regex = new RegExp(`(${this.escapeRegex(term)})`, 'gi');
      result = result.replace(regex, '<mark>$1</mark>');
    });
    
    return result;
  }

  getTypeIcon(type) {
    const icons = {
      publication: '📄',
      research: '🔬',
      team: '👤',
      project: '🎯',
      blog: '📝',
      page: '📖',
      content: '📋'
    };
    return icons[type] || '•';
  }

  showResults() {
    if (this.resultsContainer) {
      this.resultsContainer.classList.add('active');
    }
  }

  hideResults() {
    if (this.resultsContainer) {
      this.resultsContainer.classList.remove('active');
    }
  }

  handleClickOutside(e) {
    if (!this.searchInput || !this.resultsContainer) return;
    
    if (!this.searchInput.contains(e.target) && 
        !this.resultsContainer.contains(e.target)) {
      this.hideResults();
    }
  }

  escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => new UniversalSearch());
} else {
  new UniversalSearch();
}
